"""会话存储：内存默认，SQLite 可选。

会话按 `owner` 隔离：配置了 Bearer 后，owner 是 token 对应的用户；未配置时
owner 为 None，所有请求共享。SQLite 模式适合单进程重启恢复，不解决多 worker
并发；同一进程内的会话锁由 store 统一提供。
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from agent.errors import AgentSessionNotFound

DEFAULT_TTL_SECONDS = 3600
DEFAULT_MAX_SESSIONS = 100


@dataclass
class Session:
    """一段对话的消息历史；system prompt 每次请求现拼，不存这里。"""

    id: str
    owner: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    updated_at: float = field(default_factory=time.time)


class SessionBackend(Protocol):
    """内存与 SQLite 存储的共同接口。"""

    def get(self, session_id: str, owner: str | None = None) -> Session | None: ...

    def get_or_create(
        self,
        session_id: str | None = None,
        owner: str | None = None,
    ) -> Session: ...

    def reset(self, session_id: str, owner: str | None = None) -> bool: ...

    def save(self, session: Session) -> None: ...

    @property
    def count(self) -> int: ...


class SessionStore:
    """带 TTL 与容量上限的内存会话表。"""

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("会话 TTL 必须大于 0。")
        if max_sessions <= 0:
            raise ValueError("最大会话数必须大于 0。")
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def get(self, session_id: str, owner: str | None = None) -> Session | None:
        with self._lock:
            self._evict(time.time())
            session = self._sessions.get(session_id)
            if session is None or session.owner != owner:
                return None
            return session

    def get_or_create(
        self,
        session_id: str | None = None,
        owner: str | None = None,
    ) -> Session:
        now = time.time()
        with self._lock:
            self._evict(now)
            if session_id:
                existing = self._sessions.get(session_id)
                if existing is not None:
                    if existing.owner != owner:
                        raise AgentSessionNotFound()
                    existing.updated_at = now
                    return existing
            new_id = session_id or uuid.uuid4().hex
            session = Session(id=new_id, owner=owner, updated_at=now)
            self._sessions[new_id] = session
            self._evict(now)
            return session

    def reset(self, session_id: str, owner: str | None = None) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.owner != owner:
                return False
            del self._sessions[session_id]
            return True

    def save(self, session: Session) -> None:
        with self._lock:
            current = self._sessions.get(session.id)
            if current is None or current.owner != session.owner:
                raise AgentSessionNotFound()
            session.updated_at = time.time()
            self._sessions[session.id] = session

    @property
    def count(self) -> int:
        with self._lock:
            self._evict(time.time())
            return len(self._sessions)

    def _evict(self, now: float) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.updated_at > self._ttl
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
        while len(self._sessions) > self._max_sessions:
            oldest = min(self._sessions.values(), key=lambda session: session.updated_at)
            self._sessions.pop(oldest.id, None)


class SqliteSessionStore:
    """SQLite 会话表；适合单进程重启恢复。"""

    def __init__(
        self,
        path: str,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        max_sessions: int = DEFAULT_MAX_SESSIONS,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("会话 TTL 必须大于 0。")
        if max_sessions <= 0:
            raise ValueError("最大会话数必须大于 0。")
        if not path:
            raise ValueError("SQLite 路径不能为空。")

        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._path = path
        self._lock = threading.Lock()
        self._session_locks: dict[str, threading.Lock] = {}
        self._session_locks_guard = threading.Lock()

        if path != ":memory:":
            db_path = Path(path).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._path = str(db_path)

        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    owner TEXT,
                    messages TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_owner ON sessions(owner)"
            )
            self._conn.commit()

    @property
    def path(self) -> str:
        return self._path

    def get(self, session_id: str, owner: str | None = None) -> Session | None:
        with self._lock:
            self._evict(time.time())
            row = self._conn.execute(
                "SELECT id, owner, messages, updated_at FROM sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None or row["owner"] != owner:
                return None
            return self._row_to_session(row)

    def get_or_create(
        self,
        session_id: str | None = None,
        owner: str | None = None,
    ) -> Session:
        now = time.time()
        with self._lock:
            self._evict(now)
            if session_id:
                row = self._conn.execute(
                    "SELECT id, owner, messages, updated_at FROM sessions WHERE id = ?",
                    (session_id,),
                ).fetchone()
                if row is not None:
                    if row["owner"] != owner:
                        raise AgentSessionNotFound()
                    self._conn.execute(
                        "UPDATE sessions SET updated_at = ? WHERE id = ?",
                        (now, session_id),
                    )
                    self._conn.commit()
                    return Session(
                        id=session_id,
                        owner=owner,
                        messages=json.loads(row["messages"]),
                        lock=self._lock_for(session_id),
                        updated_at=now,
                    )
            new_id = session_id or uuid.uuid4().hex
            self._conn.execute(
                "INSERT INTO sessions (id, owner, messages, updated_at) VALUES (?, ?, ?, ?)",
                (new_id, owner, "[]", now),
            )
            self._conn.commit()
            self._evict(now)
            return Session(
                id=new_id,
                owner=owner,
                lock=self._lock_for(new_id),
                updated_at=now,
            )

    def reset(self, session_id: str, owner: str | None = None) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM sessions WHERE id = ? AND owner IS ?",
                (session_id, owner),
            )
            self._conn.commit()
            return cursor.rowcount > 0

    def save(self, session: Session) -> None:
        with self._lock:
            cursor = self._conn.execute(
                """
                UPDATE sessions SET messages = ?, updated_at = ?
                WHERE id = ? AND owner IS ?
                """,
                (
                    json.dumps(session.messages, ensure_ascii=False),
                    session.updated_at,
                    session.id,
                    session.owner,
                ),
            )
            self._conn.commit()
            if cursor.rowcount == 0:
                raise AgentSessionNotFound()

    @property
    def count(self) -> int:
        with self._lock:
            self._evict(time.time())
            row = self._conn.execute("SELECT COUNT(*) AS total FROM sessions").fetchone()
            return int(row["total"])

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _row_to_session(self, row: sqlite3.Row) -> Session:
        return Session(
            id=row["id"],
            owner=row["owner"],
            messages=json.loads(row["messages"]),
            lock=self._lock_for(row["id"]),
            updated_at=row["updated_at"],
        )

    def _lock_for(self, session_id: str) -> threading.Lock:
        with self._session_locks_guard:
            return self._session_locks.setdefault(session_id, threading.Lock())

    def _evict(self, now: float) -> None:
        cutoff = now - self._ttl
        self._conn.execute("DELETE FROM sessions WHERE updated_at < ?", (cutoff,))
        row = self._conn.execute("SELECT COUNT(*) AS total FROM sessions").fetchone()
        total = int(row["total"])
        excess = total - self._max_sessions
        if excess > 0:
            self._conn.execute(
                """
                DELETE FROM sessions
                WHERE id IN (
                    SELECT id FROM sessions ORDER BY updated_at ASC LIMIT ?
                )
                """,
                (excess,),
            )
        self._conn.commit()
