"""Adapter gọi TEI embedding nội bộ."""

import httpx

from app.core.config import get_settings


class TeiEmbeddingAdapter:
    dimensions = 1024

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            response = httpx.post(
                f"{get_settings().tei_embed_url.rstrip('/')}/embed",
                json={"inputs": texts, "truncate": True},
                timeout=30.0,
            )
            response.raise_for_status()
            vectors = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("TEI embedding unavailable") from exc
        if (
            not isinstance(vectors, list)
            or len(vectors) != len(texts)
            or any(not isinstance(vector, list) for vector in vectors)
            or any(len(vector) != self.dimensions for vector in vectors)
        ):
            raise RuntimeError("TEI returned invalid embedding dimensions")
        return vectors
