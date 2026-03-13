from dataclasses import dataclass

from src.application.use_cases.admin_use_case import AdminUseCase
from src.application.use_cases.api_use_case import ApiUseCase
from src.application.use_cases.auth_use_case import AuthUseCase
from src.infrastructure.gateways.ollama_gateway import OllamaGateway
from src.infrastructure.logging.file_request_logger import FileRequestLogger
from src.infrastructure.repositories.json_api_key_repository import JsonApiKeyRepository


@dataclass
class AppContainer:
    api_key_repo: JsonApiKeyRepository
    request_logger: FileRequestLogger
    ollama_gateway: OllamaGateway
    auth_use_case: AuthUseCase
    api_use_case: ApiUseCase
    admin_use_case: AdminUseCase
