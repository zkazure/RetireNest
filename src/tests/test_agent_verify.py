"""数字一致性提示的启发式规则。"""

from __future__ import annotations

from agent import numeric_warnings


def record(outputs: dict | None = None, inputs: dict | None = None) -> dict:
    return {
        "ok": outputs is not None,
        "inputs": inputs or {},
        "outputs": outputs,
        "error": None,
    }


def test_matching_amount_has_no_warning() -> None:
    warnings = numeric_warnings(
        "按假设约 27 万元。",
        [record({"future_balance_real": 270_820})],
    )
    assert warnings == []


def test_exact_amount_with_commas_has_no_warning() -> None:
    warnings = numeric_warnings(
        "期末余额为 270,820 元。",
        [record({"future_balance_real": 270_820})],
    )
    assert warnings == []


def test_input_amounts_are_allowed() -> None:
    warnings = numeric_warnings(
        "你月入 2 万元、月支出 1.2 万元，资产 50 万元。",
        [record({"x": 1}, {"monthly_income": 20_000, "monthly_expense": 12_000, "assets": 500_000})],
    )
    assert warnings == []


def test_fabricated_amount_is_flagged() -> None:
    warnings = numeric_warnings(
        "按假设你的余额会达到 50 万元。",
        [record({"future_balance_real": 270_820})],
    )
    assert len(warnings) == 1
    assert "50.00 万" in warnings[0]


def test_yi_unit_is_supported() -> None:
    warnings = numeric_warnings(
        "目标约 1.5 亿元。",
        [record({"target": 150_000_000})],
    )
    assert warnings == []


def test_percentages_and_ages_are_ignored() -> None:
    warnings = numeric_warnings(
        "常说的 4% 法则不适合所有人，你 55 岁退休。",
        [record({"x": 1})],
    )
    assert warnings == []


def test_amount_without_unit_is_not_checked() -> None:
    warnings = numeric_warnings(
        "这里有一个数字 1234567，但它没有金额单位。",
        [record({"x": 1})],
    )
    assert warnings == []


def test_multiple_unmatched_amounts_are_deduplicated() -> None:
    warnings = numeric_warnings(
        "余额 50 万元，另一处还是 50 万，目标 80 万元。",
        [record({"future_balance_real": 270_820})],
    )
    assert len(warnings) == 1
    assert "50.00 万" in warnings[0]
    assert "80.00 万" in warnings[0]


def test_no_amounts_has_no_warning() -> None:
    assert numeric_warnings("先告诉我你的年龄。", []) == []
