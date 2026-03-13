from typing import Any, AsyncGenerator

from src.domain.entities.chat import ChatCompletionRequest
from src.domain.ports.api_key_repository import ApiKeyRepositoryPort
from src.domain.ports.ollama_gateway import OllamaGatewayPort
from src.domain.ports.request_log import RequestLogPort


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

    async def chat_nonstream(self, req: ChatCompletionRequest, api_key: str | None) -> dict[str, Any]:
        self._log_request(req, api_key)
        return await self.gateway.chat_completions_nonstream(req)

    async def chat_stream(self, req: ChatCompletionRequest, api_key: str | None) -> AsyncGenerator[bytes, None]:
        self._log_request(req, api_key)
        async for chunk in self.gateway.chat_completions_stream(req):
            yield chunk

    def _log_request(self, req: ChatCompletionRequest, api_key: str | None) -> None:
        api_key_value = api_key or ""
        teacher_name: str | None = None
        is_valid = True

        if self.api_key_repo.is_enabled():
            is_valid, teacher_name = self.api_key_repo.verify_api_key(api_key_value)

        self.logger.log_validation_result(
            teacher_name=teacher_name,
            api_key=api_key or "未提供",
            model=req.model,
            messages=[{"role": m.role, "content": m.content} for m in req.messages],
            is_valid=is_valid,
        )
