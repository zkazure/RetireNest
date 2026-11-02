"""配置、会话、服务与消息裁剪用例。"""

from __future__ import annotations

import json

import pytest

import agent.session as session_module
from agent import (
    AgentDisabled,
    AgentService,
    AssistantTurn,
    LLMConfig,
    ScriptedChatClient,
    SessionStore,
    ToolCall,
    trim_messages,
)
from agent.client import OpenAIChatClient


def test_config_disabled_by_default() -> None:
    config = LLMConfig()
    assert config.enabled is False
    assert config.missing == ("RETIRENEST_LLM_API_KEY", "RETIRENEST_LLM_MODEL")
    assert "api_key" not in repr(config)


def test_config_from_env_reads_all_values() -> None:
    config = LLMConfig.from_env(
        {
            "RETIRENEST_LLM_API_KEY": "secret",
            "RETIRENEST_LLM_MODEL": "deepseek-chat",
            "RETIRENEST_LLM_BASE_URL": "https://api.deepseek.com",
        }
    )
    assert config.enabled is True
    assert config.api_key == "secret"
    assert config.model == "deepseek-chat"
    assert config.base_url == "https://api.deepseek.com"
    assert config.timeout_seconds == 60


def test_config_ignores_blank_values_and_bad_timeout() -> None:
    config = LLMConfig.from_env(
        {
            "RETIRENEST_LLM_API_KEY": "  ",
            "RETIRENEST_LLM_MODEL": "",
            "RETIRENEST_LLM_BASE_URL": "",
            "RETIRENEST_LLM_TIMEOUT_SECONDS": "not-a-number",
        }
    )
    assert config.enabled is False
    assert config.api_key is None
    assert config.model is None
    assert config.base_url is None
    assert config.timeout_seconds == 60


def test_config_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError):
        LLMConfig(api_key="k", model="m", timeout_seconds=0)


def test_openai_client_requires_config() -> None:
    with pytest.raises(ValueError):
        OpenAIChatClient(LLMConfig())


def test_service_from_env_is_disabled_without_keys() -> None:
    service = AgentService.from_env({})
    assert service.config.enabled is False
    with pytest.raises(AgentDisabled):
        _ = service.client


def test_service_disabled_raises_without_creating_session() -> None:
    service = AgentService(LLMConfig())
    with pytest.raises(AgentDisabled):
        service.chat(None, "你好")
    assert service.sessions.count == 0


def test_service_chat_returns_reply_and_stores_messages() -> None:
    fake = ScriptedChatClient(
        [
            AssistantTurn("先告诉我你的年龄。", ()),
            AssistantTurn("好的，我记下了。", ()),
        ]
    )
    service = AgentService(LLMConfig(api_key="k", model="fake"), client=fake)

    reply = service.chat(None, "我想规划退休")
    assert reply.reply == "先告诉我你的年龄。"
    assert reply.tool_calls == ()
    assert reply.warnings == ()
    assert reply.model == "fake"
    assert reply.session_id

    session = service.sessions.get(reply.session_id)
    assert session is not None
    assert [message["role"] for message in session.messages] == ["user", "assistant"]

    second = service.chat(reply.session_id, "我 30 岁")
    assert second.reply == "好的，我记下了。"
    assert len(fake.requests) == 2
    second_messages = fake.requests[1]["messages"]
    assert second_messages[0]["role"] == "system"
    assert second_messages[1]["content"] == "我想规划退休"
    assert second_messages[2]["content"] == "先告诉我你的年龄。"
    assert second_messages[3]["content"] == "我 30 岁"


def test_service_persists_tool_context_for_next_turn() -> None:
    call = ToolCall(
        id="call_1",
        name="savings_project",
        arguments=json.dumps(
            {
                "current_savings": 100_000,
                "monthly_contribution": 1_000,
                "annual_return_pct": 5,
                "inflation_pct": 2,
                "years": 10,
            }
        ),
    )
    fake = ScriptedChatClient(
        [
            AssistantTurn(None, (call,)),
            AssistantTurn("约 27 万元。", ()),
            AssistantTurn("上一轮按 10 年算的。", ()),
        ]
    )
    service = AgentService(LLMConfig(api_key="k", model="fake"), client=fake)
    first = service.chat(None, "每月存 1000，10 年后多少？")
    assert first.tool_calls[0]["ok"] is True

    service.chat(first.session_id, "你刚才算的是多少年？")
    messages = fake.requests[2]["messages"]
    roles = [message["role"] for message in messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "user"]
    assert messages[3]["content"].startswith('{"ok": true')


def test_service_reset_removes_session() -> None:
    service = AgentService(LLMConfig(), sessions=SessionStore())
    session = service.sessions.get_or_create("abc")
    assert session.id == "abc"
    assert service.reset("abc") is True
    assert service.reset("abc") is False


def test_session_store_generates_and_reuses_ids() -> None:
    store = SessionStore()
    first = store.get_or_create(None)
    assert len(first.id) == 32
    assert store.get_or_create(first.id) is first
    named = store.get_or_create("custom")
    assert named.id == "custom"


def test_session_store_expires_by_ttl(monkeypatch) -> None:
    now = [0.0]
    monkeypatch.setattr(session_module.time, "time", lambda: now[0])
    store = SessionStore(ttl_seconds=10, max_sessions=5)
    store.get_or_create("a")
    assert store.count == 1
    now[0] = 11
    assert store.count == 0


def test_session_store_evicts_oldest(monkeypatch) -> None:
    now = [0.0]
    monkeypatch.setattr(session_module.time, "time", lambda: now[0])
    store = SessionStore(ttl_seconds=100, max_sessions=2)
    store.get_or_create("a")
    now[0] = 1
    store.get_or_create("b")
    now[0] = 2
    store.get_or_create("c")
    assert store.count == 2
    assert store.get("a") is None
    assert store.get("b") is not None
    assert store.get("c") is not None


def test_trim_messages_keeps_a_user_start() -> None:
    messages = [{"role": "tool", "content": "old"}]
    for index in range(5):
        messages.append({"role": "user", "content": f"u{index}"})
        messages.append({"role": "assistant", "content": f"a{index}"})
        messages.append({"role": "tool", "content": f"t{index}"})
    trimmed = trim_messages(messages, max_messages=4)
    assert len(trimmed) <= 4
    assert trimmed[0]["role"] == "user"
    assert trimmed[-1] == messages[-1]


def test_trim_messages_keeps_short_history() -> None:
    messages = [{"role": "user", "content": "hi"}]
    assert trim_messages(messages, max_messages=10) == messages
    with pytest.raises(ValueError):
        trim_messages(messages, max_messages=0)


def test_trim_messages_falls_back_when_no_user_message() -> None:
    messages = [{"role": "assistant", "content": str(index)} for index in range(10)]
    trimmed = trim_messages(messages, max_messages=3)
    assert trimmed == messages[-3:]
