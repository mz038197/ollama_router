from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    role: str
    content: str = ""


@dataclass
class ChatCompletionRequest:
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = 0.7
    max_tokens: int | None = 256
    user: str | None = None
    stop: object | None = None


@dataclass
class AddTeacherInput:
    name: str


@dataclass
class DeleteTeacherInput:
    teacher: str


@dataclass
class AddKeyInput:
    teacher: str
    name: str
    key: str
    enabled: bool = True


@dataclass
class UpdateKeyStatusInput:
    teacher: str
    key: str
    enabled: bool = True


@dataclass
class DeleteKeyInput:
    teacher: str
    key: str
