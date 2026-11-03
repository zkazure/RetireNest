"""把计算引擎打包成前端可加载的 zip，供静态体验包在浏览器里用 Pyodide 跑。

用法（工作目录为 src/）：

    uv run python tools/build_demo_engine.py

只收引擎实际用到的包，排除 `api/` 与 `agent/`——它们依赖 fastapi 与 openai，
浏览器里既没装也用不上。产物 `frontend/public/demo/py/engine.zip` 随前端构建一起发布，
Pyodide 解包后把目录加进 `sys.path` 就能 `import`。

改引擎代码后需要重新打包；`tests/test_demo_engine.py` 会拿 zip 里的桥接模块直算，
和直接调命令的结果比对，漏打包会红。
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
OUTPUT = ROOT / "frontend" / "public" / "demo" / "py" / "engine.zip"

PACKAGES = (
    "commands",
    "pages",
    "lifecycle",
    "strategy",
    "profile",
    "simulation",
    "portfolio",
    "pension",
    "medical",
    "living",
    "deposit",
    "inflation",
    "savings",
    "longevity",
    "plan",
)

BRIDGE = '''"""浏览器侧入口：Pyodide 只调用这两个函数。

入参与返回都是 JSON 字符串，避免 Python 对象跨语言边界时的隐式转换。
"""

from __future__ import annotations

import json
from dataclasses import asdict

from commands.errors import CommandError
from commands.registry import execute_command, get_command
from pages.lifecycle import MANIFEST
from pages.resolve import resolve


def _error(code: str, message: str, status: int, field_errors: list) -> str:
    return json.dumps(
        {"error": {"code": code, "message": message, "status": status, "field_errors": field_errors}},
        ensure_ascii=False,
    )


def page_json() -> str:
    return json.dumps(resolve(MANIFEST), ensure_ascii=False)


def run_json(command_id: str, version: str, inputs_json: str) -> str:
    try:
        inputs = json.loads(inputs_json)
    except json.JSONDecodeError as exc:
        return _error("BAD_INPUT", f"输入不是合法 JSON：{exc}", 400, [])
    if get_command(command_id) is None:
        return _error("UNKNOWN_COMMAND", f"未知命令：{command_id}", 404, [])
    try:
        outputs = execute_command(command_id, version, inputs)
    except CommandError as exc:
        field_errors = [asdict(item) for item in exc.field_errors]
        return _error(exc.code, exc.message, exc.status, field_errors)
    except Exception as exc:  # 浏览器里没有服务端日志，原样回传给前端展示
        return _error("CALCULATION_ERROR", str(exc), 500, [])
    return json.dumps({"outputs": outputs}, ensure_ascii=False)
'''


def sources() -> list[Path]:
    files: list[Path] = []
    for package in PACKAGES:
        directory = SRC / package
        if not directory.is_dir():
            raise SystemExit(f"缺少包目录：{directory}")
        files.extend(
            path
            for path in sorted(directory.rglob("*.py"))
            if "__pycache__" not in path.parts and "tests" not in path.parts
        )
    return files


def build(output: Path = OUTPUT) -> tuple[int, int]:
    """写出 zip，返回 (模块数, 字节数)。测试用临时路径调它。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sources()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(SRC).as_posix())
        archive.writestr("demo_bridge.py", BRIDGE)
    return len(files), output.stat().st_size


def main() -> int:
    count, size = build()
    print(f"写出 {OUTPUT.relative_to(ROOT)}：{count} 个模块，{size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
