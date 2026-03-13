from collections.abc import AsyncGenerator
from pathlib import Path
import sys
from typing import Any

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.entities.chat import ChatCompletionRequest, ChatMessage


class FakeApiKeyRepository:
    def __init__(self, config_data: dict[str, Any] | None = None, force_enabled: bool | None = None):
        self.config_data = config_data or {}
        self.force_enabled = force_enabled

    def verify_api_key(self, api_key: str) -> tuple[bool, str | None]:
        if not api_key:
            return False, None
        for teacher_name, teacher_data in self.config_data.items():
            for key_info in teacher_data.get("api_keys", []):
                if key_info["key"] == api_key and key_info.get("enabled", False):
                    return True, teacher_name
        return False, None

    def is_enabled(self) -> bool:
        if self.force_enabled is not None:
            return self.force_enabled
        return bool(self.config_data)

    def get_all_config(self) -> dict[str, Any]:
        return self.config_data

    def add_teacher(self, teacher_name: str) -> None:
        if teacher_name not in self.config_data:
            self.config_data[teacher_name] = {"api_keys": []}

    def delete_teacher(self, teacher_name: str) -> bool:
        if teacher_name not in self.config_data:
            return False
        del self.config_data[teacher_name]
        return True

    def add_api_key(self, teacher_name: str, name: str, key: str, enabled: bool = True) -> None:
        self.add_teacher(teacher_name)
        self.config_data[teacher_name]["api_keys"].append(
            {"name": name, "key": key, "enabled": enabled}
        )

    def update_api_key_status(self, teacher_name: str, key: str, enabled: bool) -> bool:
        if teacher_name not in self.config_data:
            return False
        for key_info in self.config_data[teacher_name].get("api_keys", []):
            if key_info["key"] == key:
                key_info["enabled"] = enabled
                return True
        return False

    def delete_api_key(self, teacher_name: str, key: str) -> bool:
        if teacher_name not in self.config_data:
            return False
        api_keys = self.config_data[teacher_name].get("api_keys", [])
        for idx, key_info in enumerate(api_keys):
            if key_info["key"] == key:
                api_keys.pop(idx)
                return True
        return False


class FakeRequestLogger:
    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def log_validation_result(
        self,
        teacher_name: str | None,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
        is_valid: bool,
    ) -> None:
        self.entries.append(
            {
                "teacher_name": teacher_name,
                "api_key": api_key,
                "model": model,
                "messages": messages,
                "is_valid": is_valid,
            }
        )


class FakeOllamaGateway:
    def __init__(self):
        self.last_nonstream_req: ChatCompletionRequest | None = None
        self.last_stream_req: ChatCompletionRequest | None = None
        self.health_response = {"queue_waiting": 0, "backends": []}
        self.models_response = {"object": "list", "data": [{"id": "fake-model", "object": "model", "owned_by": "ollama"}]}
        self.nonstream_response = {
            "id": "chatcmpl-fake",
            "object": "chat.completion",
            "created": 123,
            "model": "fake-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hello"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }
        self.stream_chunks = [
            b'data: {"id":"chatcmpl-fake","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":""},"finish_reason":null}]}\n\n',
            b"data: [DONE]\n\n",
        ]

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def health(self) -> dict[str, Any]:
        return self.health_response

    async def models(self) -> dict[str, Any]:
        return self.models_response

    async def chat_completions_nonstream(self, req: ChatCompletionRequest) -> dict[str, Any]:
        self.last_nonstream_req = req
        return self.nonstream_response

    async def chat_completions_stream(
        self, req: ChatCompletionRequest
    ) -> AsyncGenerator[bytes, None]:
        self.last_stream_req = req
        for chunk in self.stream_chunks:
            yield chunk


@pytest.fixture
def fake_repo() -> FakeApiKeyRepository:
    return FakeApiKeyRepository(
        config_data={
            "TeacherA": {
                "api_keys": [
                    {"name": "ClassA", "key": "valid-key", "enabled": True},
                    {"name": "ClassB", "key": "disabled-key", "enabled": False},
                ]
            }
        },
        force_enabled=True,
    )


@pytest.fixture
def fake_logger() -> FakeRequestLogger:
    return FakeRequestLogger()


@pytest.fixture
def fake_gateway() -> FakeOllamaGateway:
    return FakeOllamaGateway()


@pytest.fixture
def sample_chat_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="fake-model",
        messages=[ChatMessage(role="user", content="hello")],
        stream=False,
        temperature=0.7,
        max_tokens=16,
    )
