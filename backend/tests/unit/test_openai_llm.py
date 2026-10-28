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
