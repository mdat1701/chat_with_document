"""Adapter gọi TEI cross-encoder reranker (T-401 §5 bước 3)."""

import httpx

from app.core.config import get_settings


class TeiRerankerAdapter:
    def rerank(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        try:
            response = httpx.post(
                f"{get_settings().tei_rerank_url.rstrip('/')}/rerank",
                json={"query": query, "texts": documents, "raw_scores": False},
                timeout=10.0,
            )
            response.raise_for_status()
            results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("TEI reranker unavailable") from exc
        if not isinstance(results, list) or len(results) != len(documents):
            raise RuntimeError("TEI reranker returned an unexpected shape")
        # TEI trả về đã sắp theo điểm giảm dần kèm `index` gốc — khôi phục
        # lại đúng thứ tự đầu vào để caller không phải tự ánh xạ.
        scores = [0.0] * len(documents)
        for item in results:
            scores[int(item["index"])] = float(item["score"])
        return scores
