from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.domain.errors import (
    AdminBusinessError,
    AppError,
    AuthenticationError,
    ServiceUnavailableError,
    UpstreamServiceError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def handle_authentication_error(_: Request, exc: AuthenticationError):
        # 維持既有對外格式：{"detail": "..."}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(UpstreamServiceError)
    async def handle_upstream_error(_: Request, exc: UpstreamServiceError):
        details = exc.details or {}
        # 維持既有對外格式：detail 為 object
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": {
                    "message": "Ollama backend error",
                    "backend": details.get("backend", ""),
                    "body": details.get("body", ""),
                }
            },
        )

    @app.exception_handler(ServiceUnavailableError)
    async def handle_service_unavailable(_: Request, exc: ServiceUnavailableError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(AdminBusinessError)
    async def handle_admin_business_error(_: Request, exc: AdminBusinessError):
        payload = {
            "detail": {
                "code": exc.code,
                "message": exc.message,
            }
        }
        if exc.details is not None:
            payload["detail"]["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError):
        payload = {"detail": exc.message}
        if exc.details is not None:
            payload["error"] = {"code": exc.code, "details": exc.details}
        return JSONResponse(status_code=exc.status_code, content=payload)
