from src.infrastructure.gateways.responses_helpers import (
    responses_input_for_log,
    sanitize_responses_request,
)


def test_sanitize_removes_reasoning_for_non_thinking_model():
    body = {
        "model": "llama3.2:3b",
        "input": "hello",
        "reasoning": {"effort": "high"},
    }
    out = sanitize_responses_request(body, supports_thinking=False)
    assert "reasoning" not in out
    assert out["model"] == "llama3.2:3b"


def test_sanitize_keeps_reasoning_for_thinking_model():
    body = {
        "model": "gemma4:26b",
        "input": "hello",
        "reasoning": {"effort": "low"},
    }
    out = sanitize_responses_request(body, supports_thinking=True)
    assert out["reasoning"] == {"effort": "low"}


def test_sanitize_drops_invalid_reasoning_effort():
    body = {
        "model": "gemma4:26b",
        "input": "hello",
        "reasoning": {"effort": "turbo"},
    }
    out = sanitize_responses_request(body, supports_thinking=True)
    assert "reasoning" not in out


def test_responses_input_for_log_string_input():
    messages = responses_input_for_log({"input": "hello"})
    assert messages == [{"role": "user", "content": "hello"}]


def test_responses_input_for_log_message_items():
    body = {
        "input": [
            {"role": "user", "content": "hi"},
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "there"}],
            },
        ]
    }
    messages = responses_input_for_log(body)
    assert messages[0]["role"] == "user"
    assert messages[1]["content"] == "there"
