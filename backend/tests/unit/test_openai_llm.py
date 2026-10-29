"""Kiểm thử resilience của `OpenAICompatibleLLM` (T-301) — trước phiên
này `app/adapters/openai_llm.py` không có test nào và không có
retry/circuit-breaker/phân loại lỗi thật (chỉ gọi `httpx` trần).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest

from app.adapters import openai_llm
from app.ports.llm_port import LLMError, LLMRequest


class _FakeSettings:
    llm_api_key = ""
    llm_base_url = "http://fake"
    llm_timeout_s = 50
    llm_breaker_failure_threshold = 3
    llm_breaker_open_seconds = 30


@pytest.fixture(autouse=True)
def _reset_breaker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_llm, "_consecutive_failures", 0)
    monkeypatch.setattr(openai_llm, "_breaker_open_until", 0.0)
    monkeypatch.setattr(openai_llm, "get_settings", lambda: _FakeSettings())


def _request() -> LLMRequest:
    return LLMRequest(system="s", user="u", model="m")


async def test_stream_succeeds_and_yields_tokens(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ok(_self: object, _request: LLMRequest, _settings: object) -> AsyncIterator[str]:
        yield "xin "
        yield "chào"

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _ok)
    adapter = openai_llm.OpenAICompatibleLLM()

    tokens = [token async for token in adapter.stream(_request())]

    assert tokens == ["xin ", "chào"]


async def test_retries_once_before_first_token_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    async def _flaky_then_ok(
        _self: object, _request: LLMRequest, _settings: object
    ) -> AsyncIterator[str]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ConnectError("boom")
        yield "ok"

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _flaky_then_ok)
    adapter = openai_llm.OpenAICompatibleLLM()

    tokens = [token async for token in adapter.stream(_request())]

    assert tokens == ["ok"]
    assert attempts["count"] == 2


async def test_fails_before_first_token_twice_raises_service_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _always_fails(
        _self: object, _request: LLMRequest, _settings: object
    ) -> AsyncIterator[str]:
        raise httpx.ConnectError("boom")
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _always_fails)
    adapter = openai_llm.OpenAICompatibleLLM()

    with pytest.raises(LLMError) as error:
        async for _ in adapter.stream(_request()):
            pass

    assert error.value.code == "SERVICE_BUSY"
    assert error.value.tokens_emitted == 0


async def test_failure_after_first_token_is_interrupted_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    async def _dies_mid_stream(
        _self: object, _request: LLMRequest, _settings: object
    ) -> AsyncIterator[str]:
        attempts["count"] += 1
        yield "phần đầu"
        raise httpx.ReadError("dropped")

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _dies_mid_stream)
    adapter = openai_llm.OpenAICompatibleLLM()

    collected: list[str] = []
    with pytest.raises(LLMError) as error:
        async for token in adapter.stream(_request()):
            collected.append(token)

    assert collected == ["phần đầu"]
    assert error.value.code == "ANSWER_INTERRUPTED"
    assert error.value.tokens_emitted == 1
    assert attempts["count"] == 1  # không retry sau khi đã gửi nội dung


async def test_timeout_before_first_token_raises_answer_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _times_out(
        _self: object, _request: LLMRequest, _settings: object
    ) -> AsyncIterator[str]:
        raise httpx.ReadTimeout("too slow")
        yield  # pragma: no cover

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _times_out)
    adapter = openai_llm.OpenAICompatibleLLM()

    with pytest.raises(LLMError) as error:
        async for _ in adapter.stream(_request()):
            pass

    assert error.value.code == "ANSWER_TIMEOUT"


class _FakeStreamResponse:
    """Mô phỏng `httpx.Response` streaming đủ để `_stream_once` đọc được,
    không dùng `httpx.MockTransport` vì cần theo dõi `__aexit__` có được
    gọi hay không khi generator bị hủy giữa chừng."""

    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.closed = False

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):  # type: ignore[no-untyped-def]
        for line in self._lines:
            yield line

    async def __aenter__(self) -> _FakeStreamResponse:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        self.closed = True
        return False


class _FakeAsyncClient:
    def __init__(self, response: _FakeStreamResponse) -> None:
        self._response = response
        self.closed = False

    def stream(self, *_args: object, **_kwargs: object) -> _FakeStreamResponse:
        return self._response

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        self.closed = True
        return False


async def test_cancelling_consumer_closes_underlying_http_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T-301 §7: hủy coroutine giữa chừng phải đóng kết nối HTTP tới LLM
    — không chỉ dừng đọc token phía server. Xác nhận bằng `__aexit__`
    thật của client/response giả lập có được gọi khi `.aclose()` generator,
    không chỉ đọc code suy luận hành vi của `async with`."""
    response = _FakeStreamResponse(
        [
            'data: {"choices":[{"delta":{"content":"a"}}]}',
            'data: {"choices":[{"delta":{"content":"b"}}]}',
            'data: {"choices":[{"delta":{"content":"c"}}]}',
        ]
    )
    fake_client = _FakeAsyncClient(response)
    monkeypatch.setattr(openai_llm.httpx, "AsyncClient", lambda **_kwargs: fake_client)
    adapter = openai_llm.OpenAICompatibleLLM()

    generator = adapter.stream(_request())
    first_token = await generator.__anext__()
    assert first_token == "a"

    await generator.aclose()

    assert fake_client.closed is True
    assert response.closed is True


async def test_circuit_breaker_opens_after_threshold_and_skips_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    async def _always_fails(
        _self: object, _request: LLMRequest, _settings: object
    ) -> AsyncIterator[str]:
        calls["count"] += 1
        raise httpx.ConnectError("boom")
        yield  # pragma: no cover

    monkeypatch.setattr(openai_llm.OpenAICompatibleLLM, "_stream_once", _always_fails)
    adapter = openai_llm.OpenAICompatibleLLM()

    # Ngưỡng test = 3 lỗi liên tiếp. Mỗi lần `stream()` thất bại hoàn
    # toàn được tính là 1 lỗi liên tiếp (dù bên trong đã tự retry 1 lần
    # trước token đầu, tốn 2 lệnh gọi `_stream_once` thật). Gọi đủ 3 lần
    # `stream()` thất bại để chạm ngưỡng và mở breaker.
    for _ in range(3):
        with pytest.raises(LLMError):
            async for _ in adapter.stream(_request()):
                pass

    calls_before_breaker_opens = calls["count"]
    assert calls_before_breaker_opens > 0

    with pytest.raises(LLMError) as error:
        async for _ in adapter.stream(_request()):
            pass

    assert error.value.code == "SERVICE_BUSY"
    # Breaker đang mở => KHÔNG gọi thêm `_stream_once` nào nữa.
    assert calls["count"] == calls_before_breaker_opens
