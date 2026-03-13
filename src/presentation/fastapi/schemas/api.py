from typing import Any

from pydantic import BaseModel, Field, field_validator


class ContentPart(BaseModel):
    """表示 content 陣列中的單個部分"""
    type: str
    text: str | None = None
    image_url: dict[str, str] | None = None


class ChatMessageSchema(BaseModel):
    """支援 OpenAI 相容格式的聊天訊息"""
    role: str
    content: str | list[ContentPart | dict[str, Any]] = Field(description="訊息內容，可以是文字或包含文字/影像的陣列")
    images: list[str] | None = Field(default=None, description="影像資料陣列（base64 編碼或 URL）")

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: Any) -> Any:
        if isinstance(v, str):
            if not v or not v.strip():
                raise ValueError("訊息內容不能為空")
            return v
        if isinstance(v, list):
            if not v:
                raise ValueError("訊息內容不能為空陣列")
            return v
        raise ValueError("訊息內容必須是字符串或陣列")


class ChatCompletionsRequestSchema(BaseModel):
    model: str
    messages: list[ChatMessageSchema]
    stream: bool = False
    temperature: float | None = 0.7
    max_tokens: int | None = 256
    user: str | None = None
    stop: Any | None = None
