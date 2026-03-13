from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.application.dto.chat_dto import ChatCompletionInputDto
from src.application.use_cases.api_use_case import ApiUseCase
from src.presentation.fastapi.schemas.api import ChatCompletionsRequestSchema


def create_api_router(api_use_case: ApiUseCase) -> APIRouter:
    router = APIRouter(tags=["API"])

    @router.get("/health")
    async def health():
        return await api_use_case.health()

    @router.get("/v1/models")
    async def list_models():
        return await api_use_case.models()

    @router.post("/v1/chat/completions")
    async def chat_completions(req: ChatCompletionsRequestSchema, request: Request):
        auth_header = request.headers.get("Authorization", "")
        api_key = auth_header[7:] if auth_header.startswith("Bearer ") else request.headers.get("X-API-Key")

        input_dto = ChatCompletionInputDto(
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            stream=req.stream,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            user=req.user,
            stop=req.stop,
        )
        domain_req = input_dto.to_domain()

        if domain_req.stream:
            generator = api_use_case.chat_stream(domain_req, api_key)
            return StreamingResponse(generator, media_type="text/event-stream")

        data = await api_use_case.chat_nonstream(domain_req, api_key)
        return JSONResponse(content=data)

    return router
