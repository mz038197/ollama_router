from typing import Any

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: str
    content: str = Field(min_length=1, description="訊息內容，不能為空")


class ChatCompletionsRequestSchema(BaseModel):
    model: str
    messages: list[ChatMessageSchema]
    stream: bool = False
    temperature: float | None = 0.7
    max_tokens: int | None = 256
    user: str | None = None
    stop: Any | None = None
