from dataclasses import dataclass
from typing import Any

from src.application.use_cases.admin_use_case import AdminUseCase
from src.application.use_cases.api_use_case import ApiUseCase
from src.application.use_cases.auth_use_case import AuthUseCase
from src.application.use_cases.portal_use_case import PortalUseCase
from src.infrastructure.gateways.ollama_gateway import OllamaGateway
from src.infrastructure.logging.file_request_logger import FileRequestLogger
from src.domain.ports.api_key_repository import ApiKeyRepositoryPort


@dataclass
class AppContainer:
    api_key_repo: ApiKeyRepositoryPort
    request_logger: FileRequestLogger
    ollama_gateway: OllamaGateway
    auth_use_case: AuthUseCase
    api_use_case: ApiUseCase
    admin_use_case: AdminUseCase
    portal_use_case: PortalUseCase | None = None
    archive_repo: Any | None = None
    prompt_log_retention_days: int = 30
    router_settings: Any | None = None
