"""页面清单：解析、约束交集、文案来源与端点契约。"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import app
from commands import get_command
from pages import RETIREMENT_PAGE, PageError, PageExecution, PageField, PageManifest, PageSection
from pages.resolve import resolve

client = TestClient(app)
FIXTURE = Path(__file__).parent / "fixtures" / "retirement-page.json"


def fields(body: dict) -> list[dict]:
    return [field for section in body["sections"] for field in section["fields"]]


def field(body: dict, name: str) -> dict:
    return next(item for item in fields(body) if item["name"] == name)


def _lookup_with_age_max(maximum: int):
    command = get_command("plan.retirement")
    assert command is not None
    inputs = tuple(
        replace(spec, constraints={**spec.constraints, "max": maximum})
        if spec.name == "age"
        else spec
        for spec in command.manifest.inputs
    )
    patched = replace(command, manifest=replace(command.manifest, inputs=inputs))

    def lookup(command_id: str):
        return patched if command_id == "plan.retirement" else get_command(command_id)

    return lookup


def test_page_endpoint_lists_every_command() -> None:
    response = client.get("/api/pages/retirement")
    assert response.status_code == 200

    body = response.json()
    assert body["id"] == "retirement"
    assert body["version"] == RETIREMENT_PAGE.version
    assert len(body["sections"]) == 8
    assert len(fields(body)) == 39
    assert len(body["executions"]) == 5
    assert [section["toggle"]["name"] for section in body["sections"] if section["toggle"]] == [
        "medical_enabled",
        "pension_enabled",
        "deposit_enabled",
    ]
    names = [item["name"] for item in fields(body)]
    assert len(set(names)) == len(names)


def test_every_execution_matches_a_registered_command_version() -> None:
    body = client.get("/api/pages/retirement").json()
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
    body = client.get("/api/pages/retirement").json()
    for item in fields(body):
        command = get_command(item["source"]["command"])
        assert command is not None
        spec = next(spec for spec in command.manifest.inputs if spec.name == item["source"]["input"])
        assert item["label"] == spec.question


def test_every_field_is_used_and_every_argument_resolves() -> None:
    body = client.get("/api/pages/retirement").json()
    used = {
        field_name for execution in body["executions"] for field_name in execution["inputs"].values()
    }
    assert used == {item["name"] for item in fields(body)}


def test_shared_constraints_are_intersected() -> None:
    body = client.get("/api/pages/retirement").json()
    age = field(body, "age")

    specs = []
    for execution in body["executions"]:
        argument = next(
            (arg for arg, name in execution["inputs"].items() if name == "age"), None
        )
        if argument is None:
            continue
        command = get_command(execution["command"])
        assert command is not None
        specs.append(next(spec for spec in command.manifest.inputs if spec.name == argument))

    assert len(specs) == 3
    assert age["min"] == max(spec.constraints["min"] for spec in specs)
    assert age["max"] == min(spec.constraints["max"] for spec in specs)


def test_range_is_recomputed_not_hardcoded() -> None:
    patched = resolve(RETIREMENT_PAGE, _lookup_with_age_max(120))
    assert field(patched, "age")["max"] == 120

    base = resolve(RETIREMENT_PAGE)
    assert field(base, "age")["max"] == 80


def test_empty_intersection_is_rejected() -> None:
    with pytest.raises(PageError):
        resolve(RETIREMENT_PAGE, _lookup_with_age_max(10))


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
                fields=(PageField(name="age", command="plan.retirement"),),
            ),
        ),
        executions=(PageExecution(command="plan.retirement", inputs={}),),
    )
    with pytest.raises(PageError, match="没有被任何命令使用"):
        resolve(page)


def test_required_comes_from_the_page_field() -> None:
    body = client.get("/api/pages/retirement").json()
    for name in ("debt", "monthly_pension", "partner", "annual_rate", "prior_monthly_wage"):
        assert field(body, name)["required"] is False
    for name in ("age", "assets", "birth_date"):
        assert field(body, name)["required"] is True

    category = field(body, "category")
    assert category["required"] is True
    assert category["visibleWhen"] == [{"field": "gender", "equals": "女"}]


def test_page_field_is_required_by_default() -> None:
    assert PageField(name="age", command="plan.retirement").required is True


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
                fields=(PageField(name="age", command="plan.retirement", required=False),),
            ),
        ),
        executions=(PageExecution(command="plan.retirement", inputs={"age": "age"}),),
    )
    with pytest.raises(PageError, match="可留空"):
        resolve(page)


def test_unknown_page_returns_404() -> None:
    response = client.get("/api/pages/nope")
    assert response.status_code == 404
    assert response.json()["code"] == "UNKNOWN_PAGE"


def test_page_fixture_matches_endpoint() -> None:
    response = client.get("/api/pages/retirement")
    assert response.status_code == 200
    assert response.json() == json.loads(FIXTURE.read_text(encoding="utf-8"))
