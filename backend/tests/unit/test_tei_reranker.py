"""Kiểm thử `TeiRerankerAdapter` (T-401) — xác nhận khôi phục đúng thứ tự
đầu vào từ phản hồi TEI (TEI trả về đã sắp theo điểm giảm dần kèm `index`
gốc, không theo thứ tự request)."""

from __future__ import annotations

import httpx
import pytest

from app.adapters import tei_reranker


class _FakeResponse:
    def __init__(self, payload: object, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)  # type: ignore[arg-type]

    def json(self) -> object:
        return self._payload


def test_rerank_restores_original_order(monkeypatch: pytest.MonkeyPatch) -> None:
    # TEI trả về đã sắp theo điểm giảm dần (index 2 cao nhất) — adapter
    # phải khôi phục lại đúng thứ tự đầu vào (0, 1, 2).
    monkeypatch.setattr(
        tei_reranker.httpx,
        "post",
        lambda *_a, **_k: _FakeResponse(
            [{"index": 2, "score": 0.9}, {"index": 0, "score": 0.5}, {"index": 1, "score": 0.1}]
        ),
    )
    adapter = tei_reranker.TeiRerankerAdapter()

    scores = adapter.rerank("câu hỏi", ["a", "b", "c"])

    assert scores == [0.5, 0.1, 0.9]


def test_rerank_empty_documents_skips_call(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_a: object, **_k: object) -> _FakeResponse:
        raise AssertionError("không nên gọi HTTP khi documents rỗng")

    monkeypatch.setattr(tei_reranker.httpx, "post", _fail)
    adapter = tei_reranker.TeiRerankerAdapter()

    assert adapter.rerank("câu hỏi", []) == []


def test_rerank_raises_runtime_error_on_shape_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tei_reranker.httpx, "post", lambda *_a, **_k: _FakeResponse([{"index": 0, "score": 0.5}])
    )
    adapter = tei_reranker.TeiRerankerAdapter()

    with pytest.raises(RuntimeError):
        adapter.rerank("câu hỏi", ["a", "b"])
