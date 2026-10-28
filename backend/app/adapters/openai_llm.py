from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

import httpx

from app.core.config import Settings, get_settings
from app.core.metrics import (
    circuit_breaker_state,
    llm_errors_total,
    llm_tokens_total,
    llm_ttft_seconds,
)
from app.ports.llm_port import LLMError, LLMPort, LLMRequest

# T-301 §5 bước 6: circuit breaker theo tiến trình (module-level, không
# cần Redis cho quy mô MVP-lite) — mở sau N lỗi liên tiếp, tự đóng sau
# `llm_breaker_open_seconds`. Trạng thái dùng chung cho mọi request vì
# `OpenAICompatibleLLM` được tạo mới mỗi lần qua `get_llm_port()`.
_consecutive_failures = 0
_breaker_open_until = 0.0


def _breaker_is_open() -> bool:
    return time.monotonic() < _breaker_open_until


def _record_llm_failure(settings: Settings) -> None:
    global _consecutive_failures, _breaker_open_until  # noqa: PLW0603
    _consecutive_failures += 1
    if _consecutive_failures >= settings.llm_breaker_failure_threshold:
        _breaker_open_until = time.monotonic() + settings.llm_breaker_open_seconds
        circuit_breaker_state.set(1)


def _record_llm_success() -> None:
    global _consecutive_failures, _breaker_open_until  # noqa: PLW0603
    _consecutive_failures = 0
    _breaker_open_until = 0.0
    circuit_breaker_state.set(0)


class OpenAICompatibleLLM(LLMPort):
    async def _stream_once(self, request: LLMRequest, settings: Settings) -> AsyncIterator[str]:
        payload = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "temperature": request.temperature,
            "stream": True,
        }
        headers = (
            {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}
        )
        async with httpx.AsyncClient(timeout=settings.llm_timeout_s) as client:
            async with client.stream(
                "POST", f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                json=payload, headers=headers,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    data = json.loads(line[6:])
                    content = data.get("choices", [{}])[0].get("delta", {}).get("content")
                    if content:
                        yield content

    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        settings = get_settings()
        if _breaker_is_open():
            llm_errors_total.labels(code="SERVICE_BUSY").inc()
            raise LLMError("SERVICE_BUSY")

        llm_tokens_total.labels(direction="in").inc()
        attempt = 0
        while True:
            attempt += 1
            tokens_emitted = 0
            started = time.perf_counter()
            try:
                async for token in self._stream_once(request, settings):
                    if tokens_emitted == 0:
                        llm_ttft_seconds.observe(time.perf_counter() - started)
                    tokens_emitted += 1
                    llm_tokens_total.labels(direction="out").inc()
                    yield token
            except httpx.TimeoutException as exc:
                if tokens_emitted > 0:
                    _record_llm_failure(settings)
                    llm_errors_total.labels(code="ANSWER_INTERRUPTED").inc()
                    raise LLMError("ANSWER_INTERRUPTED", tokens_emitted) from exc
                _record_llm_failure(settings)
                llm_errors_total.labels(code="ANSWER_TIMEOUT").inc()
                raise LLMError("ANSWER_TIMEOUT") from exc
            except Exception as exc:
                if tokens_emitted > 0:
                    _record_llm_failure(settings)
                    llm_errors_total.labels(code="ANSWER_INTERRUPTED").inc()
                    raise LLMError("ANSWER_INTERRUPTED", tokens_emitted) from exc
                if attempt == 1:
                    # T-301 §5 bước 5: retry đúng 1 lần khi lỗi xảy ra
                    # TRƯỚC token đầu tiên (chưa gửi gì cho client).
                    continue
                _record_llm_failure(settings)
                llm_errors_total.labels(code="SERVICE_BUSY").inc()
                raise LLMError("SERVICE_BUSY") from exc
            else:
                _record_llm_success()
                return


class FakeLLM(LLMPort):
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        yield "Chưa cấu hình mô hình ngôn ngữ để trả lời câu hỏi này."
