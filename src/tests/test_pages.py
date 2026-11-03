"""页面清单：解析、约束交集、文案来源与端点契约。"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from commands import get_command
from pages import (
    LIFECYCLE_PAGE,
    PageError,
    PageExecution,
    PageField,
    PageManifest,
    PagePreset,
    PageSection,
)
from pages.resolve import resolve

client = TestClient(app)
FIXTURE = Path(__file__).parent / "fixtures" / "lifecycle-page.json"
PAGE_ID = "retirement.lifecycle"


def fields(body: dict) -> list[dict]:
    return [field for section in body["sections"] for field in section["fields"]]


def field(body: dict, name: str) -> dict:
    return next(item for item in fields(body) if item["name"] == name)


def _lookup_with_age_max(maximum: int):
    command = get_command("lifecycle.project")
    assert command is not None
    def lookup(command_id: str):
        command_now = get_command(command_id)
        if command_now is None or command_now.manifest.id not in (
            "lifecycle.project",
            "lifecycle.simulate",
            "strategy.compare",
        ):
            return command_now
        patched_inputs = tuple(
            replace(spec, constraints={**spec.constraints, "max": maximum})
            if spec.name == "age"
            else spec
            for spec in command_now.manifest.inputs
        )
        return replace(command_now, manifest=replace(command_now.manifest, inputs=patched_inputs))

    return lookup


def test_page_endpoint_lists_every_command() -> None:
    response = client.get(f"/api/pages/{PAGE_ID}")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == PAGE_ID
    assert body["version"] == LIFECYCLE_PAGE.version
    assert len(body["sections"]) == 4
    assert len(fields(body)) == 13
    assert len(body["executions"]) == 3
    assert [section["toggle"] for section in body["sections"] if section["toggle"]] == []
    names = [item["name"] for item in fields(body)]
    assert len(set(names)) == len(names)


def test_every_execution_matches_a_registered_command_version() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    for execution in body["executions"]:
        command = get_command(execution["command"])
        assert command is not None
        assert execution["version"] == command.manifest.version
        assert execution["question"] == command.manifest.question
        assert [
            (output["name"], output["question"], output["visible"])
            for output in execution["outputs"]
        ] == [
            (output.name, output.question, output.visible)
            for output in command.manifest.outputs
        ]


def test_labels_come_from_manifest_questions() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    for item in fields(body):
        command = get_command(item["source"]["command"])
        assert command is not None
        spec = next(spec for spec in command.manifest.inputs if spec.name == item["source"]["input"])
        assert item["label"] == spec.question


def test_every_field_is_used_and_every_argument_resolves() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    used = {
        field_name for execution in body["executions"] for field_name in execution["inputs"].values()
    }
    assert used == {item["name"] for item in fields(body)}


def _age_page() -> PageManifest:
    """年龄不在主页上，但三个命令共享这个参数，用它验证约束交集。"""
    return PageManifest(
        id="probe",
        version="1.0.0",
        title="探针",
        description="",
        sections=(
            PageSection(
                id="one",
                title="一",
                fields=(PageField(name="age", command="lifecycle.project", required=False),),
            ),
        ),
        executions=(
            PageExecution(command="lifecycle.project", inputs={"age": "age"}),
            PageExecution(command="lifecycle.simulate", inputs={"age": "age"}),
            PageExecution(command="strategy.compare", inputs={"age": "age"}),
        ),
    )


def test_shared_constraints_are_intersected() -> None:
    age = field(resolve(_age_page()), "age")

    specs = []
    for command_id in ("lifecycle.project", "lifecycle.simulate", "strategy.compare"):
        command = get_command(command_id)
        assert command is not None
        specs.append(next(spec for spec in command.manifest.inputs if spec.name == "age"))

    assert len(specs) == 3
    assert age["min"] == max(spec.constraints["min"] for spec in specs)
    assert age["max"] == min(spec.constraints["max"] for spec in specs)


def test_range_is_recomputed_not_hardcoded() -> None:
    patched = resolve(_age_page(), _lookup_with_age_max(120))
    assert field(patched, "age")["max"] == 120

    base = resolve(_age_page())
    assert field(base, "age")["max"] == 100


def test_empty_intersection_is_rejected() -> None:
    with pytest.raises(PageError):
        resolve(_age_page(), _lookup_with_age_max(10))


def test_field_without_consumer_is_rejected() -> None:
    page = PageManifest(
        id="broken",
        version="1.0.0",
        title="坏页面",
        description="",
        sections=(
            PageSection(
                id="one",
                title="一",
                fields=(PageField(name="age", command="lifecycle.project"),),
            ),
        ),
        executions=(PageExecution(command="lifecycle.project", inputs={}),),
    )
    with pytest.raises(PageError, match="没有被任何命令使用"):
        resolve(page)


def test_required_comes_from_the_page_field() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    for name in ("category", "retirement_age", "retirement_expense"):
        assert field(body, name)["required"] is False
    for name in ("sex", "city", "birth_date", "income"):
        assert field(body, name)["required"] is True


def test_retirement_expense_is_optional_with_default_hint() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    retirement_expense = field(body, "retirement_expense")
    assert retirement_expense["required"] is False
    assert retirement_expense["hint"] == "留空则按当前每月支出计算。"


def test_tier_field_carries_options_and_amounts() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    income = field(body, "income")
    assert income["type"] == "tier"
    assert len(income["tiers"]) >= 5
    assert all({"value", "label", "amount"} <= set(tier) for tier in income["tiers"])
    assert income["allowCustom"] is True
    assert income["min"] == 0
    assert income["max"] == 10_000_000


def test_tier_fields_allow_custom_values() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    tier_fields = [item for item in fields(body) if item["type"] == "tier"]
    assert len(tier_fields) == 9
    assert all(item["allowCustom"] is True for item in tier_fields)
    retirement_age = field(body, "retirement_age")
    assert retirement_age["integer"] is True
    assert (retirement_age["min"], retirement_age["max"]) == (30, 90)


def test_select_fields_stay_choice_only() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    for name in ("sex", "city", "category"):
        assert field(body, name)["allowCustom"] is False


def test_page_field_is_required_by_default() -> None:
    assert PageField(name="income", command="lifecycle.project").required is True


def test_optional_field_rejects_required_command_input() -> None:
    page = PageManifest(
        id="broken",
        version="1.0.0",
        title="坏页面",
        description="",
        sections=(
            PageSection(
                id="one",
                title="一",
                fields=(PageField(name="income", command="lifecycle.project", required=False),),
            ),
        ),
        executions=(PageExecution(command="lifecycle.project", inputs={"income": "income"}),),
    )
    with pytest.raises(PageError, match="可留空"):
        resolve(page)


def test_unknown_page_returns_404() -> None:
    response = client.get("/api/pages/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "UNKNOWN_PAGE"


def _page_with_preset(values: dict, preset_id: str = "probe") -> PageManifest:
    return replace(LIFECYCLE_PAGE, presets=(PagePreset(id=preset_id, label="探针", values=values),))


def test_preset_is_delivered_with_every_field() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    assert [item["id"] for item in body["presets"]] == ["nailong"]

    nailong = body["presets"][0]
    assert nailong["label"] == "奶龙"
    assert nailong["description"] == "34 岁 · 深圳 · 月入两万多，想 60 岁退休"
    names = {item["name"] for item in fields(body)}
    assert set(nailong["values"]) <= names
    assert len(nailong["values"]) == 12
    assert "category" not in nailong["values"]


def test_preset_values_match_field_options() -> None:
    body = client.get(f"/api/pages/{PAGE_ID}").json()
    for name, value in body["presets"][0]["values"].items():
        spec = field(body, name)
        if spec["type"] == "tier":
            assert value in {tier["value"] for tier in spec["tiers"]}
        elif spec["type"] == "select":
            assert value in {option["value"] for option in spec["options"]}
        elif spec["type"] == "date":
            assert date.fromisoformat(value).isoformat() == value


def test_preset_may_fill_only_some_fields() -> None:
    resolved = resolve(_page_with_preset({"sex": "女"}))
    assert resolved["presets"][0]["values"] == {"sex": "女"}


def test_preset_with_unknown_field_is_rejected() -> None:
    with pytest.raises(PageError, match="未知字段"):
        resolve(_page_with_preset({"nope": "x"}))


def test_preset_with_unknown_option_is_rejected() -> None:
    with pytest.raises(PageError, match="不在选项里"):
        resolve(_page_with_preset({"sex": "其他"}))


def test_preset_with_unknown_tier_is_rejected() -> None:
    """允许自定义的档位字段：非数字照样拒；不允许自定义时只认档位 key。"""
    with pytest.raises(PageError, match="不是数字"):
        resolve(_page_with_preset({"income": "9k"}))
    assert resolve(_page_with_preset({"income": "17000"}))["presets"]

    page = PageManifest(
        id="probe",
        version="1.0.0",
        title="探针",
        description="",
        sections=(
            PageSection(
                id="one",
                title="一",
                fields=(PageField(name="income", command="lifecycle.project"),),
            ),
        ),
        executions=(PageExecution(command="lifecycle.project", inputs={"income": "income"}),),
        presets=(PagePreset(id="probe", label="探针", values={"income": "9k"}),),
    )
    with pytest.raises(PageError, match="不在档位里"):
        resolve(page)


def test_preset_custom_number_respects_constraints() -> None:
    assert resolve(_page_with_preset({"retirement_age": "58"}))["presets"]
    with pytest.raises(PageError, match="大于上限"):
        resolve(_page_with_preset({"retirement_age": "95"}))
    with pytest.raises(PageError, match="不是整数"):
        resolve(_page_with_preset({"retirement_age": "58.5"}))


def test_preset_with_bad_date_is_rejected() -> None:
    with pytest.raises(PageError, match="不是合法日期"):
        resolve(_page_with_preset({"birth_date": "1992/03/15"}))


def test_preset_ids_must_be_unique() -> None:
    page = replace(
        LIFECYCLE_PAGE,
        presets=(
            PagePreset(id="probe", label="甲", values={"sex": "男"}),
            PagePreset(id="probe", label="乙", values={"sex": "女"}),
        ),
    )
    with pytest.raises(PageError, match="id 重复"):
        resolve(page)


def test_page_fixture_matches_endpoint() -> None:
    response = client.get(f"/api/pages/{PAGE_ID}")
    assert response.status_code == 200
    assert response.json() == json.loads(FIXTURE.read_text(encoding="utf-8"))
