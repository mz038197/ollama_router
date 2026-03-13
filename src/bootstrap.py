from src.application.use_cases.admin_use_case import AdminUseCase
from src.application.use_cases.api_use_case import ApiUseCase
from src.application.use_cases.auth_use_case import AuthUseCase
from src.infrastructure.gateways.ollama_gateway import OllamaGateway
from src.infrastructure.logging.file_request_logger import FileRequestLogger
from src.infrastructure.repositories.json_api_key_repository import JsonApiKeyRepository
from src.presentation.fastapi.dependencies import AppContainer


def build_container(
    backends: list[str],
    request_timeout: float,
    max_concurrent_per_backend: int,
    default_temperature: float,
    default_num_predict: int,
) -> AppContainer:
    api_key_repo = JsonApiKeyRepository()
    request_logger = FileRequestLogger()
    ollama_gateway = OllamaGateway(
        backend_urls=backends,
        timeout=request_timeout,
        max_concurrent_per_backend=max_concurrent_per_backend,
        default_temperature=default_temperature,
        default_num_predict=default_num_predict,
    )

    auth_use_case = AuthUseCase(api_key_repo=api_key_repo)
    api_use_case = ApiUseCase(
        gateway=ollama_gateway,
        api_key_repo=api_key_repo,
        logger=request_logger,
    )
    admin_use_case = AdminUseCase(api_key_repo=api_key_repo)

    return AppContainer(
        api_key_repo=api_key_repo,
        request_logger=request_logger,
        ollama_gateway=ollama_gateway,
        auth_use_case=auth_use_case,
        api_use_case=api_use_case,
        admin_use_case=admin_use_case,
    )
