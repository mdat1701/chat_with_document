"""Authenticated runtime configuration endpoint (T-105, API-02)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.deps import CurrentUser, get_current_user
from app.core.config import get_settings

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_config(
    response: Response,
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    settings = get_settings()
    response.headers["Cache-Control"] = "private, max-age=300"
    return {
        "max_file_size_bytes": settings.max_file_size_bytes,
        "max_documents": settings.max_documents,
        "max_pages": settings.max_pages,
        "retention_days": settings.retention_days,
        "max_question_length": settings.max_question_length,
        "answer_timeout_ms": settings.answer_timeout_ms,
        "features": {"citation_page_numbers": settings.citation_page_numbers},
        "retrieval": {
            "tau": settings.retrieval_tau,
            "top_k": settings.rerank_top_out,
            "max_chunks_per_doc": settings.rerank_max_chunks_per_doc,
        },
        "supported_languages": list(settings.supported_languages),
    }
