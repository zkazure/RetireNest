"""把 docs/submission 下的 HTML 版式渲染成提交用 PNG，并校验尺寸与体积。

用法：
    uv run --project src python docs/submission/build-images.py
    python3 docs/submission/build-images.py          # 只用标准库，两种都行

只依赖本机已装的 Chromium（headless shell 或完整版），可用 CHROME_BIN 指定。
"""

from __future__ import annotations

import glob
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TARGETS = (
    # 名称, 源 HTML, 输出 PNG, 宽, 高
    ("cover", "cover.html", "cover.png", 1280, 720),
    ("poster", "poster.html", "poster.png", 1080, 1920),
)

CHROME_HINTS = (
    "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
    "~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
)


def find_chrome() -> Path:
    forced = os.environ.get("CHROME_BIN")
    if forced:
        path = Path(forced).expanduser()
        if path.exists():
            return path
        raise SystemExit(f"CHROME_BIN 指向的文件不存在：{path}")

    for hint in CHROME_HINTS:
        pattern = str(Path(hint).expanduser())
        for match in sorted(glob.glob(pattern), reverse=True):
            if Path(match).is_file():
                return Path(match)

    for name in ("chrome-headless-shell", "chromium", "google-chrome", "chrome"):
        which = shutil.which(name)
        if which:
            return Path(which)
    raise SystemExit("找不到 Chromium；请装一个或用 CHROME_BIN 指定可执行文件。")


def render(chrome: Path, html: Path, out: Path, width: int, height: int) -> None:
    if not html.is_file():
        raise SystemExit(f"缺少版式文件：{html}")
    with tempfile.TemporaryDirectory(prefix="retirenest-shot-") as profile:
        cmd = [
            str(chrome),
            "--no-sandbox",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--force-device-scale-factor=1",
            f"--window-size={width},{height}",
            f"--user-data-dir={profile}",
            f"--screenshot={out}",
            html.as_uri(),
        ]
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not out.is_file():
        raise SystemExit(
            f"渲染失败：{out.name}\nstdout: {done.stdout[-800:]}\nstderr: {done.stderr[-800:]}"
        )


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        head = handle.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"{path.name} 不是 PNG")
    width, height = struct.unpack(">II", head[16:24])
    return width, height


def main() -> int:
    chrome = find_chrome()
    print(f"chromium: {chrome}")

    failures: list[str] = []
    for name, source, target, width, height in TARGETS:
        html = ROOT / source
        out = ROOT / target
        render(chrome, html, out, width, height)
        got_w, got_h = png_size(out)
        size_mb = out.stat().st_size / 1024 / 1024
        bad = []
        if (got_w, got_h) != (width, height):
            bad.append(f"尺寸 {got_w}×{got_h}，应为 {width}×{height}")
        if size_mb >= 10:
            bad.append(f"体积 {size_mb:.2f} MB，超过 10 MB")
        status = "OK" if not bad else "FAIL " + "；".join(bad)
        print(f"{name:<7} {target:<11} {got_w}×{got_h}  {size_mb*1024:6.0f} KB  {status}")
        if bad:
            failures.append(name)

    if failures:
        print("有图片未通过校验：" + "、".join(failures))
        return 1
    print("两张图均符合提交要求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
