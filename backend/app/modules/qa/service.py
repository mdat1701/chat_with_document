"""Hội thoại: dựng prompt, gọi LLM streaming, phát hiện ngôn ngữ,
kiểm tra trích dẫn trước khi trả về client.

Story: US-011 - US-017.
"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.tracing import get_tracer
from app.modules.qa.prompt import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt
from app.modules.retrieval.service import Evidence, diversify_evidence, retrieve
from app.ports.embedding_port import EmbeddingPort
from app.ports.llm_port import LLMPort, LLMRequest
from app.ports.reranker_port import RerankerPort

logger = logging.getLogger(__name__)
_tracer = get_tracer(__name__)

try:
    from lingua import Language, LanguageDetectorBuilder

    _language_detector = LanguageDetectorBuilder.from_languages(
        Language.VIETNAMESE, Language.ENGLISH
    ).build()
except ImportError:
    _language_detector = None


def _contexts(evidence: list[Evidence]) -> list[dict[str, object]]:
    return [
        {
            "document_id": str(item.document_id),
            "document_name": item.document_name,
            "page_start": item.page_start,
            "page_end": item.page_end,
            "content": item.content,
        }
        for item in evidence
    ]


def detect_language(question: str) -> tuple[str, str]:
    if len(question.strip()) < 10:
        return "vi", "other"
    if _language_detector is not None:
        try:
            detected = _language_detector.detect_language_of(question)
        except RuntimeError:
            logger.warning("language detector failed; using heuristic fallback")
        else:
            if detected == Language.VIETNAMESE:
                return "vi", "vi"
            if detected == Language.ENGLISH:
                return "en", "en"
    vietnamese_chars = set("ăâđêôơưĂÂĐÊÔƠƯáàảãạấầẩẫậắằẳẵặ")
    english_words = {"the", "what", "how", "when", "where", "is", "are"}
    vi_score = sum(char in vietnamese_chars for char in question)
    en_score = sum(word in english_words for word in question.lower().split())
    return ("vi", "vi") if vi_score >= en_score else ("en", "en")


async def stream_answer(
    session: AsyncSession,
    owner_id: UUID,
    question: str,
    embedding: EmbeddingPort,
    *,
    llm: LLMPort | None = None,
    document_ids: list[UUID] | None = None,
    reranker: RerankerPort | None = None,
) -> AsyncIterator[tuple[str, object]]:
    question = question.strip()
    settings = get_settings()
    if not question or len(question) > settings.max_question_length:
        raise ValueError("QUESTION_INVALID")
    language, _detected = detect_language(question)
    evidence = await retrieve(
        session, owner_id, embedding.embed_batch([question])[0], question,
        vector_top_k=settings.retrieval_vector_top_k,
        fts_top_k=settings.retrieval_fts_top_k,
        rrf_k=settings.retrieval_rrf_k,
        top_k=settings.rerank_top_in,
        min_score=settings.retrieval_tau,
        document_ids=document_ids,
        reranker=reranker,
    )
    evidence = diversify_evidence(
        evidence, max_chunks_per_doc=settings.rerank_max_chunks_per_doc,
        limit=settings.rerank_top_out,
    )
    contexts = _contexts(evidence)
    if llm is None:
        # `modules.qa` không được chọn adapter LLM cụ thể (nguyên tắc P-01,
        # SADD §2.2.1) — caller (router, T-304) phải tiêm qua `get_llm_port()`.
        raise ValueError("llm provider is required; inject via api.deps.get_llm_port()")
    if not contexts:
        # Cổng bằng chứng (T-302) đã chặn: không gọi LLM khi không có bằng
        # chứng đủ liên quan (P-04, tiết kiệm chi phí R-06).
        yield "complete", {
            "answer": "Không tìm thấy thông tin trong các tài liệu đã chọn.",
            "citations": [],
            "prompt_version": PROMPT_VERSION,
            "answer_type": "not_found",
        }
        return
    provider = llm
    request = LLMRequest(
        system=f"{SYSTEM_PROMPT}\nTrả lời bằng {'tiếng Việt' if language == 'vi' else 'English'}.",
        user=build_prompt(question, contexts),
        model=settings.llm_model,
    )
    chunks: list[str] = []
    async for token in provider.stream(request):
        chunks.append(token)
        yield "token", token
    answer = "".join(chunks)
    names = {str(item["document_id"]): item["document_name"] for item in contexts}
    # Span OTel (SADD §4.3): chỉ đếm số nhãn hợp lệ/bị loại — KHÔNG ghi
    # nội dung câu trả lời hay trích dẫn (P-03).
    with _tracer.start_as_current_span("qa.validate_citations") as span:
        raw_citations = re.findall(r"\[doc:([^ ]+) p:(\d+)-(\d+)\]", answer)
        # T-303: chỉ chấp nhận trích dẫn trỏ tới document_id THẬT có trong
        # bằng chứng đã truy xuất — loại trích dẫn bịa (LLM có thể tạo ra
        # id không tồn tại trong `contexts`) thay vì chỉ kiểm tra cú pháp.
        valid_citations = [
            (doc, start, end) for doc, start, end in raw_citations if doc in names
        ]
        span.set_attribute("raw_citation_count", len(raw_citations))
        span.set_attribute("valid_citation_count", len(valid_citations))
        span.set_attribute("rejected_citation_count", len(raw_citations) - len(valid_citations))
    if not valid_citations:
        answer = "Không tìm thấy đủ bằng chứng trong các tài liệu đã chọn."
    citation_items = [
        {
            "document_id": doc,
            "document_name": names.get(doc),
            "page_start": int(start),
            "page_end": int(end),
        }
        for doc, start, end in valid_citations
    ]
    yield "complete", {
        "answer": answer,
        "citations": citation_items,
        "prompt_version": PROMPT_VERSION,
        "answer_type": "answered" if citation_items else "not_found",
    }
