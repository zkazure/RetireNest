"""OpenAI 兼容客户端的响应映射；不发网络请求。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent import AgentUpstreamError, LLMConfig
from agent.client import OpenAIChatClient


def make_client(response=None, error: Exception | None = None) -> OpenAIChatClient:
    class Completions:
        def create(self, **kwargs):
            if error is not None:
                raise error
            return response

    client = object.__new__(OpenAIChatClient)
    client._client = SimpleNamespace(  # type: ignore[attr-defined]
        chat=SimpleNamespace(completions=Completions())
    )
    client._model = "test-model"  # type: ignore[attr-defined]
    return client


def test_text_response_is_mapped() -> None:
    message = SimpleNamespace(content="你好", tool_calls=None)
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    client = make_client(response)

    turn = client.complete([{"role": "user", "content": "hi"}], [])
    assert turn.content == "你好"
    assert turn.tool_calls == ()


def test_tool_calls_are_mapped() -> None:
    function = SimpleNamespace(name="savings_project", arguments='{"years": 10}')
    call = SimpleNamespace(id="call_1", function=function)
    message = SimpleNamespace(content=None, tool_calls=[call])
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    client = make_client(response)

    turn = client.complete([], [{"type": "function"}])
    assert turn.content is None
    assert len(turn.tool_calls) == 1
    assert turn.tool_calls[0].id == "call_1"
    assert turn.tool_calls[0].name == "savings_project"
    assert turn.tool_calls[0].arguments == '{"years": 10}'


def test_tool_call_without_function_is_skipped() -> None:
    call = SimpleNamespace(id="call_1", function=None)
    message = SimpleNamespace(content="x", tool_calls=[call])
    response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
    client = make_client(response)

    turn = client.complete([], [])
    assert turn.tool_calls == ()


def test_empty_choices_is_upstream_error() -> None:
    client = make_client(SimpleNamespace(choices=[]))
    with pytest.raises(AgentUpstreamError):
        client.complete([], [])


def test_provider_exception_becomes_upstream_error() -> None:
    client = make_client(error=RuntimeError("boom"))
    with pytest.raises(AgentUpstreamError):
        client.complete([], [])


def test_client_requires_model_and_key() -> None:
    with pytest.raises(ValueError):
        OpenAIChatClient(LLMConfig())
