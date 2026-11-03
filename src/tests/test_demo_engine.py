"""浏览器引擎包要能独立跑通，且与直算结果一致。

静态体验包把引擎压成 zip 交给 Pyodide。这里用 Python 自己的 zipimport 验证两件事：
包里的模块齐全（漏打包的包会 ImportError），以及桥接入口算出来的数字与直接调命令一致。
"""

from __future__ import annotations

import importlib
import json
import sys
import zipfile
from pathlib import Path

from commands.registry import execute_command, get_command
from pages.lifecycle import MANIFEST
from pages.resolve import resolve
from tools.build_demo_engine import build


def _load_bridge(archive: Path):
    sys.path.insert(0, str(archive))
    try:
        importlib.invalidate_caches()
        module = importlib.import_module("demo_bridge")
        return module
    finally:
        sys.path.remove(str(archive))


def _unload(module) -> None:
    sys.modules.pop(module.__name__, None)


def test_archive_carries_engine_and_bridge(tmp_path: Path) -> None:
    archive = tmp_path / "engine.zip"
    count, size = build(archive)

    assert count > 50 and size > 0
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
    assert "demo_bridge.py" in names
    assert any(name.startswith("lifecycle/") for name in names)
    # 依赖 fastapi 与 openai 的模块不能混进来
    assert not any(name.startswith("api/") for name in names)
    assert not any(name.startswith("agent/") for name in names)


def test_bridge_matches_direct_command_call(tmp_path: Path) -> None:
    archive = tmp_path / "engine.zip"
    build(archive)
    bridge = _load_bridge(archive)
    try:
        page = json.loads(bridge.page_json())
        assert page["id"] == MANIFEST.id
        assert page == resolve(MANIFEST)

        values = dict(page["presets"][0]["values"]) | {"retirement_age": "62"}
        version = get_command("lifecycle.project").manifest.version
        result = json.loads(bridge.run_json("lifecycle.project", version, json.dumps(values)))
        direct = execute_command("lifecycle.project", version, values)

        assert "error" not in result
        assert result["outputs"] == direct
    finally:
        _unload(bridge)


def test_bridge_reports_input_errors(tmp_path: Path) -> None:
    archive = tmp_path / "engine.zip"
    build(archive)
    bridge = _load_bridge(archive)
    try:
        version = get_command("lifecycle.project").manifest.version
        broken = json.loads(
            bridge.run_json("lifecycle.project", version, json.dumps({"retirement_age": "很快"}))
        )
        assert broken["error"]["code"] == "INVALID_INPUT"
        assert broken["error"]["field_errors"]
    finally:
        _unload(bridge)
