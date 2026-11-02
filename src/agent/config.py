"""模型服务配置；只从环境变量读取，不把 key 写进日志或响应。"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

API_KEY_ENV = "RETIRENEST_LLM_API_KEY"
MODEL_ENV = "RETIRENEST_LLM_MODEL"
BASE_URL_ENV = "RETIRENEST_LLM_BASE_URL"
TIMEOUT_ENV = "RETIRENEST_LLM_TIMEOUT_SECONDS"
DEFAULT_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class LLMConfig:
    """OpenAI 兼容服务的连接参数。

    任何一项缺失都会关闭 Agent；`missing` 给出具体的环境变量名。
    """

    api_key: str | None = field(default=None, repr=False)
    model: str | None = None
    base_url: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("模型超时时间必须大于 0。")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def with_overrides(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> LLMConfig:
        """用请求头里的值补一份临时配置；没给的项沿用服务端配置。"""
        return LLMConfig(
            api_key=api_key or self.api_key,
            model=model or self.model,
            base_url=base_url or self.base_url,
            timeout_seconds=self.timeout_seconds,
        )

    def describe(self) -> dict[str, object]:
        """给设置页看的非敏感状态：不回显 key，只说明是否可用。"""
        host = None
        if self.base_url:
            from urllib.parse import urlparse

            host = urlparse(self.base_url).hostname
        return {
            "enabled": self.enabled,
            "model": self.model,
            "base_url_host": host,
            "missing": list(self.missing),
        }

    @property
    def missing(self) -> tuple[str, ...]:
        missing = []
        if not self.api_key:
            missing.append(API_KEY_ENV)
        if not self.model:
            missing.append(MODEL_ENV)
        return tuple(missing)

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> LLMConfig:
        source = os.environ if environ is None else environ
        timeout_raw = source.get(TIMEOUT_ENV, "").strip()
        timeout = DEFAULT_TIMEOUT_SECONDS
        if timeout_raw:
            try:
                timeout = float(timeout_raw)
            except ValueError:
                # 可选的超时配置写错时退回默认值，不能让整个服务起不来。
                timeout = DEFAULT_TIMEOUT_SECONDS
        return cls(
            api_key=source.get(API_KEY_ENV, "").strip() or None,
            model=source.get(MODEL_ENV, "").strip() or None,
            base_url=source.get(BASE_URL_ENV, "").strip() or None,
            timeout_seconds=timeout,
        )
