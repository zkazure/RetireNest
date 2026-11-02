"""新命令经协议执行的端到端测试。"""

from __future__ import annotations

from datetime import date

import pytest

from commands import execute_command
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
    return execute_command(command_id, "1.0.0", {**BASE, **extra})


def test_项目命令给出逐年轨迹():
    result = run("lifecycle.project")
    assert result["pension_monthly"] > 0
    assert len(result["rows"]) > 10
    assert {"age", "income", "expense", "assets"} <= set(result["rows"][0])


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


def test_退休年龄可选并接受档位():
    result = run("lifecycle.project", retirement_age="55")
    assert result["rows"][55 - 35]["phase"] == "退休"
