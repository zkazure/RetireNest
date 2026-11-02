"""Agent 层的可预期错误。"""

from __future__ import annotations


class AgentError(Exception):
    """Agent 错误的基类；HTTP 状态码由 API 层读取。"""

    status = 500
    code = "AGENT_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AgentDisabled(AgentError):
    """未配置模型服务时关闭 Agent，不影响其它端点。"""

    status = 503
    code = "AGENT_DISABLED"

    def __init__(self, missing: tuple[str, ...] = ()) -> None:
        self.missing = missing
        if missing:
            detail = "、".join(missing)
            message = f"Agent 未配置：请设置 {detail} 后重试。"
        else:
            message = "Agent 未配置：请设置模型服务后重试。"
        super().__init__(message)


class AgentUpstreamError(AgentError):
    """模型服务调用失败。"""

    status = 502
    code = "AGENT_UPSTREAM_ERROR"

    def __init__(self, message: str = "模型服务暂时不可用，请稍后重试。") -> None:
        super().__init__(message)
