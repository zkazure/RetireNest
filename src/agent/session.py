"""内存会话存储。

单进程 uvicorn 可用；重启即丢失，不落库。会话级锁保证同一会话的请求串行，
避免两条消息同时改同一份历史。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

DEFAULT_TTL_SECONDS = 3600
DEFAULT_MAX_SESSIONS = 100


@dataclass
class Session:
    """一段对话的消息历史；system prompt 每次请求现拼，不存这里。"""

    id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    updated_at: float = field(default_factory=time.monotonic)


class SessionStore:
    """带 TTL 与容量上限的会话表。"""

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

    def get(self, session_id: str) -> Session | None:
        with self._lock:
            self._evict(time.monotonic())
            return self._sessions.get(session_id)

    def get_or_create(self, session_id: str | None = None) -> Session:
        now = time.monotonic()
        with self._lock:
            self._evict(now)
            if session_id:
                existing = self._sessions.get(session_id)
                if existing is not None:
                    existing.updated_at = now
                    return existing
            new_id = session_id or uuid.uuid4().hex
            session = Session(id=new_id, updated_at=now)
            self._sessions[new_id] = session
            self._evict(now)
            return session

    def reset(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    @property
    def count(self) -> int:
        with self._lock:
            self._evict(time.monotonic())
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
