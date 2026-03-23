"""Ollama gateway 與 tool 相關的純函式單元測試。"""
import json

from src.domain.entities.chat import ChatCompletionRequest, ChatMessage
from src.infrastructure.gateways.ollama_gateway import (
    build_ollama_messages,
    merge_tool_calls_stream,
    normalize_tool_call_for_ollama,
    resolve_tool_name_from_tool_call_id,
    tool_calls_ollama_to_openai,
)


def test_normalize_tool_call_parses_arguments_json_string():
    tc = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "f", "arguments": '{"a": 1}'},
    }
    out = normalize_tool_call_for_ollama(tc)
    assert out["function"]["arguments"] == {"a": 1}


def test_tool_calls_ollama_to_openai_converts_arguments_to_string():
    ollama = [
        {
            "type": "function",
            "function": {"name": "get_x", "index": 0, "arguments": {"city": "NYC"}},
        }
    ]
    openai = tool_calls_ollama_to_openai(ollama)
    assert openai is not None
    assert openai[0]["function"]["name"] == "get_x"
    assert json.loads(openai[0]["function"]["arguments"]) == {"city": "NYC"}


def test_merge_tool_calls_stream_merges_by_index():
    a = [{"type": "function", "function": {"index": 0, "name": "a", "arguments": {}}}]
    b = [{"type": "function", "function": {"index": 1, "name": "b", "arguments": {}}}]
    m = merge_tool_calls_stream(a, b)
    assert len(m) == 2
    assert m[0]["function"]["name"] == "a"
    assert m[1]["function"]["name"] == "b"


def test_resolve_tool_name_from_assistant_tool_calls():
    msgs = [
        ChatMessage(role="user", content="hi"),
        ChatMessage(
            role="assistant",
            content="",
            tool_calls=[
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {"name": "foo", "arguments": "{}"},
                }
            ],
        ),
        ChatMessage(role="tool", content="result", tool_call_id="call_abc"),
    ]
    req = ChatCompletionRequest(model="m", messages=msgs, stream=False)
    name = resolve_tool_name_from_tool_call_id("call_abc", req.messages, 2)
    assert name == "foo"


def test_build_ollama_messages_includes_tools_and_tool_role():
    req = ChatCompletionRequest(
        model="m",
        messages=[
            ChatMessage(role="user", content="q"),
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "t", "arguments": "{}"},
                    }
                ],
            ),
            ChatMessage(role="tool", content="ok", tool_call_id="c1"),
        ],
        stream=False,
        tools=[{"type": "function", "function": {"name": "t", "parameters": {"type": "object"}}}],
    )
    msgs = build_ollama_messages(req)
    assert msgs[2]["role"] == "tool"
    assert msgs[2]["tool_name"] == "t"
    assert "tool_calls" in msgs[1]
