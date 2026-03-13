from typing import Any, AsyncGenerator, Protocol

from src.domain.entities.chat import ChatCompletionRequest


class OllamaGatewayPort(Protocol):
    async def startup(self) -> None:
        ...

    async def shutdown(self) -> None:
        ...

    async def health(self) -> dict[str, Any]:
        ...

    async def models(self) -> dict[str, Any]:
        ...

    async def chat_completions_nonstream(self, req: ChatCompletionRequest) -> dict[str, Any]:
        ...

    async def chat_completions_stream(self, req: ChatCompletionRequest) -> AsyncGenerator[bytes, None]:
        ...
