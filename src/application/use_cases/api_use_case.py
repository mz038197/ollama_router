from typing import Any, AsyncGenerator

from src.domain.errors import StatefulResponsesNotSupportedError
from src.domain.entities.auth import AuthContext
from src.domain.entities.chat import ChatCompletionRequest, ChatMessage
from src.domain.ports.api_key_repository import ApiKeyRepositoryPort
from src.domain.ports.ollama_gateway import OllamaGatewayPort
from src.domain.ports.request_log import RequestLogPort
from src.infrastructure.gateways.responses_helpers import responses_input_for_log


class ApiUseCase:
    def __init__(
        self,
        gateway: OllamaGatewayPort,
        api_key_repo: ApiKeyRepositoryPort,
        logger: RequestLogPort,
    ):
        self.gateway = gateway
        self.api_key_repo = api_key_repo
        self.logger = logger

    async def health(self) -> dict[str, Any]:
        return await self.gateway.health()

    async def models(self) -> dict[str, Any]:
        return await self.gateway.models()

    async def chat_nonstream(
        self,
        req: ChatCompletionRequest,
        api_key: str | None,
        client_ip: str | None = None,
        auth_context: AuthContext | None = None,
    ) -> dict[str, Any]:
        self._log_request(req, api_key, client_ip, auth_context)
        return await self.gateway.chat_completions_nonstream(req)

    async def chat_stream(
        self,
        req: ChatCompletionRequest,
        api_key: str | None,
        client_ip: str | None = None,
        auth_context: AuthContext | None = None,
    ) -> AsyncGenerator[bytes, None]:
        self._log_request(req, api_key, client_ip, auth_context)
        async for chunk in self.gateway.chat_completions_stream(req):
            yield chunk

    def validate_responses_request(self, body: dict[str, Any]) -> None:
        self._validate_responses_body(body)

    async def responses_create(
        self, body: dict[str, Any], api_key: str | None, client_ip: str | None = None
    ) -> dict[str, Any]:
        self._validate_responses_body(body)
        self._log_responses_request(body, api_key, client_ip)
        return await self.gateway.responses_create(body)

    async def responses_create_stream(
        self, body: dict[str, Any], api_key: str | None, client_ip: str | None = None
    ) -> AsyncGenerator[bytes, None]:
        self._validate_responses_body(body)
        self._log_responses_request(body, api_key, client_ip)
        async for chunk in self.gateway.responses_create_stream(body):
            yield chunk

    def _validate_responses_body(self, body: dict[str, Any]) -> None:
        previous_response_id = body.get("previous_response_id")
        if previous_response_id not in (None, ""):
            raise StatefulResponsesNotSupportedError()

    def _log_responses_request(
        self, body: dict[str, Any], api_key: str | None, client_ip: str | None = None
    ) -> None:
        model = body.get("model")
        model_name = model if isinstance(model, str) else "N/A"
        messages = responses_input_for_log(body)
        api_key_value = api_key or ""
        teacher_name: str | None = None
        is_valid = True

        if self.api_key_repo.is_enabled():
            is_valid, teacher_name = self.api_key_repo.verify_api_key(api_key_value)

        self.logger.log_validation_result(
            teacher_name=teacher_name,
            api_key=api_key or "未提供",
            model=model_name,
            messages=messages,
            is_valid=is_valid,
            client_ip=client_ip,
        )

    def _log_request(
        self,
        req: ChatCompletionRequest,
        api_key: str | None,
        client_ip: str | None = None,
        auth_context: AuthContext | None = None,
    ) -> None:
        api_key_value = api_key or ""
        teacher_name: str | None = None
        is_valid = True

        if self.api_key_repo.is_enabled():
            if auth_context is None and hasattr(self.api_key_repo, "verify_api_key_context"):
                auth_context = self.api_key_repo.verify_api_key_context(api_key_value)
                is_valid = auth_context is not None
            else:
                is_valid, teacher_name = self.api_key_repo.verify_api_key(api_key_value)
        if auth_context is not None:
            teacher_name = auth_context.teacher_name

        messages = [_message_to_log_dict(m) for m in req.messages]

        self.logger.log_validation_result(
            teacher_name=teacher_name,
            api_key=api_key or "未提供",
            model=req.model,
            messages=messages,
            is_valid=is_valid,
            client_ip=client_ip,
        )
        if hasattr(self.api_key_repo, "log_prompt"):
            raw_prompt = _messages_to_text(messages)
            self.api_key_repo.log_prompt(
                auth=auth_context,
                raw_prompt=raw_prompt,
                final_prompt=raw_prompt,
                model=req.model,
                status="ok" if is_valid else "rejected",
                client_ip=client_ip,
            )

    def log_invalid_auth(self, api_key: str, client_ip: str | None = None) -> None:
        """記錄無效的認證嘗試，供安全審計追蹤。"""
        teacher_name: str | None = None
        is_valid = False

        if self.api_key_repo.is_enabled():
            is_valid, teacher_name = self.api_key_repo.verify_api_key(api_key)

        self.logger.log_validation_result(
            teacher_name=teacher_name,
            api_key=api_key or "未提供",
            model="N/A",
            messages=[],
            is_valid=is_valid,
            client_ip=client_ip,
        )


def _message_to_log_dict(m: ChatMessage) -> dict[str, Any]:
    d: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        d["tool_calls"] = m.tool_calls
    if m.tool_call_id:
        d["tool_call_id"] = m.tool_call_id
    if m.tool_name:
        d["tool_name"] = m.tool_name
    return d


def _messages_to_text(messages: list[dict[str, Any]]) -> str:
    parts = []
    for message in messages:
        parts.append(f"{message.get('role', '')}: {message.get('content', '')}")
    return "\n".join(parts)
