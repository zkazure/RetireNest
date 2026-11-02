"""Agent HTTP 端点：禁用、成功、工具轨迹、会话与错误映射。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agent import (
    AgentService,
    AgentUpstreamError,
    AssistantTurn,
    LLMConfig,
    ScriptedChatClient,
    ToolCall,
    tool_name,
)
from api.app import app
from commands import list_commands

client = TestClient(app)


@pytest.fixture(autouse=True)
def restore_agent_service():
    original = app.state.agent_service
    yield
    app.state.agent_service = original


def install(service: AgentService) -> AgentService:
    app.state.agent_service = service
    return service


def test_disabled_agent_returns_503() -> None:
    install(AgentService(LLMConfig()))
    response = client.post("/api/agent/chat", json={"message": "你好"})
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "AGENT_DISABLED"
    assert "RETIRENEST_LLM_API_KEY" in body["message"]


def test_missing_service_returns_503() -> None:
    app.state.agent_service = None
    response = client.post("/api/agent/chat", json={"message": "你好"})
    assert response.status_code == 503
    assert response.json()["code"] == "AGENT_DISABLED"


def test_chat_returns_reply_and_session_id() -> None:
    fake = ScriptedChatClient([AssistantTurn("先告诉我你的年龄。", ())])
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=fake))

    response = client.post("/api/agent/chat", json={"message": "我想规划退休"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reply"] == "先告诉我你的年龄。"
    assert body["model"] == "fake"
    assert body["session_id"]
    assert body["tool_calls"] == []
    assert body["warnings"] == []


def test_chat_returns_tool_trace() -> None:
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
            AssistantTurn("按假设约 27 万元。", ()),
        ]
    )
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=fake))

    response = client.post("/api/agent/chat", json={"message": "每月存 1000，10 年后多少？"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["tool_calls"]) == 1
    record = body["tool_calls"][0]
    assert record["command_id"] == "savings.project"
    assert record["ok"] is True
    assert record["outputs"]["future_balance_real"] > 0


def test_chat_continues_existing_session() -> None:
    fake = ScriptedChatClient(
        [
            AssistantTurn("先告诉我你的年龄。", ()),
            AssistantTurn("好的，我记下了。", ()),
        ]
    )
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=fake))

    first = client.post("/api/agent/chat", json={"message": "我想规划退休"})
    session_id = first.json()["session_id"]
    second = client.post(
        "/api/agent/chat",
        json={"session_id": session_id, "message": "我 30 岁"},
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id
    assert second.json()["reply"] == "好的，我记下了。"
    second_messages = fake.requests[1]["messages"]
    assert second_messages[1]["content"] == "我想规划退休"
    assert second_messages[2]["content"] == "先告诉我你的年龄。"


def test_chat_isolates_sessions() -> None:
    fake = ScriptedChatClient(
        [
            AssistantTurn("A 的回复", ()),
            AssistantTurn("B 的回复", ()),
        ]
    )
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=fake))

    first = client.post("/api/agent/chat", json={"message": "问题 A"})
    second = client.post("/api/agent/chat", json={"message": "问题 B"})
    assert first.status_code == second.status_code == 200
    assert first.json()["session_id"] != second.json()["session_id"]
    second_messages = fake.requests[1]["messages"]
    assert [message["role"] for message in second_messages] == ["system", "user"]
    assert second_messages[1]["content"] == "问题 B"


def test_upstream_error_returns_502() -> None:
    class BoomClient:
        def complete(self, messages, tools):
            raise AgentUpstreamError()

    install(AgentService(LLMConfig(api_key="k", model="fake"), client=BoomClient()))
    response = client.post("/api/agent/chat", json={"message": "你好"})
    assert response.status_code == 502
    assert response.json()["code"] == "AGENT_UPSTREAM_ERROR"


@pytest.mark.parametrize("command", list_commands(), ids=lambda command: command.manifest.id)
def test_agent_can_call_every_command(command) -> None:
    examples = command.manifest.examples
    if not examples:
        pytest.skip("该命令没有示例输入。")
    call = ToolCall(
        id="call_1",
        name=tool_name(command.manifest.id),
        arguments=json.dumps(examples[0]["inputs"], ensure_ascii=False),
    )
    fake = ScriptedChatClient(
        [
            AssistantTurn(None, (call,)),
            AssistantTurn("已拿到工具结果。", ()),
        ]
    )
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=fake))

    response = client.post("/api/agent/chat", json={"message": "执行示例"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["tool_calls"]) == 1
    record = body["tool_calls"][0]
    assert record["ok"] is True, record
    assert record["command_id"] == command.manifest.id
    assert record["outputs"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": ""},
        {"message": "   "},
        {"message": "a" * 4001},
        {"message": "你好", "extra": 1},
        {"message": "你好", "session_id": "bad id!"},
    ],
)
def test_invalid_requests_return_422(payload: dict) -> None:
    install(AgentService(LLMConfig(api_key="k", model="fake"), client=ScriptedChatClient([])))
    response = client.post("/api/agent/chat", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
