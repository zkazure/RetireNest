"""run.py 的跨平台端口清理：解析、平台分派与 kill 参数拼装。"""

from __future__ import annotations

import importlib.util
import signal
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_run() -> ModuleType:
    spec = importlib.util.spec_from_file_location("retirenest_run", ROOT / "run.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


run = _load_run()

NETSTAT = """\
活动连接

  协议  本地地址          外部地址        状态           PID
  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       4321
  TCP    0.0.0.0:5173           0.0.0.0:0              LISTENING       8765
  TCP    [::]:8000              [::]:0                 LISTENING       4321
  TCP    127.0.0.1:8000         127.0.0.1:54321        ESTABLISHED     9001
  TCP    127.0.0.1:18000        0.0.0.0:0              LISTENING       1111
"""

SS = """\
State      Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN     0      511        127.0.0.1:8000       0.0.0.0:*    users:(("uvicorn",pid=4321,fd=12))
LISTEN     0      511        127.0.0.1:5173       0.0.0.0:*    users:(("node",pid=8765,fd=23))
"""


@pytest.mark.parametrize(
    ("port", "expected"),
    [(8000, [4321]), (5173, [8765]), (18000, [1111]), (9999, [])],
)
def test_parse_windows_netstat(port: int, expected: list[int]) -> None:
    assert run.parse_windows_netstat(NETSTAT, port) == expected


def test_parse_windows_netstat_ignores_established_and_headers() -> None:
    # ESTABLISHED 行的本地端口同样是 8000，但 PID 9001 不应被当成监听进程。
    assert 9001 not in run.parse_windows_netstat(NETSTAT, 8000)


def test_parse_lsof() -> None:
    assert run.parse_lsof("4321\n8765\n\n") == [4321, 8765]
    assert run.parse_lsof("") == []


def test_parse_ss() -> None:
    assert run.parse_ss(SS) == [4321, 8765]
    assert run.parse_ss("") == []


def test_listener_pids_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_capture(command: list[str]) -> str:
        calls.append(command)
        return NETSTAT

    monkeypatch.setattr(run, "IS_WINDOWS", True)
    monkeypatch.setattr(run, "run_capture", fake_capture)

    assert run.listener_pids(8000) == [4321]
    assert calls == [["netstat", "-ano", "-p", "tcp"]]


def test_listener_pids_posix_uses_lsof(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_capture(command: list[str]) -> str:
        calls.append(command)
        return "4321\n"

    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.shutil, "which", lambda name: "/usr/bin/lsof" if name == "lsof" else None)
    monkeypatch.setattr(run, "run_capture", fake_capture)

    assert run.listener_pids(8000) == [4321]
    assert calls == [["lsof", "-ti", "tcp:8000", "-sTCP:LISTEN"]]


def test_listener_pids_posix_falls_back_to_ss(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_capture(command: list[str]) -> str:
        calls.append(command)
        return SS

    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.shutil, "which", lambda name: "/usr/bin/ss" if name == "ss" else None)
    monkeypatch.setattr(run, "run_capture", fake_capture)

    assert run.listener_pids(8000) == [4321, 8765]
    assert calls == [["ss", "-ltnp"]]


def test_listener_pids_without_any_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.shutil, "which", lambda name: None)
    monkeypatch.setattr(run, "run_capture", lambda command: pytest.fail("不该执行查询命令"))

    assert run.listener_pids(8000) == []


def test_kill_pids_windows_uses_taskkill_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> None:
        calls.append(command)

    monkeypatch.setattr(run, "IS_WINDOWS", True)
    monkeypatch.setattr(run.subprocess, "run", fake_run)

    run.kill_pids([11, 22])

    assert calls == [
        ["taskkill", "/F", "/T", "/PID", "11"],
        ["taskkill", "/F", "/T", "/PID", "22"],
    ]


def test_kill_pids_posix_uses_sigterm_then_sigkill(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[tuple[int, int]] = []

    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.os, "kill", lambda pid, sig: sent.append((pid, sig)))

    run.kill_pids([7])
    run.kill_pids([8], force=True)

    assert sent == [(7, signal.SIGTERM), (8, signal.SIGKILL)]


def test_kill_pids_reports_permission_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def deny(pid: int, sig: int) -> None:
        raise PermissionError

    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.os, "kill", deny)

    run.kill_pids([7])

    assert "无法结束进程 7：权限不足" in capsys.readouterr().out


def test_stop_port_terms_and_returns(monkeypatch: pytest.MonkeyPatch) -> None:
    state = {"alive": True}
    killed: list[tuple[list[int], bool]] = []

    def fake_listener(port: int) -> list[int]:
        return [4321] if state["alive"] else []

    def fake_kill(pids: list[int], force: bool = False) -> None:
        killed.append((list(pids), force))
        state["alive"] = False

    monkeypatch.setattr(run, "listener_pids", fake_listener)
    monkeypatch.setattr(run, "kill_pids", fake_kill)

    assert run.stop_port(8000, timeout=0) is True
    assert killed == [([4321], False)]


def test_stop_port_forces_when_still_listening(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[tuple[list[int], bool]] = []

    monkeypatch.setattr(run, "listener_pids", lambda port: [4321])
    monkeypatch.setattr(
        run,
        "kill_pids",
        lambda pids, force=False: killed.append((list(pids), force)),
    )

    assert run.stop_port(8000, timeout=0) is True
    assert killed == [([4321], False), ([4321], True)]


def test_stop_port_without_listener(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "listener_pids", lambda port: [])
    monkeypatch.setattr(run, "kill_pids", lambda pids, force=False: pytest.fail("不该结束进程"))

    assert run.stop_port(8000, timeout=0) is False


def test_stop_ports_without_lsof_or_ss(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run, "IS_WINDOWS", False)
    monkeypatch.setattr(run.shutil, "which", lambda name: None)
    monkeypatch.setattr(run, "stop_port", lambda port, timeout=0: pytest.fail("不该处理端口"))

    run.stop_ports([8000])

    assert "找不到 lsof 或 ss" in capsys.readouterr().out


def test_parse_args_stop_defaults() -> None:
    args = run.parse_args(["--stop"])

    assert args.stop is True
    assert args.ports is None
    assert args.prod is False
    assert args.no_open is False


def test_parse_args_ports() -> None:
    args = run.parse_args(["--stop", "--ports", "18000", "18001"])

    assert args.ports == [18000, 18001]


def test_parse_args_default_is_dev_mode() -> None:
    args = run.parse_args([])

    assert args.stop is False
    assert args.ports is None


def test_load_env_file_reads_pairs(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    path.write_text(
        "# 注释行\n"
        "\n"
        "RETIRENEST_LLM_API_KEY=sk-local\n"
        "  RETIRENEST_LLM_MODEL = deepseek-chat  \n"
        "export RETIRENEST_LLM_BASE_URL=https://api.example.com/v1\n",
        encoding="utf-8",
    )
    environ: dict[str, str] = {}

    applied = run.load_env_file(path, environ)

    assert applied == [
        "RETIRENEST_LLM_API_KEY",
        "RETIRENEST_LLM_MODEL",
        "RETIRENEST_LLM_BASE_URL",
    ]
    assert environ == {
        "RETIRENEST_LLM_API_KEY": "sk-local",
        "RETIRENEST_LLM_MODEL": "deepseek-chat",
        "RETIRENEST_LLM_BASE_URL": "https://api.example.com/v1",
    }


def test_load_env_file_strips_paired_quotes(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    path.write_text('A="sk-quoted"\nB=\'single\'\nC="mismatch\'\n', encoding="utf-8")
    environ: dict[str, str] = {}

    assert run.load_env_file(path, environ) == ["A", "B", "C"]
    assert environ == {"A": "sk-quoted", "B": "single", "C": "\"mismatch'"}


def test_load_env_file_skips_blank_values_and_malformed_lines(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    path.write_text("EMPTY=\n无等号\n=没有变量名\nOK=1\n", encoding="utf-8")
    environ: dict[str, str] = {}

    assert run.load_env_file(path, environ) == ["OK"]
    assert environ == {"OK": "1"}


def test_load_env_file_does_not_override_existing(tmp_path: Path) -> None:
    path = tmp_path / ".env.local"
    path.write_text("RETIRENEST_LLM_MODEL=from-file\n", encoding="utf-8")
    environ = {"RETIRENEST_LLM_MODEL": "from-shell"}

    assert run.load_env_file(path, environ) == []
    assert environ == {"RETIRENEST_LLM_MODEL": "from-shell"}


def test_load_env_file_without_file(tmp_path: Path) -> None:
    environ: dict[str, str] = {}

    assert run.load_env_file(tmp_path / ".env.local", environ) == []
    assert environ == {}


def test_load_env_file_returns_names_only(tmp_path: Path) -> None:
    # 返回值用于打印提示，只有变量名，不会把密钥带进日志。
    path = tmp_path / ".env.local"
    path.write_text("RETIRENEST_LLM_API_KEY=sk-secret\n", encoding="utf-8")

    applied = run.load_env_file(path, {})

    assert applied == ["RETIRENEST_LLM_API_KEY"]
    assert all("sk-secret" not in name for name in applied)


def test_main_stop_skips_tool_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    stopped: list[list[int]] = []

    def fake_stop_ports(ports: list[int], timeout: float = 5.0) -> None:
        stopped.append(list(ports))

    monkeypatch.setattr(run, "stop_ports", fake_stop_ports)
    monkeypatch.setattr(run, "find_tool", lambda name, hint: pytest.fail("--stop 不该检查外部工具"))

    assert run.main(["--stop"]) == 0
    assert stopped == [[8000, 5173]]

    assert run.main(["--stop", "--ports", "18000"]) == 0
    assert stopped == [[8000, 5173], [18000]]


def test_main_rejects_ports_without_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(run, "stop_ports", lambda ports, timeout=5.0: pytest.fail("不该清理端口"))
    monkeypatch.setattr(run, "find_tool", lambda name, hint: pytest.fail("不该检查外部工具"))

    with pytest.raises(SystemExit):
        run.main(["--ports", "18000"])
