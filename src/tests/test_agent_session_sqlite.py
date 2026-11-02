"""SQLite 会话存储：持久化、owner 隔离、TTL 与容量。"""

from __future__ import annotations

import time

import pytest

import agent.session as session_module
from agent import AgentSessionNotFound, Session, SqliteSessionStore


def test_messages_survive_store_restart(tmp_path) -> None:
    path = str(tmp_path / "sessions.sqlite3")
    store = SqliteSessionStore(path)
    session = store.get_or_create("s1", owner="alice")
    session.messages = [{"role": "user", "content": "你好"}]
    session.updated_at = time.time()
    store.save(session)
    store.close()

    reopened = SqliteSessionStore(path)
    loaded = reopened.get("s1", "alice")
    assert loaded is not None
    assert loaded.messages == [{"role": "user", "content": "你好"}]
    assert loaded.owner == "alice"
    reopened.close()


def test_owner_isolation(tmp_path) -> None:
    store = SqliteSessionStore(str(tmp_path / "sessions.sqlite3"))
    store.get_or_create("s1", owner="alice")

    assert store.get("s1", "bob") is None
    assert store.reset("s1", "bob") is False
    with pytest.raises(AgentSessionNotFound):
        store.get_or_create("s1", owner="bob")
    assert store.reset("s1", "alice") is True
    store.close()


def test_no_owner_session_can_be_reset(tmp_path) -> None:
    store = SqliteSessionStore(str(tmp_path / "sessions.sqlite3"))
    store.get_or_create("s1", owner=None)
    assert store.reset("s1", owner=None) is True
    store.close()


def test_ttl_expires_sessions(monkeypatch, tmp_path) -> None:
    now = [0.0]
    monkeypatch.setattr(session_module.time, "time", lambda: now[0])
    store = SqliteSessionStore(str(tmp_path / "sessions.sqlite3"), ttl_seconds=10)
    store.get_or_create("a")
    assert store.count == 1
    now[0] = 11
    assert store.count == 0
    store.close()


def test_capacity_evicts_oldest(monkeypatch, tmp_path) -> None:
    now = [0.0]
    monkeypatch.setattr(session_module.time, "time", lambda: now[0])
    store = SqliteSessionStore(
        str(tmp_path / "sessions.sqlite3"),
        ttl_seconds=100,
        max_sessions=2,
    )
    store.get_or_create("a")
    now[0] = 1
    store.get_or_create("b")
    now[0] = 2
    store.get_or_create("c")

    assert store.count == 2
    assert store.get("a") is None
    assert store.get("b") is not None
    assert store.get("c") is not None
    store.close()


def test_memory_path_works() -> None:
    store = SqliteSessionStore(":memory:")
    session = store.get_or_create("s1")
    assert session.id == "s1"
    assert store.get("s1").id == "s1"  # type: ignore[union-attr]
    store.close()


def test_same_session_shares_a_lock(tmp_path) -> None:
    store = SqliteSessionStore(str(tmp_path / "sessions.sqlite3"))
    store.get_or_create("s1", owner="alice")
    first = store.get("s1", "alice")
    second = store.get("s1", "alice")
    assert first is not None and second is not None
    assert first.lock is second.lock
    store.close()


def test_save_missing_session_raises(tmp_path) -> None:
    store = SqliteSessionStore(str(tmp_path / "sessions.sqlite3"))
    with pytest.raises(AgentSessionNotFound):
        store.save(Session(id="missing"))
    store.close()


def test_empty_path_is_rejected() -> None:
    with pytest.raises(ValueError):
        SqliteSessionStore("")
