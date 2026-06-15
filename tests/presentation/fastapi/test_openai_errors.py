import json

from src.presentation.fastapi.openai_errors import (
    make_openai_error_body,
    openai_stream_error_bytes,
)


def test_make_openai_error_body_shape():
    body = make_openai_error_body("failed", error_type="server_error", code="x")
    assert body == {
        "error": {
            "message": "failed",
            "type": "server_error",
            "param": None,
            "code": "x",
        }
    }


def test_openai_stream_error_bytes_is_valid_json():
    raw = openai_stream_error_bytes("upstream down", error_type="server_error")
    line = raw.decode("utf-8").strip()
    assert line.startswith("data: ")
    payload = json.loads(line[6:])
    assert payload["error"]["message"] == "upstream down"
