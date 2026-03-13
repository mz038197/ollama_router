from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.bootstrap import build_container
from src.presentation.fastapi.error_handlers import register_error_handlers
from src.presentation.fastapi.middleware.api_key_middleware import ApiKeyMiddleware
from src.presentation.fastapi.routers.admin_router import create_admin_router
from src.presentation.fastapi.routers.api_router import create_api_router

# =========================
# 可調整設定
# =========================
BACKENDS = [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11435",
    "http://127.0.0.1:11436",
    "http://127.0.0.1:11437",
]
REQUEST_TIMEOUT = 300.0
MAX_CONCURRENT_PER_BACKEND = 1
DEFAULT_NUM_PREDICT = 256
DEFAULT_TEMPERATURE = 0.7

container = build_container(
    backends=BACKENDS,
    request_timeout=REQUEST_TIMEOUT,
    max_concurrent_per_backend=MAX_CONCURRENT_PER_BACKEND,
    default_temperature=DEFAULT_TEMPERATURE,
    default_num_predict=DEFAULT_NUM_PREDICT,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await container.ollama_gateway.startup()
    yield
    await container.ollama_gateway.shutdown()


app = FastAPI(title="Vans OpenAI-Compatible Ollama Router", lifespan=lifespan)

# Error handlers
register_error_handlers(app)

# Middleware
app.add_middleware(ApiKeyMiddleware, auth_use_case=container.auth_use_case)

# Routers
app.include_router(create_api_router(container.api_use_case))
app.include_router(create_admin_router(container.admin_use_case))
