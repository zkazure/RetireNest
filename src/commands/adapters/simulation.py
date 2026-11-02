"""蒙特卡洛退休模拟与安全提取率命令。"""

from __future__ import annotations

from typing import Any

from commands.errors import CommandInputError
from commands.models import Command, CommandManifest, InputSpec, OutputSpec
from plan.models import FieldError
from simulation import MonteCarloInput, WithdrawalInput, safe_withdrawal, simulate

MAX_AMOUNT = 1_000_000_000
MAX_SEED = 2**31 - 1
RETURN = {"min": -5, "max": 15}
INFLATION = {"min": 0, "max": 10}
VOLATILITY = {"min": 0, "max": 40}
PATHS = {"min": 100, "max": 20_000}
SEED = {"min": 0, "max": MAX_SEED}

ASSUMPTIONS_COMMON = (
    "按实际购买力计算；名义毛收益率取对数正态，通胀按输入确定性折算；"
    "每年年末投入或支取，支出按实际值固定。"
)
DISCLAIMER = "结果是基于假设的路径回测，不构成投资建议；成功率是路径占比，不是概率保证。"


def _common_inputs() -> tuple[InputSpec, ...]:
    return (
        InputSpec(
            name="annual_return_pct",
            question="你预期的名义年回报率？",
            type="number",
            unit="%",
            description="名义值；工具会用 inflation_pct 折算实际回报。",
            constraints=RETURN,
        ),
        InputSpec(
            name="volatility_pct",
            question="你预期的年化波动率？",
            type="number",
            unit="%",
            description="名义年收益率的标准差；0 表示确定性路径。",
            constraints=VOLATILITY,
        ),
        InputSpec(
            name="inflation_pct",
            question="你预期的年通胀率？",
            type="number",
            unit="%",
            description="用于把名义收益折算成实际收益；通胀本身不做随机化。",
            constraints=INFLATION,
        ),
        InputSpec(
            name="paths",
            question="模拟多少条路径？",
            type="integer",
            unit="条",
            required=False,
            default=2000,
            description="默认 2000；越多越稳定，但计算越慢，上限 20000。",
            constraints=PATHS,
        ),
        InputSpec(
            name="seed",
            question="随机种子？",
            type="integer",
            required=False,
            default=42,
            description="同一个种子与同一组参数得到同一结果；便于复核和测试。",
            constraints=SEED,
        ),
    )


MONTE_CARLO_MANIFEST = CommandManifest(
    id="simulation.retirement",
    version="1.0.0",
    question="按现在的储蓄和投入，退休后钱会不会用完？",
    description="跑数千条随机市场路径，给出资金未耗尽的路径占比与余额分位。",
    when_to_use="用户问退休后资金是否够用、成功率多少、或想比较不同支出水平时用。",
    when_not_to_use=(
        "用户已经有一笔退休余额，只问每年能安全提取多少时用 withdrawal.safe_rate；"
        "不要用本命令反复试提取率。"
    ),
    inputs=(
        InputSpec(
            name="current_savings",
            question="你现在有多少可用于退休规划的储蓄？",
            type="number",
            unit="元",
            description="按今天的购买力填写，不含负债。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        InputSpec(
            name="monthly_contribution",
            question="你每月能拿出多少钱用于退休储蓄？",
            type="number",
            unit="元/月",
            description="按实际购买力填写，积累期内每年按 12 个月合计投入。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        InputSpec(
            name="years_to_retirement",
            question="距离退休还有几年？",
            type="integer",
            unit="年",
            description="积累期年数，整数；与 retirement_years 合计不超过 100。",
            constraints={"min": 1, "max": 50},
        ),
        InputSpec(
            name="retirement_years",
            question="退休后计划多少年？",
            type="integer",
            unit="年",
            description="消耗期年数，整数；与 years_to_retirement 合计不超过 100。",
            constraints={"min": 1, "max": 60},
        ),
        InputSpec(
            name="annual_retirement_expense",
            question="退休后每年打算花多少？",
            type="number",
            unit="元/年",
            description="实际值；工具会减去养老金后得到每年净支取。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        InputSpec(
            name="monthly_pension",
            question="你预计每月能领多少养老金？",
            type="number",
            unit="元/月",
            required=False,
            default=0,
            description="实际值，可选；养老金覆盖支出时净支取为 0。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        *_common_inputs(),
    ),
    outputs=(
        OutputSpec(
            name="success_rate",
            question="资金未耗尽的路径占比",
            type="number",
            unit="%",
            semantic="percent",
            precision=1,
        ),
        OutputSpec(
            name="failed_paths",
            question="耗尽路径数",
            type="integer",
            unit="条",
            precision=0,
        ),
        OutputSpec(
            name="median_terminal_balance_real",
            question="期末余额中位数",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="p10_terminal_balance_real",
            question="期末余额 10% 分位",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="p90_terminal_balance_real",
            question="期末余额 90% 分位",
            type="number",
            unit="元",
            semantic="money_total_real",
            precision=0,
        ),
        OutputSpec(
            name="median_depletion_year",
            question="资金耗尽的中位年份",
            type="number",
            unit="年",
            precision=1,
        ),
        OutputSpec(
            name="terminal_balance_percentiles",
            question="期末余额分位",
            type="object",
            visible=False,
        ),
        OutputSpec(
            name="depletion_year_percentiles",
            question="耗尽年份分位",
            type="object",
            visible=False,
        ),
        OutputSpec(
            name="balance_percentiles",
            question="逐年余额分位",
            type="object",
            visible=False,
        ),
        OutputSpec(name="paths", question="模拟路径数", type="integer", visible=False),
        OutputSpec(name="seed", question="随机种子", type="integer", visible=False),
        OutputSpec(name="assumptions", question="计算假设", type="text"),
        OutputSpec(name="note", question="结果提示", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "current_savings": 500_000,
                "monthly_contribution": 3_000,
                "years_to_retirement": 15,
                "retirement_years": 30,
                "annual_retirement_expense": 96_000,
                "monthly_pension": 3_000,
                "annual_return_pct": 5,
                "volatility_pct": 12,
                "inflation_pct": 2,
                "paths": 2000,
                "seed": 42,
            },
        },
    ),
)

WITHDRAWAL_MANIFEST = CommandManifest(
    id="withdrawal.safe_rate",
    version="1.0.0",
    question="退休时有一笔钱，每年可以安全提取多少？",
    description="在目标成功率下二分搜索最高提取比例，并给出对应的年/月提取额。",
    when_to_use="用户已有退休余额，问每年或每月能安全提取多少时用。",
    when_not_to_use=(
        "用户问按当前投入能否攒到目标时用 savings.project / savings.goal；"
        "不要把安全提取率当成保证收益，也不要用它替代 simulation.retirement 的整段规划。"
    ),
    inputs=(
        InputSpec(
            name="retirement_savings",
            question="退休时预计有多少储蓄？",
            type="number",
            unit="元",
            description="按今天的购买力填写，作为退休起点的可投资余额。",
            constraints={"min": 0, "max": MAX_AMOUNT},
        ),
        InputSpec(
            name="retirement_years",
            question="退休后计划多少年？",
            type="integer",
            unit="年",
            description="消耗期年数，整数。",
            constraints={"min": 1, "max": 60},
        ),
        InputSpec(
            name="target_success_rate",
            question="你希望达到的模拟成功率？",
            type="number",
            unit="%",
            required=False,
            default=90,
            description="默认 90%；越高越保守，可提取比例越低。",
            constraints={"min": 50, "max": 99.9},
        ),
        *_common_inputs(),
    ),
    outputs=(
        OutputSpec(
            name="safe_withdrawal_rate_pct",
            question="安全提取率",
            type="number",
            unit="%",
            semantic="percent",
            precision=2,
        ),
        OutputSpec(
            name="annual_withdrawal_real",
            question="每年可提取",
            type="number",
            unit="元/年",
            semantic="money_per_year_real",
            precision=0,
        ),
        OutputSpec(
            name="monthly_withdrawal_real",
            question="每月可提取",
            type="number",
            unit="元/月",
            semantic="money_per_month_real",
            precision=0,
        ),
        OutputSpec(
            name="success_rate_at_rate",
            question="该提取率下的成功率",
            type="number",
            unit="%",
            semantic="percent",
            precision=1,
        ),
        OutputSpec(
            name="depletion_year_percentiles",
            question="耗尽年份分位",
            type="object",
            visible=False,
        ),
        OutputSpec(name="paths", question="模拟路径数", type="integer", visible=False),
        OutputSpec(name="seed", question="随机种子", type="integer", visible=False),
        OutputSpec(name="assumptions", question="计算假设", type="text"),
        OutputSpec(name="note", question="结果提示", type="text"),
    ),
    examples=(
        {
            "name": "default",
            "inputs": {
                "retirement_savings": 2_000_000,
                "retirement_years": 30,
                "annual_return_pct": 5,
                "volatility_pct": 12,
                "inflation_pct": 2,
                "target_success_rate": 90,
                "paths": 2000,
                "seed": 42,
            },
        },
    ),
)


def _domain_error(exc: ValueError) -> CommandInputError:
    return CommandInputError("请检查输入。", [FieldError("inputs", str(exc))])


def _assumptions(
    *,
    annual_return_pct: float,
    volatility_pct: float,
    inflation_pct: float,
    paths: int,
    seed: int,
) -> str:
    return (
        f"{ASSUMPTIONS_COMMON}名义年回报 {annual_return_pct:g}%，"
        f"年波动率 {volatility_pct:g}%，通胀 {inflation_pct:g}%；"
        f"{paths} 条路径，seed={seed}。"
    )


def handle_simulation(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = MonteCarloInput(
            current_savings=inputs["current_savings"],
            monthly_contribution=inputs["monthly_contribution"],
            years_to_retirement=inputs["years_to_retirement"],
            retirement_years=inputs["retirement_years"],
            annual_return_pct=inputs["annual_return_pct"],
            volatility_pct=inputs["volatility_pct"],
            inflation_pct=inputs["inflation_pct"],
            annual_retirement_expense=inputs["annual_retirement_expense"],
            monthly_pension=inputs["monthly_pension"],
            paths=inputs["paths"],
            seed=inputs["seed"],
        )
    except ValueError as exc:
        raise _domain_error(exc) from exc

    result = simulate(data)
    terminal = result.terminal_balance_percentiles
    depletion = result.depletion_year_percentiles
    return {
        "success_rate": result.success_rate,
        "failed_paths": result.failed_paths,
        "median_terminal_balance_real": terminal["p50"],
        "p10_terminal_balance_real": terminal["p10"],
        "p90_terminal_balance_real": terminal["p90"],
        "median_depletion_year": depletion.get("p50"),
        "terminal_balance_percentiles": terminal,
        "depletion_year_percentiles": depletion or None,
        "balance_percentiles": [
            {"year": point.year, "p10": point.p10, "p50": point.p50, "p90": point.p90}
            for point in result.balance_percentiles
        ],
        "paths": data.paths,
        "seed": data.seed,
        "assumptions": _assumptions(
            annual_return_pct=data.annual_return_pct,
            volatility_pct=data.volatility_pct,
            inflation_pct=data.inflation_pct,
            paths=data.paths,
            seed=data.seed,
        ),
        "note": DISCLAIMER,
    }


def handle_withdrawal(inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        data = WithdrawalInput(
            retirement_savings=inputs["retirement_savings"],
            retirement_years=inputs["retirement_years"],
            annual_return_pct=inputs["annual_return_pct"],
            volatility_pct=inputs["volatility_pct"],
            inflation_pct=inputs["inflation_pct"],
            target_success_rate=inputs["target_success_rate"],
            paths=inputs["paths"],
            seed=inputs["seed"],
        )
    except ValueError as exc:
        raise _domain_error(exc) from exc

    result = safe_withdrawal(data)
    return {
        "safe_withdrawal_rate_pct": result.safe_withdrawal_rate_pct,
        "annual_withdrawal_real": result.annual_withdrawal_real,
        "monthly_withdrawal_real": result.monthly_withdrawal_real,
        "success_rate_at_rate": result.success_rate_at_rate,
        "depletion_year_percentiles": result.depletion_year_percentiles or None,
        "paths": data.paths,
        "seed": data.seed,
        "assumptions": _assumptions(
            annual_return_pct=data.annual_return_pct,
            volatility_pct=data.volatility_pct,
            inflation_pct=data.inflation_pct,
            paths=data.paths,
            seed=data.seed,
        ),
        "note": (
            f"{DISCLAIMER} 提取额按实际购买力固定，"
            f"目标成功率为 {data.target_success_rate:g}%。"
        ),
    }


SIMULATION_COMMAND = Command(manifest=MONTE_CARLO_MANIFEST, handler=handle_simulation)
WITHDRAWAL_COMMAND = Command(manifest=WITHDRAWAL_MANIFEST, handler=handle_withdrawal)
COMMANDS = (SIMULATION_COMMAND, WITHDRAWAL_COMMAND)
"""注册表使用的两个模拟命令。"""
