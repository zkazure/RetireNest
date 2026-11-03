"""新命令经协议执行的端到端测试。"""

from __future__ import annotations

from datetime import date

import pytest

from commands import execute_command, get_command
from commands.errors import CommandInputError

BASE = {
    "age": 35,
    "sex": "男",
    "city": "上海",
    "birth_date": (date.today().replace(year=date.today().year - 35)).isoformat(),
    "income": "20k30k",
    "expense": "10k15k",
    "assets": "100w200w",
    "debt": "none",
    "retirement_expense": "6k10k",
    "travel": "once",
    "entertainment": "mid",
    "children": "none",
}


def run(command_id: str, **extra):
    command = get_command(command_id)
    assert command is not None
    return execute_command(command_id, command.manifest.version, {**BASE, **extra})


def test_项目命令给出逐年轨迹():
    result = run("lifecycle.project")
    assert result["pension_monthly"] > 0
    assert len(result["rows"]) > 10
    assert {"age", "income", "pension", "passive", "expense", "assets"} <= set(result["rows"][0])
    first = result["rows"][0]
    assert first["pension"] == 0
    assert first["passive"] > 0
    assert first["passive"] < first["income"]


def test_仿真命令给出成功率():
    result = run("lifecycle.simulate", paths=200)
    assert 0 <= result["success_rate"] <= 1
    assert result["affordable_monthly_expense"] > 0


def test_对比命令给出五个策略():
    result = run("strategy.compare")
    assert len(result["variants"]) == 5
    assert all("success_rate" in item for item in result["variants"])


def test_非法档位被拒绝():
    with pytest.raises(CommandInputError):
        run("lifecycle.project", income="不存在")


def test_自定义金额与同额档位结果一致():
    by_value = run("lifecycle.project", income="16000", expense="12500", assets="1500000", debt="0")
    by_key = run("lifecycle.project", income="12k20k", expense="10k15k", assets="100w200w")
    assert by_value == by_key


def test_自定义金额按原值计算而不是档位中值():
    custom = run("lifecycle.project", income="17000")
    tier = run("lifecycle.project", income="12k20k")
    assert custom["rows"] != tier["rows"]
    assert custom["final_assets"] > tier["final_assets"]


def test_自定义退休年龄生效():
    result = run("lifecycle.project", retirement_age="58")
    assert result["rows"][58 - 35]["phase"] == "退休"


def test_自定义数值越界被拒绝():
    with pytest.raises(CommandInputError):
        run("lifecycle.project", income="99999999")
    with pytest.raises(CommandInputError):
        run("lifecycle.project", retirement_age="25")
    with pytest.raises(CommandInputError):
        run("lifecycle.project", children="1.5")


def test_退休年龄可选并接受档位():
    result = run("lifecycle.project", retirement_age="55")
    assert result["rows"][55 - 35]["phase"] == "退休"


def test_退休后支出可选且缺省按当前支出():
    omitted = {key: value for key, value in BASE.items() if key != "retirement_expense"}
    result = execute_command("lifecycle.project", get_command("lifecycle.project").manifest.version, omitted)
    explicit = run("lifecycle.project", retirement_expense="10k15k")
    assert result["rows"] == explicit["rows"]

    retired = next(row for row in result["rows"] if row["phase"] == "退休")
    assert retired["expense"] - retired["medical"] - retired["soft"] == pytest.approx(
        12_500 * 12
    )
    assert run("lifecycle.project", retirement_expense="")["rows"] == explicit["rows"]
