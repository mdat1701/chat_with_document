"""Cổng rerank cross-encoder (T-401 §5 bước 3)."""

from typing import Protocol


class RerankerPort(Protocol):
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        """Trả điểm rerank cho từng phần tử của `documents`, CÙNG THỨ TỰ
        đầu vào (không tự sắp xếp lại) — caller tự quyết định cách dùng
        điểm số."""
        ...
