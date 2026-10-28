"""Kiểm thử cổng bằng chứng (T-302) — trước phiên này `app/modules/retrieval`
không có test đơn vị nào. Tập trung vào đúng lỗi logic đã sửa: `top_score`
(độ tương đồng cosine CHƯA qua RRF) phải được so sánh trực tiếp với `τ`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from app.core.errors import DomainError
from app.modules.retrieval import service


@dataclass
class _FakeChunk:
    id: int
    document_id: object
    page_start: int
    page_end: int
    content: str


class _FakeResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeSession:
    def __init__(
        self, vector_rows: list[tuple[object, ...]], fts_rows: list[tuple[object, ...]]
    ) -> None:
        self._results = [_FakeResult(vector_rows), _FakeResult(fts_rows)]

    async def execute(self, _statement: object) -> _FakeResult:
        return self._results.pop(0)


def _chunk(chunk_id: int, document_id: object | None = None) -> _FakeChunk:
    return _FakeChunk(
        id=chunk_id,
        document_id=document_id or uuid4(),
        page_start=1,
        page_end=2,
        content="nội dung đoạn trích",
    )


async def test_retrieve_raises_no_ready_documents_when_no_candidates() -> None:
    session = _FakeSession(vector_rows=[], fts_rows=[])

    with pytest.raises(DomainError) as error:
        await service.retrieve(session, uuid4(), [0.1, 0.2], "câu hỏi")

    assert error.value.code == "NO_READY_DOCUMENTS"


async def test_retrieve_blocks_low_relevance_evidence_gate() -> None:
    """τ mặc định 0.25 — candidate có cosine similarity thấp hơn PHẢI bị chặn,
    không được lọt qua chỉ vì có mặt trong top-k (lỗi logic đã sửa)."""
    chunk = _chunk(1)
    session = _FakeSession(vector_rows=[(chunk, "A.pdf", 0.05)], fts_rows=[])

    evidence = await service.retrieve(
        session, uuid4(), [0.1, 0.2], "câu hỏi kiến thức chung", min_score=0.25
    )

    assert evidence == []


async def test_retrieve_passes_gate_when_top_score_above_tau() -> None:
    chunk = _chunk(1)
    session = _FakeSession(vector_rows=[(chunk, "A.pdf", 0.9)], fts_rows=[])

    evidence = await service.retrieve(
        session, uuid4(), [0.1, 0.2], "câu hỏi có đáp án", min_score=0.25
    )

    assert len(evidence) == 1
    assert evidence[0].document_id == chunk.document_id


async def test_retrieve_gate_uses_raw_vector_score_not_rrf_constant() -> None:
    """Hồi quy cho lỗi cũ: trước đây điều kiện lọc là
    `score >= 1 / (rrf_k + top_k)` (luôn đúng với mọi ứng viên trong
    top-k) thay vì so với `τ` thật. Một candidate với cosine similarity
    rất thấp (0.01) nhưng lọt top-k phải vẫn bị cổng bằng chứng chặn."""
    chunk = _chunk(1)
    session = _FakeSession(vector_rows=[(chunk, "A.pdf", 0.01)], fts_rows=[])

    evidence = await service.retrieve(
        session, uuid4(), [0.1, 0.2], "câu hỏi", top_k=8, rrf_k=60, min_score=0.15
    )

    assert evidence == []


def test_diversify_evidence_caps_chunks_per_document() -> None:
    doc_a, doc_b = uuid4(), uuid4()
    items = [
        service.Evidence(doc_a, "A.pdf", 1, 1, "x", 0.9),
        service.Evidence(doc_a, "A.pdf", 2, 2, "x", 0.8),
        service.Evidence(doc_a, "A.pdf", 3, 3, "x", 0.7),
        service.Evidence(doc_b, "B.pdf", 1, 1, "x", 0.6),
    ]

    selected = service.diversify_evidence(items, max_chunks_per_doc=2, limit=8)

    assert sum(1 for item in selected if item.document_id == doc_a) == 2
    assert any(item.document_id == doc_b for item in selected)
