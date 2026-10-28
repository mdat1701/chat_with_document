"""Cổng embedding nội bộ, tách lõi ingestion khỏi TEI."""

from typing import Protocol


class EmbeddingPort(Protocol):
    @property
    def dimensions(self) -> int: ...

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
