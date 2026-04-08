"""Ollama gateway 與 tool 相關的純函式單元測試。"""
import json

from src.domain.entities.chat import ChatCompletionRequest, ChatMessage
from src.infrastructure.gateways.ollama_gateway import (
    build_ollama_messages,
    extract_ollama_message_fields,
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
    assert isinstance(openai[0]["function"]["arguments"], str)
    assert json.loads(openai[0]["function"]["arguments"]) == {"city": "NYC"}


def test_tool_calls_ollama_to_openai_stringifies_without_type_field():
    """Ollama 有時不帶 type=function；仍須輸出 OpenAI 規範的 arguments 字串。"""
    ollama = [{"function": {"name": "f", "arguments": {"x": 1}}}]
    openai = tool_calls_ollama_to_openai(ollama)
    assert openai is not None
    assert openai[0]["type"] == "function"
    assert isinstance(openai[0]["function"]["arguments"], str)
    assert json.loads(openai[0]["function"]["arguments"]) == {"x": 1}


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


def test_extract_ollama_message_fields_falls_back_to_thinking_when_content_empty():
    data = {
        "message": {
            "role": "assistant",
            "content": "",
            "thinking": "internal reasoning…\nfinal answer line",
        }
    }
    content, tcs = extract_ollama_message_fields(data)
    assert "final answer line" in content
    assert tcs is None


def test_extract_ollama_message_fields_falls_back_to_reasoning():
    data = {"message": {"role": "assistant", "content": "", "reasoning": "Canberra"}}
    content, tcs = extract_ollama_message_fields(data)
    assert content == "Canberra"
    assert tcs is None


def test_extract_ollama_message_fields_prefers_content_when_both_present():
    data = {
        "message": {
            "role": "assistant",
            "content": "visible",
            "thinking": "hidden",
        }
    }
    content, _ = extract_ollama_message_fields(data)
    assert content == "visible"


def test_extract_ollama_message_fields_does_not_replace_with_thinking_when_tool_calls():
    data = {
        "message": {
            "role": "assistant",
            "content": "",
            "thinking": "only thinking",
            "tool_calls": [{"type": "function", "function": {"name": "f"}}],
        }
    }
    content, tcs = extract_ollama_message_fields(data)
    assert content == ""
    assert tcs is not None


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
