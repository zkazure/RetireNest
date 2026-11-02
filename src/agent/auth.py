"""轻量 Bearer 访问控制。

不是账号体系：只把 token 映射到用户名，用于按用户隔离会话。配置了但解析不出
任何合法 token 时保持 fail closed（所有请求 401），不会悄悄退回无鉴权。
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field

from agent.errors import AgentUnauthorized

TOKENS_ENV = "RETIRENEST_AGENT_TOKENS"
TOKEN_ENV = "RETIRENEST_AGENT_TOKEN"


@dataclass(frozen=True, slots=True)
class AgentAuth:
    """token 到用户的映射；`configured` 区分“未启用”和“启用但配置为空”。"""

    tokens: Mapping[str, str] = field(default_factory=dict, repr=False)
    configured: bool = False

    @property
    def enabled(self) -> bool:
        return self.configured

    def user_for(self, token: str | None) -> str | None:
        if not self.configured:
            return None
        if not token:
            raise AgentUnauthorized("缺少访问令牌。")
        for known, user in self.tokens.items():
            if secrets.compare_digest(known, token):
                return user
        raise AgentUnauthorized("访问令牌无效。")

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> AgentAuth:
        source = os.environ if environ is None else environ
        raw_tokens = source.get(TOKENS_ENV, "").strip()
        single = source.get(TOKEN_ENV, "").strip()
        if raw_tokens:
            return cls(tokens=_parse_tokens(raw_tokens), configured=True)
        if single:
            return cls(tokens={single: "default"}, configured=True)
        return cls()


def _parse_tokens(raw: str) -> dict[str, str]:
    """解析 `token:user,token2:user2`；坏条目跳过，合法条目为空则 fail closed。"""
    tokens: dict[str, str] = {}
    for item in raw.split(","):
        part = item.strip()
        if not part or ":" not in part:
            continue
        token, user = part.split(":", 1)
        token = token.strip()
        user = user.strip() or "default"
        if token:
            tokens[token] = user
    return tokens
