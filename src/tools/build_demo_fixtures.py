"""把页面清单与三条命令的结果预先算好，生成静态体验包用的夹具。

用法（工作目录为 src/）：

    uv run python tools/build_demo_fixtures.py

GitHub Pages 上跑不了 FastAPI，所以演示版把「页面清单 + 若干预置画像的命令输出」
在构建期算成一份 JSON，前端用 `demo-shim.ts` 拦截 `/api` 请求直接喂数据。
预置画像只有退休年龄不同，其余沿用页面清单里的示例画像。

输出写到 frontend/public/demo/fixtures.json，构建时被原样拷进产物。
改动画像或口径后重跑一次即可，不要手改产物。
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

# 脚本在 src/tools 下，导入领域模块前先把 src/ 放到最前面。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commands.registry import execute_command, get_command
from pages.lifecycle import MANIFEST, NAILONG
from pages.resolve import resolve

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "frontend" / "public" / "demo" / "fixtures.json"

# 只改退休年龄，其余字段沿用示例画像，保证「换场景」读起来是同一家人的不同选择。
SCENARIOS = (
    ("nailong-60", "奶龙 · 60 岁退休", "60", "月入两万多，想 60 岁退休"),
    ("nailong-55", "奶龙 · 55 岁早退", "55", "同样的收入，提前五年退下来，看缺口差多少"),
    ("nailong-63", "奶龙 · 63 岁晚退", "63", "多干三年，养老金与终值各涨多少"),
)


def canonical(inputs: dict[str, Any]) -> str:
    """与前端同口径的输入键：键名排序、无空格、不转义中文。"""
    return json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_inputs(values: dict[str, Any], execution: Any) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for argument, field in execution.inputs.items():
        value = values.get(field)
        if value is None or value == "":
            continue
        inputs[argument] = value
    return inputs


def scenario_page() -> dict[str, Any]:
    presets = tuple(
        replace(
            NAILONG,
            id=scenario_id,
            label=label,
            description=description,
            values={**NAILONG.values, "retirement_age": age},
        )
        for scenario_id, label, age, description in SCENARIOS
    )
    return resolve(replace(MANIFEST, presets=presets))


def scenario_payload() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for scenario_id, label, age, _ in SCENARIOS:
        values = {**NAILONG.values, "retirement_age": age}
        scenario: dict[str, Any] = {"id": scenario_id, "label": label, "commands": {}}
        for execution in MANIFEST.executions:
            command = get_command(execution.command)
            if command is None:
                raise SystemExit(f"页面清单引用了未知命令：{execution.command}")
            inputs = build_inputs(values, execution)
            outputs = execute_command(
                execution.command, command.manifest.version, inputs
            )
            scenario["commands"][execution.command] = {
                "version": command.manifest.version,
                "key": canonical(inputs),
                "inputs": inputs,
                "outputs": outputs,
            }
        payload.append(scenario)
    return payload


def build() -> dict[str, Any]:
    return {
        "note": "由 src/tools/build_demo_fixtures.py 生成，勿手改",
        "page": scenario_page(),
        "scenarios": scenario_payload(),
    }


def main() -> int:
    fixtures = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(fixtures, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    size_kb = OUTPUT.stat().st_size / 1024
    print(f"写出 {OUTPUT.relative_to(ROOT)}（{size_kb:.0f} KB）")
    for scenario in fixtures["scenarios"]:
        project = scenario["commands"]["lifecycle.project"]["outputs"]
        print(
            f"  {scenario['label']:<16} 养老金 {project['pension_monthly']:>9,.2f} 元/月"
            f"  退休时资产 {project['retirement_assets'] / 10000:>8.1f} 万"
            f"  终值 {project['final_assets'] / 10000:>8.1f} 万"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
