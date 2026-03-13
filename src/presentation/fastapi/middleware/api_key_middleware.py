from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.application.use_cases.auth_use_case import AuthUseCase
from src.domain.errors import AuthenticationError


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_use_case: AuthUseCase):
        super().__init__(app)
        self.auth_use_case = auth_use_case

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/v1/chat/completions":
            api_key = None
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            else:
                api_key = request.headers.get("X-API-Key")

            is_valid, _ = self.auth_use_case.verify(api_key or "")
            if not is_valid:
                err = AuthenticationError()
                return JSONResponse(status_code=err.status_code, content={"detail": err.message})

        response = await call_next(request)
        return response
