from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMRequest:
    system: str
    user: str
    model: str
    temperature: float = 0.0


class LLMError(RuntimeError):
    """Lỗi khi gọi LLM (T-301 §5 bước 5). `code` thuộc tập đã khai báo
    trong `core/errors.py`: `SERVICE_BUSY` | `ANSWER_TIMEOUT` |
    `ANSWER_INTERRUPTED`. `tokens_emitted > 0` nghĩa là đã gửi nội dung
    cho client trước khi lỗi xảy ra — quyết định có retry hay không."""

    def __init__(self, code: str, tokens_emitted: int = 0) -> None:
        super().__init__(code)
        self.code = code
        self.tokens_emitted = tokens_emitted


class LLMPort:
    async def stream(self, request: LLMRequest) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # pragma: no cover - makes this an async generator for mypy
