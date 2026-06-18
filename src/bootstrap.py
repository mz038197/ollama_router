from src.application.use_cases.admin_use_case import AdminUseCase
from src.application.use_cases.api_use_case import ApiUseCase
from src.application.use_cases.auth_use_case import AuthUseCase
from src.application.use_cases.portal_use_case import PortalUseCase
from src.infrastructure.config import load_router_settings
from src.infrastructure.gateways.ollama_gateway import OllamaGateway
from src.infrastructure.logging.file_request_logger import FileRequestLogger
from src.infrastructure.repositories.json_api_key_repository import JsonApiKeyRepository
from src.infrastructure.repositories.sqlite_router_repository import SqliteRouterRepository
from src.presentation.fastapi.dependencies import AppContainer


def build_container(
    backends: list[str],
    request_timeout: float,
    max_concurrent_per_backend: int,
    default_temperature: float,
    default_num_predict: int,
    config_path: str | None = None,
    use_sqlite: bool = True,
) -> AppContainer:
    settings = load_router_settings(config_path)
    api_key_repo = (
        SqliteRouterRepository(settings.database.path, settings)
        if use_sqlite
        else JsonApiKeyRepository()
    )
    request_logger = FileRequestLogger()
    ollama_gateway = OllamaGateway(
        backend_urls=backends,
        timeout=request_timeout,
        max_concurrent_per_backend=max_concurrent_per_backend,
        default_temperature=default_temperature,
        default_num_predict=default_num_predict,
    )

    legacy_admin_repo = JsonApiKeyRepository()
    auth_use_case = AuthUseCase(api_key_repo=api_key_repo)
    api_use_case = ApiUseCase(
        gateway=ollama_gateway,
        api_key_repo=api_key_repo,
        logger=request_logger,
    )
    admin_use_case = AdminUseCase(api_key_repo=legacy_admin_repo, request_logger=request_logger)
    portal_use_case = PortalUseCase(api_key_repo, settings) if isinstance(api_key_repo, SqliteRouterRepository) else None

    return AppContainer(
        api_key_repo=api_key_repo,
        request_logger=request_logger,
        ollama_gateway=ollama_gateway,
        auth_use_case=auth_use_case,
        api_use_case=api_use_case,
        admin_use_case=admin_use_case,
        portal_use_case=portal_use_case,
        archive_repo=api_key_repo if isinstance(api_key_repo, SqliteRouterRepository) else None,
        prompt_log_retention_days=settings.prompt_logs.retention_days,
    )
