"""RetireNest 一键启动器。

开发模式：同时启动 FastAPI（8000）和 Vite（5173），保留热更新。
演示模式：构建前端后由 FastAPI 在 8000 单端口托管页面和 API。

用法：
    uv run --project src python run.py
    uv run --project src python run.py --prod
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
FRONTEND = ROOT / "frontend"
HOST = "127.0.0.1"
API_PORT = 8000
WEB_PORT = 5173
STARTUP_TIMEOUT = 60.0


def say(message: str) -> None:
    print(f"[run] {message}", flush=True)


def fail(message: str, code: int = 1) -> NoReturn:
    print(f"[run] 错误：{message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def find_tool(name: str, hint: str) -> str:
    path = shutil.which(name)
    if path is None:
        fail(f"找不到 {name}。{hint}")
    return path


def npm_command(npm: str, *args: str) -> list[str]:
    """Windows 上 npm 是 .cmd，需要经过 cmd.exe 才能启动。"""
    if os.name == "nt":
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", npm, *args]
    return [npm, *args]


def run_checked(command: list[str], cwd: Path) -> None:
    say("执行：" + " ".join(command))
    try:
        subprocess.run(command, cwd=cwd, check=True)
    except FileNotFoundError as exc:
        fail(f"命令不存在：{exc.filename}")
    except subprocess.CalledProcessError as exc:
        fail(f"命令失败（退出码 {exc.returncode}）。")


def ensure_dependencies(uv: str, npm: str) -> None:
    say("同步后端依赖…")
    run_checked([uv, "sync", "--locked"], SRC)

    if (FRONTEND / "node_modules").is_dir():
        say("前端依赖已存在，跳过安装。")
        return

    installer = "ci" if (FRONTEND / "package-lock.json").is_file() else "install"
    say(f"安装前端依赖（npm {installer}）…")
    run_checked(npm_command(npm, installer), FRONTEND)


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((HOST, port)) == 0


def ensure_port_free(port: int, label: str) -> None:
    if port_in_use(port):
        fail(f"{label}端口 {port} 已被占用，请先停止占用该端口的进程。")


def pump(name: str, process: subprocess.Popen[str]) -> None:
    if process.stdout is None:
        return
    try:
        for line in process.stdout:
            print(f"[{name}] {line}", end="", flush=True)
    except (OSError, ValueError):
        pass


def spawn(name: str, command: list[str], cwd: Path) -> subprocess.Popen[str]:
    say(f"启动 {name}：{' '.join(command)}")
    options: dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True

    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **options,
    )
    threading.Thread(target=pump, args=(name, process), daemon=True).start()
    return process


def wait_for_port(name: str, port: int, process: subprocess.Popen[str]) -> None:
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            fail(f"{name} 启动失败（退出码 {code}）。")
        if port_in_use(port):
            return
        time.sleep(0.2)
    fail(f"等待 {name} 监听 {HOST}:{port} 超时（{STARTUP_TIMEOUT:.0f} 秒）。")


def terminate(name: str, process: subprocess.Popen[str] | None) -> None:
    if process is None or process.poll() is not None:
        return
    say(f"停止 {name}…")
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass

    try:
        process.wait(timeout=5)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        if os.name == "nt":
            process.kill()
        else:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            pass


def stop_all(processes: list[tuple[str, subprocess.Popen[str] | None]]) -> None:
    for name, process in processes:
        try:
            terminate(name, process)
        except KeyboardInterrupt:
            continue


def open_browser(url: str, no_open: bool) -> None:
    if no_open:
        say("已跳过自动打开浏览器。")
        return
    try:
        opened = webbrowser.open(url, new=2)
    except (OSError, webbrowser.Error):
        opened = False
    if not opened:
        say("无法自动打开浏览器，请手动访问上面的地址。")


def watch(processes: list[tuple[str, subprocess.Popen[str] | None]]) -> int:
    try:
        while True:
            for name, process in processes:
                if process is None:
                    continue
                code = process.poll()
                if code is not None:
                    say(f"{name} 已退出（退出码 {code}）。")
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[run] 收到 Ctrl+C，正在停止…", flush=True)
        return 0


def run_dev(uv: str, npm: str, no_open: bool) -> int:
    ensure_port_free(API_PORT, "后端")
    ensure_port_free(WEB_PORT, "前端")

    backend = spawn(
        "api",
        [
            uv,
            "run",
            "--no-sync",
            "uvicorn",
            "api.app:app",
            "--host",
            HOST,
            "--port",
            str(API_PORT),
        ],
        SRC,
    )
    frontend: subprocess.Popen[str] | None = None
    try:
        wait_for_port("后端", API_PORT, backend)
        frontend = spawn(
            "web",
            npm_command(npm, "run", "dev"),
            FRONTEND,
        )
        wait_for_port("前端", WEB_PORT, frontend)
        url = f"http://{HOST}:{WEB_PORT}/commands.html"
        say(f"开发模式已就绪：{url}")
        open_browser(url, no_open)
        return watch([("api", backend), ("web", frontend)])
    finally:
        stop_all([("api", backend), ("web", frontend)])


def run_prod(uv: str, npm: str, no_open: bool) -> int:
    ensure_port_free(API_PORT, "后端")
    say("构建前端…")
    run_checked(npm_command(npm, "run", "build"), FRONTEND)

    backend = spawn(
        "api",
        [
            uv,
            "run",
            "--no-sync",
            "uvicorn",
            "api.app:app",
            "--host",
            HOST,
            "--port",
            str(API_PORT),
        ],
        SRC,
    )
    try:
        wait_for_port("后端", API_PORT, backend)
        url = f"http://{HOST}:{API_PORT}/"
        say(f"演示模式已就绪：{url}")
        open_browser(url, no_open)
        return watch([("api", backend)])
    finally:
        stop_all([("api", backend)])


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RetireNest 一键启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  uv run --project src python run.py\n"
            "  uv run --project src python run.py --prod\n"
            "  uv run --project src python run.py --prod --no-open\n"
        ),
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="构建前端并由 FastAPI 在 8000 单端口托管",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="不自动打开浏览器",
    )
    return parser.parse_args(argv)


def _raise_keyboard_interrupt(_signum: int, _frame: object) -> None:
    raise KeyboardInterrupt


def install_signal_handlers() -> None:
    """确保后台启动或进程管理器发的信号也能走清理逻辑。"""
    try:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    except (OSError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    install_signal_handlers()
    args = parse_args(argv)
    uv = find_tool("uv", "请先安装 uv：https://docs.astral.sh/uv/")
    npm = find_tool("npm", "请先安装 Node.js（含 npm）：https://nodejs.org/")
    find_tool("node", "请先安装 Node.js（含 npm）：https://nodejs.org/")

    try:
        ensure_dependencies(uv, npm)
        if args.prod:
            return run_prod(uv, npm, args.no_open)
        return run_dev(uv, npm, args.no_open)
    except KeyboardInterrupt:
        print("\n[run] 收到 Ctrl+C，正在停止…", flush=True)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
