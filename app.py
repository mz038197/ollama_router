from contextlib import asynccontextmanager
import asyncio
import os

from fastapi import FastAPI

from src.bootstrap import build_container
from src.presentation.fastapi.error_handlers import register_error_handlers
from src.presentation.fastapi.middleware.api_key_middleware import ApiKeyMiddleware
from src.presentation.fastapi.routers.admin_router import create_admin_router
from src.presentation.fastapi.routers.api_router import create_api_router
from src.presentation.fastapi.routers.portal_router import create_portal_router
from src.infrastructure.jobs.log_archive_job import run_daily_archive_job

# =========================
# 可調整設定
# =========================
BACKENDS = [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11435",
    "http://127.0.0.1:11436",
    "http://127.0.0.1:11437",
]
REQUEST_TIMEOUT = 900.0
MAX_CONCURRENT_PER_BACKEND = 1
DEFAULT_NUM_PREDICT = 200000
DEFAULT_TEMPERATURE = 0.7

container = build_container(
    backends=BACKENDS,
    request_timeout=REQUEST_TIMEOUT,
    max_concurrent_per_backend=MAX_CONCURRENT_PER_BACKEND,
    default_temperature=DEFAULT_TEMPERATURE,
    default_num_predict=DEFAULT_NUM_PREDICT,
    config_path=os.getenv("OLLAMA_ROUTER_CONFIG"),
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    archive_stop_event = asyncio.Event()
    archive_task = None
    if container.archive_repo is not None:
        archive_task = asyncio.create_task(
            run_daily_archive_job(
                container.archive_repo,
                container.prompt_log_retention_days,
                archive_stop_event,
            )
        )
    await container.ollama_gateway.startup()
    try:
        yield
    finally:
        archive_stop_event.set()
        if archive_task is not None:
            archive_task.cancel()
        await container.ollama_gateway.shutdown()


app = FastAPI(title="Vans OpenAI-Compatible Ollama Router", lifespan=lifespan)

# Error handlers
register_error_handlers(app)

# Middleware
app.add_middleware(ApiKeyMiddleware, auth_use_case=container.auth_use_case)

# Routers
app.include_router(create_api_router(container.api_use_case))
app.include_router(create_admin_router(container.admin_use_case))
if container.portal_use_case is not None and container.router_settings is not None:
    app.include_router(create_portal_router(container.portal_use_case, container.router_settings))
