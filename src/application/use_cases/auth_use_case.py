from src.domain.ports.api_key_repository import ApiKeyRepositoryPort


class AuthUseCase:
    def __init__(self, api_key_repo: ApiKeyRepositoryPort):
        self.api_key_repo = api_key_repo

    def verify(self, api_key: str) -> tuple[bool, str | None]:
        if not self.api_key_repo.is_enabled():
            return True, None
        return self.api_key_repo.verify_api_key(api_key)
