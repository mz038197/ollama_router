import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator

import httpx

from src.domain.errors import ServiceUnavailableError, UpstreamServiceError
from src.domain.entities.chat import ChatCompletionRequest


@dataclass
class BackendState:
    base_url: str
    semaphore: asyncio.Semaphore
    active: int = 0
    completed: int = 0
    failed: int = 0


class OllamaGateway:
    def __init__(
        self,
        backend_urls: list[str],
        timeout: float = 300.0,
        max_concurrent_per_backend: int = 1,
        default_temperature: float = 0.7,
        default_num_predict: int = 256,
    ):
        self.backends = [
            BackendState(
                base_url=url,
                semaphore=asyncio.Semaphore(max_concurrent_per_backend),
            )
            for url in backend_urls
        ]
        self.timeout = timeout
        self.default_temperature = default_temperature
        self.default_num_predict = default_num_predict
        self.client: httpx.AsyncClient | None = None
        self.lock = asyncio.Lock()
        self.waiting_count = 0

    async def startup(self) -> None:
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def shutdown(self) -> None:
        if self.client:
            await self.client.aclose()

    async def health(self) -> dict[str, Any]:
        result = []
        assert self.client is not None
        for backend in self.backends:
            ok = False
            detail = ""
            try:
                response = await self.client.get(f"{backend.base_url}/api/tags")
                ok = response.status_code == 200
                detail = f"HTTP {response.status_code}"
            except Exception as e:
                detail = str(e)

            result.append(
                {
                    "base_url": backend.base_url,
                    "ok": ok,
                    "active": backend.active,
                    "completed": backend.completed,
                    "failed": backend.failed,
                    "detail": detail,
                }
            )

        return {"queue_waiting": self.waiting_count, "backends": result}

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

    async def _release_backend(self, backend: BackendState, success: bool) -> None:
        async with self.lock:
            backend.active -= 1
            if success:
                backend.completed += 1
            else:
                backend.failed += 1
            backend.semaphore.release()

    def _to_ollama_payload(self, req: ChatCompletionRequest) -> dict[str, Any]:
        messages = []
        for msg in req.messages:
            message_obj = {"role": msg.role, "content": msg.content}
            if msg.images:
                message_obj["images"] = msg.images
            messages.append(message_obj)

        return {
            "model": req.model,
            "messages": messages,
            "stream": req.stream,
            "options": {
                "temperature": req.temperature if req.temperature is not None else self.default_temperature,
                "num_predict": req.max_tokens if req.max_tokens is not None else self.default_num_predict,
            },
        }

    async def chat_completions_nonstream(self, req: ChatCompletionRequest) -> dict[str, Any]:
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
            response = await self.client.post(f"{backend.base_url}/api/chat", json=payload)
            if response.status_code != 200:
                raise UpstreamServiceError(
                    status_code=response.status_code,
                    backend=backend.base_url,
                    body=safe_json_or_text(response),
                )
            ollama_data = response.json()
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

    async def chat_completions_stream(self, req: ChatCompletionRequest) -> AsyncGenerator[bytes, None]:
        enqueue_time = time.perf_counter()
        async with self.lock:
            self.waiting_count += 1
            queue_position_estimate = max(self.waiting_count - len(self.backends), 0)

        backend = await self._pick_backend()
        async with self.lock:
            self.waiting_count -= 1

        success = False
        released = False
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
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise UpstreamServiceError(
                        status_code=response.status_code,
                        backend=backend.base_url,
                        body=body.decode("utf-8", errors="ignore"),
                    )

                first_chunk = make_openai_stream_chunk(
                    request_id=request_id,
                    created=created,
                    model=req.model,
                    delta={"role": "assistant", "content": ""},
                )
                yield sse(first_chunk)

                async for line in response.aiter_lines():
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
        except UpstreamServiceError:
            await self._release_backend(backend, success=False)
            released = True
            raise
        finally:
            if not released:
                await self._release_backend(backend, success=success)

    async def models(self) -> dict[str, Any]:
        assert self.client is not None
        last_error = None
        for backend in self.backends:
            try:
                response = await self.client.get(f"{backend.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for item in data.get("models", []):
                        name = item.get("name", "")
                        models.append({"id": name, "object": "model", "owned_by": "ollama"})
                    return {"object": "list", "data": models}
            except Exception as e:
                last_error = str(e)

        raise ServiceUnavailableError(message=f"No backend available: {last_error}")


def safe_json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except Exception:
        return response.text


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
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = {
        "id": request_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    if meta:
        response["router_meta"] = meta
    return response


def make_openai_stream_chunk(
    request_id: str,
    created: int,
    model: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def sse(data_obj: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(data_obj, ensure_ascii=False)}\n\n".encode("utf-8")
