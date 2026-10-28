"""Truy vấn vector trong phạm vi owner_id, cổng bằng chứng
(evidence gate) và kiểm tra trích dẫn trước khi trả cho qa.

Story: US-011 - US-014.

Ngoại lệ duy nhất theo SADD Sec 2.2.1: được phép đọc bảng chunk do
ingestion ghi (ignore_imports khai báo trong pyproject.toml).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.core.metrics import retrieval_top_score
from app.modules.documents.models import Chunk, Document
from app.ports.reranker_port import RerankerPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Evidence:
    document_id: UUID
    document_name: str
    page_start: int
    page_end: int
    content: str
    score: float


async def retrieve(
    session: AsyncSession,
    owner_id: UUID,
    query_vector: list[float],
    query_text: str = "",
    *,
    top_k: int = 8,
    vector_top_k: int | None = None,
    fts_top_k: int | None = None,
    rrf_k: int = 60,
    document_ids: list[UUID] | None = None,
    min_score: float = 0.25,
    rerank_candidate_limit: int = 20,
    reranker: RerankerPort | None = None,
) -> list[Evidence]:
    vector_statement = (
        select(
            Chunk,
            Document.name,
            (1 - Chunk.embedding.cosine_distance(query_vector)).label("score"),
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.owner_id == owner_id,
            Document.owner_id == owner_id,
            Document.status == "ready",
        )
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(vector_top_k or top_k)
    )
    if document_ids:
        vector_statement = vector_statement.where(Chunk.document_id.in_(document_ids))
    vector_rows = (await session.execute(vector_statement)).all()
    fts_statement = (
        select(
            Chunk,
            Document.name,
            func.ts_rank_cd(
                Chunk.tsv,
                func.websearch_to_tsquery("simple", func.unaccent(query_text)),
            ).label("score"),
        )
        .join(Document, Document.id == Chunk.document_id)
        .where(
            Chunk.owner_id == owner_id,
            Document.owner_id == owner_id,
            Document.status == "ready",
            Chunk.tsv.op("@@")(
                func.websearch_to_tsquery("simple", func.unaccent(query_text))
            ),
        )
        .order_by(desc("score"))
        .limit(fts_top_k or top_k)
    )
    if document_ids:
        fts_statement = fts_statement.where(Chunk.document_id.in_(document_ids))
    fts_rows = (await session.execute(fts_statement)).all()
    if not vector_rows and not fts_rows:
        raise DomainError("NO_READY_DOCUMENTS")

    ranked: dict[int, tuple[Chunk, str, float]] = {}
    for rank, (chunk, name, _score) in enumerate(vector_rows, 1):
        ranked[chunk.id] = (chunk, name, 1 / (rrf_k + rank))
    for rank, (chunk, name, _score) in enumerate(fts_rows, 1):
        previous = ranked.get(chunk.id)
        ranked[chunk.id] = (
            chunk,
            name,
            (previous[2] if previous else 0) + 1 / (rrf_k + rank),
        )
    rerank_candidates = sorted(ranked.values(), key=lambda item: item[2], reverse=True)[
        :rerank_candidate_limit
    ]

    rerank_scores: list[float] | None = None
    if reranker is not None and rerank_candidates:
        try:
            rerank_scores = reranker.rerank(
                query_text, [chunk.content for chunk, _, _ in rerank_candidates]
            )
        except RuntimeError:
            # T-401 §6: reranker lỗi/timeout -> bỏ qua bước rerank, dùng
            # thẳng top-k từ RRF; KHÔNG được làm hỏng cả câu trả lời.
            logger.warning("TEI reranker unavailable, falling back to RRF ranking")
            rerank_scores = None

    if rerank_scores is not None:
        # T-401 §5 bước 5: cổng bằng chứng áp lên điểm rerank cao nhất khi
        # có reranker — thay cho điểm cosine thô (T-302).
        scored = sorted(
            zip(rerank_candidates, rerank_scores, strict=True),
            key=lambda pair: pair[1],
            reverse=True,
        )
        top_score = scored[0][1] if scored else 0.0
        retrieval_top_score.observe(top_score)
        if top_score < min_score:
            return []
        ordered = [(chunk, name, score) for (chunk, name, _rrf), score in scored[:top_k]]
    else:
        # Cổng bằng chứng (T-302, P-04): dùng độ tương đồng cosine CHƯA
        # qua RRF làm tín hiệu liên quan thật khi không có reranker.
        top_vector_score = max((float(score) for _, _, score in vector_rows), default=0.0)
        retrieval_top_score.observe(top_vector_score)
        if top_vector_score < min_score:
            return []
        ordered = rerank_candidates[:top_k]

    return [
        Evidence(
            document_id=chunk.document_id,
            document_name=name or "",
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            content=chunk.content,
            score=float(score) if rerank_scores is not None else min(1.0, float(score) * rrf_k / 2),
        )
        for chunk, name, score in ordered
    ]


def diversify_evidence(
    evidence: list[Evidence], *, max_chunks_per_doc: int = 4, limit: int = 8
) -> list[Evidence]:
    document_count = len({item.document_id for item in evidence})
    if document_count <= 1:
        return evidence[:limit]
    selected: list[Evidence] = []
    counts: dict[UUID, int] = {}
    for item in evidence:
        if counts.get(item.document_id, 0) >= max_chunks_per_doc:
            continue
        selected.append(item)
        counts[item.document_id] = counts.get(item.document_id, 0) + 1
        if len(selected) == limit:
            break
    return selected
