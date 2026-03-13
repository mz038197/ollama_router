from typing import Protocol


class RequestLogPort(Protocol):
    def log_validation_result(
        self,
        teacher_name: str | None,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
        is_valid: bool,
    ) -> None:
        ...
