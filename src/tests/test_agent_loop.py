"""工具循环：成功、缺参、未知工具、坏 JSON、多调用与轮数上限。"""

from __future__ import annotations

import json

import pytest

from agent import (
    AssistantTurn,
    ScriptedChatClient,
    ToolCall,
    build_catalog,
    run_agent,
)
from agent.loop import MAX_TOOL_CONTENT_CHARS, TRUNCATED_SUFFIX, _truncate

SAVINGS_ARGS = {
    "current_savings": 100_000,
    "monthly_contribution": 1_000,
    "annual_return_pct": 5,
    "inflation_pct": 2,
    "years": 10,
}


@pytest.fixture(scope="module")
def catalog():
    return build_catalog()


def tool_call(name: str, arguments: object, call_id: str = "call_1") -> ToolCall:
    if isinstance(arguments, str):
        raw = arguments
    else:
        raw = json.dumps(arguments, ensure_ascii=False)
    return ToolCall(id=call_id, name=name, arguments=raw)


def conversation() -> list[dict]:
    return [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "每月存 1000 元，10 年后有多少？"},
    ]


def test_single_tool_call_then_final_answer(catalog) -> None:
    client = ScriptedChatClient(
        [
            AssistantTurn(None, (tool_call("savings_project", SAVINGS_ARGS),)),
            AssistantTurn("按这组假设，10 年后约 27 万元。", ()),
        ]
    )
    messages = conversation()
    run = run_agent(messages, client, catalog)

    assert run.reply == "按这组假设，10 年后约 27 万元。"
    assert len(run.tool_calls) == 1
    record = run.tool_calls[0]
    assert record["ok"] is True
    assert record["command_id"] == "savings.project"
    assert record["version"] == "1.0.0"
    assert record["inputs"] == SAVINGS_ARGS
    assert record["outputs"]["future_balance_real"] > 0

    assert [message["role"] for message in messages] == [
        "system",
        "user",
        "assistant",
        "tool",
        "assistant",
    ]
    assert messages[-1]["content"] == run.reply
    assert len(client.requests) == 2
    tool_result = json.loads(client.requests[1]["messages"][3]["content"])
    assert tool_result["ok"] is True
    assert tool_result["command_id"] == "savings.project"


def test_missing_parameters_are_fed_back_to_model(catalog) -> None:
    incomplete = {"current_savings": 100_000}
    client = ScriptedChatClient(
        [
            AssistantTurn(None, (tool_call("savings_project", incomplete),)),
            AssistantTurn("还需要每月投入、年限、回报率和通胀率。", ()),
        ]
    )
    messages = conversation()
    run = run_agent(messages, client, catalog)

    record = run.tool_calls[0]
    assert record["ok"] is False
    assert record["error"]["code"] == "INVALID_INPUT"
    fields = {error["field"] for error in record["error"]["field_errors"]}
    assert {"monthly_contribution", "years"} <= fields

    tool_message = client.requests[1]["messages"][3]["content"]
    assert "monthly_contribution" in tool_message
    assert "field_errors" in tool_message


def test_unknown_tool_is_reported_to_model(catalog) -> None:
    client = ScriptedChatClient(
        [
            AssistantTurn(None, (tool_call("not_a_tool", {}),)),
            AssistantTurn("我换一个工具。", ()),
        ]
    )
    run = run_agent(conversation(), client, catalog)

    record = run.tool_calls[0]
    assert record["ok"] is False
    assert record["command_id"] is None
    assert record["error"]["code"] == "UNKNOWN_TOOL"


def test_invalid_json_arguments_are_reported(catalog) -> None:
    client = ScriptedChatClient(
        [
            AssistantTurn(None, (ToolCall("c1", "savings_project", "{bad"),)),
            AssistantTurn("参数格式有问题。", ()),
        ]
    )
    run = run_agent(conversation(), client, catalog)

    record = run.tool_calls[0]
    assert record["ok"] is False
    assert record["error"]["code"] == "INVALID_ARGUMENTS"


def test_non_object_arguments_are_reported(catalog) -> None:
    client = ScriptedChatClient(
        [
            AssistantTurn(None, (tool_call("savings_project", "[1, 2]"),)),
            AssistantTurn("参数必须是对象。", ()),
        ]
    )
    run = run_agent(conversation(), client, catalog)

    assert run.tool_calls[0]["error"]["code"] == "INVALID_ARGUMENTS"


def test_multiple_calls_in_one_turn(catalog) -> None:
    first = dict(SAVINGS_ARGS, years=10)
    second = dict(SAVINGS_ARGS, years=20)
    client = ScriptedChatClient(
        [
            AssistantTurn(
                None,
                (
                    tool_call("savings_project", first, "call_1"),
                    tool_call("savings_project", second, "call_2"),
                ),
            ),
            AssistantTurn("两个年限的结果分别是……", ()),
        ]
    )
    messages = conversation()
    run = run_agent(messages, client, catalog)

    assert len(run.tool_calls) == 2
    assert all(record["ok"] for record in run.tool_calls)
    tool_messages = [message for message in messages if message["role"] == "tool"]
    assert len(tool_messages) == 2
    assert [message["tool_call_id"] for message in tool_messages] == ["call_1", "call_2"]


def test_max_rounds_forces_a_final_answer(catalog) -> None:
    class LoopingClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages, tools):
            self.calls += 1
            if not tools:
                return AssistantTurn("工具调用太多，先给你已有结果。", ())
            return AssistantTurn(
                None,
                (tool_call("savings_project", SAVINGS_ARGS, f"call_{self.calls}"),),
            )

    client = LoopingClient()
    run = run_agent(conversation(), client, catalog, max_rounds=2)

    assert len(run.tool_calls) == 2
    assert run.warnings
    assert "2" in run.warnings[0]
    assert run.reply == "工具调用太多，先给你已有结果。"
    assert client.calls == 3


def test_no_tool_call_is_returned_and_stored(catalog) -> None:
    client = ScriptedChatClient([AssistantTurn("你好，先告诉我你的年龄。", ())])
    messages = conversation()
    run = run_agent(messages, client, catalog)

    assert run.tool_calls == ()
    assert run.reply == "你好，先告诉我你的年龄。"
    assert messages[-1] == {"role": "assistant", "content": run.reply}


def test_truncate_marks_suffix() -> None:
    text = "x" * (MAX_TOOL_CONTENT_CHARS + 10)
    truncated = _truncate(text)
    assert len(truncated) == MAX_TOOL_CONTENT_CHARS + len(TRUNCATED_SUFFIX)
    assert truncated.endswith(TRUNCATED_SUFFIX)
    assert _truncate("short") == "short"
