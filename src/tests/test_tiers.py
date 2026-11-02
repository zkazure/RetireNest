"""档位输入：校验、解析与页面下发。"""

from __future__ import annotations

from profile import tiers as profile_tiers
from profile.errors import ProfileError

import pytest

from commands import tiers as tier_help
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from commands.validation import coerce_inputs
from pages import resolve
from pages.models import PageError, PageExecution, PageField, PageManifest, PageSection

TABLE = profile_tiers.INCOME
OPTIONS = tier_help.options(TABLE)


def _manifest(tiers=OPTIONS) -> CommandManifest:
    return CommandManifest(
        id="demo.tier",
        version="1.0.0",
        question="月收入？",
        inputs=(
            InputSpec(
                name="income",
                question="月收入？",
                type="tier",
                unit="元/月",
                tiers=tiers,
            ),
        ),
        outputs=(OutputSpec(name="income", question="月收入", type="number"),),
    )


def _command(manifest: CommandManifest | None = None) -> Command:
    return Command(manifest=manifest or _manifest(), handler=lambda inputs: {})


def _page(field: PageField, command: Command) -> PageManifest:
    return PageManifest(
        id="demo",
        version="2.0.0",
        title="演示",
        description="",
        sections=(PageSection(id="s1", title="收入", fields=(field,)),),
        executions=(PageExecution(command=command.manifest.id, inputs={"income": "income"}),),
    )


def test_档位选项由档位表生成():
    assert [tier.value for tier in OPTIONS] == list(TABLE.options())
    assert OPTIONS[0].amount == pytest.approx(TABLE.tiers[0].amount)


def test_取选项对应数值():
    spec = _manifest().inputs[0]
    assert tier_help.amount(spec, "12k20k") == pytest.approx(16_000)
    with pytest.raises(ProfileError):
        tier_help.amount(spec, "不存在")


def test_校验接受合法选项():
    command = _command()
    values, errors = coerce_inputs(command.manifest, {"income": "12k20k"})
    assert errors == []
    assert values["income"] == "12k20k"


@pytest.mark.parametrize("bad", ["不存在", 16000, None])
def test_校验拒绝非法选项(bad):
    command = _command()
    _, errors = coerce_inputs(command.manifest, {"income": bad})
    assert [error.field for error in errors] == ["income"]


def test_页面下发档位与回显():
    command = _command()
    field = PageField(name="income", command="demo.tier", precise=True)
    payload = resolve(_page(field, command), lookup=lambda _: command)
    spec = payload["sections"][0]["fields"][0]
    assert spec["type"] == "tier"
    assert spec["tiers"][0]["value"] == "lt5k"
    assert spec["tiers"][0]["amount"] == pytest.approx(3_500)
    assert spec["allowCustom"] is True
    assert spec["precise"] is True


def test_档位表不一致时报错():
    command = _command()
    other = _command(_manifest(tiers=OPTIONS[:3]))
    field = PageField(name="income", command="demo.tier")
    page = PageManifest(
        id="demo",
        version="2.0.0",
        title="演示",
        description="",
        sections=(PageSection(id="s1", title="收入", fields=(field,)),),
        executions=(
            PageExecution(command="demo.tier", inputs={"income": "income"}),
            PageExecution(command="demo.tier2", inputs={"income": "income"}),
        ),
    )
    lookup = {"demo.tier": command, "demo.tier2": other}
    with pytest.raises(PageError):
        resolve(page, lookup=lambda cid: lookup.get(cid))


def test_没有档位表时报错():
    command = _command(_manifest(tiers=()))
    field = PageField(name="income", command="demo.tier")
    with pytest.raises(PageError):
        resolve(_page(field, command), lookup=lambda _: command)
