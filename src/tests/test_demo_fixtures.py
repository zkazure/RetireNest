"""静态体验包的夹具不能悄悄过期：口径一动，这里就会红。

夹具是构建期快照，前端在 GitHub Pages 上直接读它。若某次改动调整了计算口径却没重跑
`tools/build_demo_fixtures.py`，页面上的数字就会和 README、海报对不上，故把「重新生成
的结果与已提交文件一致」钉成测试。
"""

from __future__ import annotations

import json
from pathlib import Path

from tools.build_demo_fixtures import OUTPUT, build

SCENARIOS = {"nailong-60", "nailong-55", "nailong-63"}
COMMANDS = {"lifecycle.project", "lifecycle.simulate", "strategy.compare"}


def test_fixtures_match_committed_file() -> None:
    assert OUTPUT.is_file(), "缺少夹具，先跑 tools/build_demo_fixtures.py"
    committed = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert build() == committed, "夹具已过期，重跑 tools/build_demo_fixtures.py"


def test_every_scenario_has_all_commands() -> None:
    fixtures = json.loads(Path(OUTPUT).read_text(encoding="utf-8"))
    ids = {scenario["id"] for scenario in fixtures["scenarios"]}
    assert ids == SCENARIOS
    for scenario in fixtures["scenarios"]:
        assert set(scenario["commands"]) == COMMANDS
        keys = {item["key"] for item in scenario["commands"].values()}
        assert len(keys) == 1, "同一场景的三条命令应共用一份输入"


def test_terminal_assets_add_up() -> None:
    fixtures = json.loads(Path(OUTPUT).read_text(encoding="utf-8"))
    for scenario in fixtures["scenarios"]:
        project = scenario["commands"]["lifecycle.project"]["outputs"]
        total = project["total_contributions"] + project["total_returns"]
        assert round(total, 2) == round(project["final_assets"], 2)
