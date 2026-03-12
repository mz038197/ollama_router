import asyncio
import json
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from auth import ApiKeyConfig, RequestLogger


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


# =========================
# 資料模型
# =========================
class ChatMessage(BaseModel):
    role: str
    content: Optional[str] = ""


class ChatCompletionsRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = DEFAULT_TEMPERATURE
    max_tokens: Optional[int] = DEFAULT_NUM_PREDICT

    # 可額外接受其他 OpenAI 風格欄位，避免前端多傳就壞掉
    user: Optional[str] = None
    stop: Optional[Any] = None
    # API 金鑰驗證
    api_key: Optional[str] = None


@dataclass
class BackendState:
    base_url: str
    semaphore: asyncio.Semaphore
    active: int = 0
    completed: int = 0
    failed: int = 0


# =========================
# Router 核心
# =========================
class OllamaRouter:
    def __init__(self, backend_urls: list[str], timeout: float = REQUEST_TIMEOUT):
        self.backends = [
            BackendState(
                base_url=url,
                semaphore=asyncio.Semaphore(MAX_CONCURRENT_PER_BACKEND),
            )
            for url in backend_urls
        ]
        self.timeout = timeout
        self.client: Optional[httpx.AsyncClient] = None
        self.lock = asyncio.Lock()
        self.waiting_count = 0

    async def startup(self):
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def shutdown(self):
        if self.client:
            await self.client.aclose()

    async def health(self) -> dict[str, Any]:
        result = []
        assert self.client is not None

        for b in self.backends:
            ok = False
            detail = ""
            try:
                r = await self.client.get(f"{b.base_url}/api/tags")
                ok = r.status_code == 200
                detail = f"HTTP {r.status_code}"
            except Exception as e:
                detail = str(e)

            result.append(
                {
                    "base_url": b.base_url,
                    "ok": ok,
                    "active": b.active,
                    "completed": b.completed,
                    "failed": b.failed,
                    "detail": detail,
                }
            )

        return {
            "queue_waiting": self.waiting_count,
            "backends": result,
        }

    async def _pick_backend(self) -> BackendState:
        while True:
            async with self.lock:
                available = [b for b in self.backends if b.semaphore._value > 0]
                if available:
                    chosen = min(available, key=lambda x: x.active)
                    await chosen.semaphore.acquire()
                    chosen.active += 1
                    return chosen
            await asyncio.sleep(0.03)

    async def _release_backend(self, backend: BackendState, success: bool):
        async with self.lock:
            backend.active -= 1
            if success:
                backend.completed += 1
            else:
                backend.failed += 1
            backend.semaphore.release()

    def _to_ollama_payload(self, req: ChatCompletionsRequest) -> dict[str, Any]:
        return {
            "model": req.model,
            "messages": [m.model_dump() for m in req.messages],
            "stream": req.stream,
            "options": {
                "temperature": req.temperature if req.temperature is not None else DEFAULT_TEMPERATURE,
                "num_predict": req.max_tokens if req.max_tokens is not None else DEFAULT_NUM_PREDICT,
            },
        }

    async def chat_completions_nonstream(self, req: ChatCompletionsRequest) -> dict[str, Any]:
        enqueue_time = time.perf_counter()

        async with self.lock:
            self.waiting_count += 1
            queue_position_estimate = max(self.waiting_count - len(self.backends), 0)

        backend = await self._pick_backend()

        async with self.lock:
            self.waiting_count -= 1

        success = False
        started = time.perf_counter()
        try:
            assert self.client is not None
            payload = self._to_ollama_payload(req)
            r = await self.client.post(f"{backend.base_url}/api/chat", json=payload)

            if r.status_code != 200:
                raise HTTPException(
                    status_code=r.status_code,
                    detail={
                        "message": "Ollama backend error",
                        "backend": backend.base_url,
                        "body": safe_json_or_text(r),
                    },
                )

            ollama_data = r.json()
            text = extract_ollama_message_content(ollama_data)

            success = True
            return make_openai_nonstream_response(
                model=req.model,
                content=text,
                created=int(time.time()),
                request_id=f"chatcmpl-{uuid.uuid4().hex}",
                meta={
                    "backend": backend.base_url,
                    "waited_seconds": round(started - enqueue_time, 3),
                    "queue_position_estimate": queue_position_estimate,
                },
            )
        finally:
            await self._release_backend(backend, success=success)

    async def chat_completions_stream(
        self, req: ChatCompletionsRequest
    ) -> AsyncGenerator[bytes, None]:
        enqueue_time = time.perf_counter()

        async with self.lock:
            self.waiting_count += 1
            queue_position_estimate = max(self.waiting_count - len(self.backends), 0)

        backend = await self._pick_backend()

        async with self.lock:
            self.waiting_count -= 1

        success = False
        request_id = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        started = time.perf_counter()

        try:
            assert self.client is not None
            payload = self._to_ollama_payload(req)

            async with self.client.stream(
                "POST",
                f"{backend.base_url}/api/chat",
                json=payload,
            ) as r:
                if r.status_code != 200:
                    body = await r.aread()
                    raise HTTPException(
                        status_code=r.status_code,
                        detail={
                            "message": "Ollama backend error",
                            "backend": backend.base_url,
                            "body": body.decode("utf-8", errors="ignore"),
                        },
                    )

                # 先送出 role chunk
                first_chunk = make_openai_stream_chunk(
                    request_id=request_id,
                    created=created,
                    model=req.model,
                    delta={"role": "assistant", "content": ""},
                )
                yield sse(first_chunk)

                async for line in r.aiter_lines():
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    done = bool(obj.get("done", False))
                    piece = ""
                    if "message" in obj and isinstance(obj["message"], dict):
                        piece = obj["message"].get("content", "") or ""

                    if piece:
                        chunk = make_openai_stream_chunk(
                            request_id=request_id,
                            created=created,
                            model=req.model,
                            delta={"content": piece},
                        )
                        yield sse(chunk)

                    if done:
                        final_chunk = make_openai_stream_chunk(
                            request_id=request_id,
                            created=created,
                            model=req.model,
                            delta={},
                            finish_reason="stop",
                        )
                        yield sse(final_chunk)
                        yield b"data: [DONE]\n\n"
                        success = True
                        break

        finally:
            await self._release_backend(backend, success=success)

    async def models(self) -> dict[str, Any]:
        # 簡化版：從第一個可用 backend 取得模型清單
        assert self.client is not None
        last_error = None

        for b in self.backends:
            try:
                r = await self.client.get(f"{b.base_url}/api/tags")
                if r.status_code == 200:
                    data = r.json()
                    models = []
                    for item in data.get("models", []):
                        name = item.get("name", "")
                        models.append(
                            {
                                "id": name,
                                "object": "model",
                                "owned_by": "ollama",
                            }
                        )
                    return {"object": "list", "data": models}
            except Exception as e:
                last_error = str(e)

        raise HTTPException(status_code=503, detail=f"No backend available: {last_error}")


# =========================
# 工具函式
# =========================
def safe_json_or_text(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return resp.text


def extract_ollama_message_content(data: dict[str, Any]) -> str:
    message = data.get("message", {})
    if isinstance(message, dict):
        return message.get("content", "") or ""
    return ""


def make_openai_nonstream_response(
    model: str,
    content: str,
    created: int,
    request_id: str,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    resp = {
        "id": request_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    if meta:
        resp["router_meta"] = meta
    return resp


def make_openai_stream_chunk(
    request_id: str,
    created: int,
    model: str,
    delta: dict[str, Any],
    finish_reason: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }


def sse(data_obj: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n".encode("utf-8")


def verify_and_log_request(req: ChatCompletionsRequest) -> tuple[bool, Optional[str]]:
    """
    驗證 API 金鑰並記錄請求
    
    Return: (is_valid, teacher_name)
    """
    # 如果未配置任何金鑰，則允許全部通過
    if not api_key_config.is_enabled():
        request_logger.log_validation_result(
            teacher_name=None,
            api_key=req.api_key or "未提供",
            model=req.model,
            messages=[m.model_dump() for m in req.messages],
            is_valid=True,
        )
        return True, None

    # 進行金鑰驗證
    is_valid, teacher_name = api_key_config.verify_api_key(req.api_key or "")

    # 記錄驗證結果
    request_logger.log_validation_result(
        teacher_name=teacher_name,
        api_key=req.api_key or "未提供",
        model=req.model,
        messages=[m.model_dump() for m in req.messages],
        is_valid=is_valid,
    )

    return is_valid, teacher_name


router = OllamaRouter(BACKENDS)


# 初始化 API 金鑰配置和日誌記錄器
api_key_config = ApiKeyConfig()
request_logger = RequestLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await router.startup()
    yield
    await router.shutdown()


app = FastAPI(title="Vans OpenAI-Compatible Ollama Router", lifespan=lifespan)


# =========================
# API
# =========================
@app.get("/health")
async def health():
    return await router.health()


@app.get("/v1/models")
async def list_models():
    return await router.models()


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionsRequest, request: Request):
    # 驗證 API 金鑰並記錄請求
    is_valid, teacher_name = verify_and_log_request(req)

    # 如果金鑰驗證失敗且已配置了金鑰，則拒絕請求
    if not is_valid and api_key_config.is_enabled():
        raise HTTPException(status_code=401, detail="無效的 API 金鑰")

    if req.stream:
        generator = router.chat_completions_stream(req)
        return StreamingResponse(generator, media_type="text/event-stream")

    data = await router.chat_completions_nonstream(req)
    return JSONResponse(content=data)