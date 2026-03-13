from dataclasses import dataclass
from typing import Any

from src.domain.entities.chat import ChatCompletionRequest, ChatMessage


@dataclass
class ChatCompletionInputDto:
    model: str
    messages: list[dict[str, Any]]
    stream: bool
    temperature: float | None
    max_tokens: int | None
    user: str | None
    stop: object | None

    def to_domain(self) -> ChatCompletionRequest:
        return ChatCompletionRequest(
            model=self.model,
            messages=[
                ChatMessage(
                    role=m.get("role", ""),
                    content=m.get("content", ""),
                    images=m.get("images"),
                )
                for m in self.messages
            ],
            stream=self.stream,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            user=self.user,
            stop=self.stop,
        )
