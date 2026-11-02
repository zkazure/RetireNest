"""Agent HTTP 端点：禁用、成功、工具轨迹、会话与错误映射。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from agent import (
    AgentAuth,
    AgentService,
    AgentUpstreamError,
    AssistantTurn,
    LLMConfig,
    ScriptedChatClient,
    SqliteSessionStore,
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


AUTH = AgentAuth(
    tokens={"tok-alice": "alice", "tok-bob": "bob"},
    configured=True,
)


def auth_service(turns: list[AssistantTurn]) -> AgentService:
    return AgentService(
        LLMConfig(api_key="k", model="fake"),
        client=ScriptedChatClient(turns),
        auth=AUTH,
    )


def bearer(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


def test_auth_is_required_and_token_maps_to_user() -> None:
    install(auth_service([AssistantTurn("你好。", ())]))
    assert client.post("/api/agent/chat", json={"message": "hi"}).status_code == 401
    assert (
        client.post(
            "/api/agent/chat",
            json={"message": "hi"},
            headers=bearer("wrong"),
        ).status_code
        == 401
    )
    ok = client.post(
        "/api/agent/chat",
        json={"message": "hi"},
        headers=bearer("tok-alice"),
    )
    assert ok.status_code == 200
    assert ok.json()["reply"] == "你好。"


def test_users_cannot_share_sessions() -> None:
    install(
        auth_service(
            [
                AssistantTurn("alice 第一次", ()),
                AssistantTurn("bob 的会话", ()),
                AssistantTurn("alice 第二次", ()),
            ]
        )
    )
    first = client.post(
        "/api/agent/chat",
        json={"message": "alice"},
        headers=bearer("tok-alice"),
    )
    session_id = first.json()["session_id"]

    stolen = client.post(
        "/api/agent/chat",
        json={"session_id": session_id, "message": "bob"},
        headers=bearer("tok-bob"),
    )
    assert stolen.status_code == 404
    assert stolen.json()["code"] == "AGENT_SESSION_NOT_FOUND"

    bob = client.post(
        "/api/agent/chat",
        json={"message": "bob"},
        headers=bearer("tok-bob"),
    )
    assert bob.status_code == 200
    assert bob.json()["reply"] == "bob 的会话"

    again = client.post(
        "/api/agent/chat",
        json={"session_id": session_id, "message": "again"},
        headers=bearer("tok-alice"),
    )
    assert again.status_code == 200
    assert again.json()["reply"] == "alice 第二次"


def test_delete_session_checks_owner() -> None:
    install(auth_service([AssistantTurn("先记下。", ())]))
    first = client.post(
        "/api/agent/chat",
        json={"message": "hi"},
        headers=bearer("tok-alice"),
    )
    session_id = first.json()["session_id"]

    denied = client.delete(
        f"/api/agent/sessions/{session_id}",
        headers=bearer("tok-bob"),
    )
    assert denied.status_code == 404

    deleted = client.delete(
        f"/api/agent/sessions/{session_id}",
        headers=bearer("tok-alice"),
    )
    assert deleted.status_code == 200
    assert deleted.json()["reset"] is True

    missing = client.delete(
        f"/api/agent/sessions/{session_id}",
        headers=bearer("tok-alice"),
    )
    assert missing.status_code == 404


def test_stream_emits_tool_and_reply_events() -> None:
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
    install(
        AgentService(
            LLMConfig(api_key="k", model="fake"),
            client=ScriptedChatClient(
                [
                    AssistantTurn(None, (call,)),
                    AssistantTurn("按假设约 27 万元。", ()),
                ]
            ),
        )
    )
    response = client.post(
        "/api/agent/chat/stream",
        json={"message": "每月存 1000，10 年后多少？"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    text = response.text
    for event in ("session", "tool_call", "tool_result", "reply", "done"):
        assert f"event: {event}" in text
    assert "savings.project" in text
    assert "future_balance_real" in text


def test_stream_requires_token() -> None:
    install(auth_service([AssistantTurn("你好。", ())]))
    response = client.post("/api/agent/chat/stream", json={"message": "hi"})
    assert response.status_code == 401
    assert response.json()["code"] == "AGENT_UNAUTHORIZED"


def test_stream_reports_cross_user_session_as_error_event() -> None:
    install(
        auth_service(
            [
                AssistantTurn("alice 的会话", ()),
            ]
        )
    )
    first = client.post(
        "/api/agent/chat",
        json={"message": "alice"},
        headers=bearer("tok-alice"),
    )
    session_id = first.json()["session_id"]

    response = client.post(
        "/api/agent/chat/stream",
        json={"session_id": session_id, "message": "bob"},
        headers=bearer("tok-bob"),
    )
    assert response.status_code == 200
    assert "event: error" in response.text
    assert "AGENT_SESSION_NOT_FOUND" in response.text


def test_sqlite_session_survives_new_service(tmp_path) -> None:
    path = str(tmp_path / "agent.sqlite3")
    first_store = SqliteSessionStore(path)
    first_service = AgentService(
        LLMConfig(api_key="k", model="fake"),
        client=ScriptedChatClient([AssistantTurn("第一轮回答。", ())]),
        sessions=first_store,
    )
    first = first_service.chat(None, "第一轮问题")
    first_store.close()

    second_store = SqliteSessionStore(path)
    second_fake = ScriptedChatClient([AssistantTurn("第二轮回答。", ())])
    second_service = AgentService(
        LLMConfig(api_key="k", model="fake"),
        client=second_fake,
        sessions=second_store,
    )
    second = second_service.chat(first.session_id, "第二轮问题")
    assert second.reply == "第二轮回答。"
    assert second_fake.requests[0]["messages"][1]["content"] == "第一轮问题"
    assert second_fake.requests[0]["messages"][2]["content"] == "第一轮回答。"
    second_store.close()


def test_demo_fake_service_runs_without_key() -> None:
    service = AgentService.from_env({"RETIRENEST_AGENT_FAKE": "1"})
    assert service.enabled is True
    assert service.model_name == "fake-demo"

    reply = service.chat(None, "演示一下")
    assert "开发假模型" in reply.reply
    assert len(reply.tool_calls) == 1
    assert reply.tool_calls[0]["command_id"] == "savings.project"
    assert reply.tool_calls[0]["ok"] is True
    assert reply.warnings == ()
