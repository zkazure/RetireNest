"""RetireNest 一键启动器。

开发模式：同时启动 FastAPI（8000）和 Vite（5173），保留热更新。
演示模式：构建前端后由 FastAPI 在 8000 单端口托管页面和 API。

用法：
    uv run --project src python run.py
    uv run --project src python run.py --prod
    uv run --project src python run.py --stop
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import MutableMapping
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
FRONTEND = ROOT / "frontend"
ENV_FILE = ROOT / ".env.local"
"""本地模型密钥；已被 gitignore，启动时补进进程环境。"""
HOST = "127.0.0.1"
API_PORT = 8000
WEB_PORT = 5173
STARTUP_TIMEOUT = 60.0
STOP_TIMEOUT = 5.0
IS_WINDOWS = os.name == "nt"


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
    if IS_WINDOWS:
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
        fail(
            f"{label}端口 {port} 已被占用，请先执行 make stop"
            f" 或 uv run --project src python run.py --stop。"
        )


def run_capture(command: list[str]) -> str:
    """执行只读的查询命令并返回 stdout；命令不存在或失败时返回空串。"""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace",
            check=False,
        )
    except OSError:
        return ""
    return result.stdout or ""


def parse_windows_netstat(text: str, port: int) -> list[int]:
    """从 `netstat -ano` 的 LISTENING 行里取出监听指定端口的 PID。"""
    pids: set[int] = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != "TCP":
            continue
        local, state, pid = parts[1], parts[3].upper(), parts[4]
        if state != "LISTENING" or local.rsplit(":", 1)[-1] != str(port):
            continue
        if pid.isdigit():
            pids.add(int(pid))
    return sorted(pids)


def parse_lsof(text: str) -> list[int]:
    """`lsof -ti` 每行一个 PID。"""
    return sorted({int(line.strip()) for line in text.splitlines() if line.strip().isdigit()})


def parse_ss(text: str) -> list[int]:
    """从 `ss -ltnp` 的 users:(("proc",pid=1234,fd=5)) 里取 PID。"""
    return sorted({int(pid) for pid in re.findall(r"pid=(\d+)", text)})


def listener_pids(port: int) -> list[int]:
    """返回监听指定端口的进程 PID，按平台选择 netstat / lsof / ss。"""
    if IS_WINDOWS:
        return parse_windows_netstat(run_capture(["netstat", "-ano", "-p", "tcp"]), port)
    if shutil.which("lsof"):
        return parse_lsof(run_capture(["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"]))
    if shutil.which("ss"):
        return parse_ss(run_capture(["ss", "-ltnp"]))
    return []


def kill_pids(pids: list[int], force: bool = False) -> None:
    """结束进程；Windows 用 taskkill 连同子进程，POSIX 先 SIGTERM 后 SIGKILL。"""
    for pid in pids:
        if IS_WINDOWS:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            continue
        try:
            os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            say(f"无法结束进程 {pid}：权限不足。")


def wait_until_free(port: int, timeout: float) -> list[int]:
    """等端口释放，返回超时后仍占用的 PID。"""
    deadline = time.monotonic() + timeout
    while True:
        pids = listener_pids(port)
        if not pids or time.monotonic() >= deadline:
            return pids
        time.sleep(0.2)


def stop_port(port: int, timeout: float = STOP_TIMEOUT) -> bool:
    """结束监听指定端口的进程；没有监听进程时静默返回 False。"""
    pids = listener_pids(port)
    if not pids:
        return False
    show = "、".join(str(pid) for pid in pids)
    say(f"停止端口 {port}：{show}")
    kill_pids(pids)
    left = wait_until_free(port, timeout)
    if left:
        say(f"强制结束端口 {port}：" + "、".join(str(pid) for pid in left))
        kill_pids(left, force=True)
        wait_until_free(port, timeout)
    return True


def stop_ports(ports: list[int], timeout: float = STOP_TIMEOUT) -> None:
    if not IS_WINDOWS and not shutil.which("lsof") and not shutil.which("ss"):
        say("找不到 lsof 或 ss，无法按端口查找进程；请安装 lsof 后重试。")
        return
    for port in ports:
        stop_port(port, timeout)


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
    if IS_WINDOWS:
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
    if IS_WINDOWS:
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
        if IS_WINDOWS:
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
            "  uv run --project src python run.py --stop\n"
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
    parser.add_argument(
        "--stop",
        action="store_true",
        help="只结束占用开发端口的进程后退出",
    )
    parser.add_argument(
        "--ports",
        nargs="+",
        type=int,
        metavar="PORT",
        help="配合 --stop 使用，默认 8000 5173",
    )
    return parser.parse_args(argv)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def load_env_file(
    path: Path = ENV_FILE,
    environ: MutableMapping[str, str] | None = None,
) -> list[str]:
    """把 `.env.local` 里的 `KEY=VALUE` 补进环境变量。

    已存在的变量不覆盖，方便在命令行临时 export 覆盖文件；空值等于没写。
    返回本次补进去的变量名，调用方只打印名字，不打印值。
    """
    target = os.environ if environ is None else environ
    if not path.is_file():
        return []
    applied: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()
        name, sep, value = line.partition("=")
        name = name.strip()
        if not sep or not name:
            continue
        value = _unquote(value.strip())
        if not value or name in target:
            continue
        target[name] = value
        applied.append(name)
    return applied


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
    if args.ports and not args.stop:
        fail("--ports 只能配合 --stop 使用。")
    if args.stop:
        stop_ports(args.ports or [API_PORT, WEB_PORT])
        return 0

    loaded = load_env_file()
    if loaded:
        say(f"从 .env.local 读取 {len(loaded)} 项环境变量：{'、'.join(loaded)}")

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
