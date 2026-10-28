from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.tei_embedding import TeiEmbeddingAdapter
from app.api.deps import CurrentUser, get_current_user, get_db_session, get_llm_port
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.ratelimit import check_rate_limit
from app.core.redis_client import get_redis
from app.modules.analytics.service import record_event
from app.modules.documents.models import Document
from app.modules.qa.models import Answer
from app.modules.qa.service import stream_answer
from app.ports.llm_port import LLMError, LLMPort

router = APIRouter(prefix="/conversations", tags=["conversations"])


class QuestionRequest(BaseModel):
    text: str = Field(min_length=1)


@router.post("", status_code=201)
async def create_conversation(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    conversation_id = uuid4()
    redis = get_redis()
    await redis.set(
        f"conversation:{current_user.id}:{conversation_id}",
        json.dumps({"turn_index": 0}),
        ex=timedelta(hours=24),
    )
    return {"conversation_id": str(conversation_id)}


@router.post("/{conversation_id}/questions")
async def ask_question(
    conversation_id: UUID,
    payload: QuestionRequest,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    llm: LLMPort = Depends(get_llm_port),
) -> StreamingResponse:
    question = payload.text.strip()
    if not question or len(question) > get_settings().max_question_length:
        raise DomainError("QUESTION_INVALID")
    rate = await check_rate_limit(
        get_redis(), key=f"rl:question:{current_user.id}", limit=10, window_seconds=60
    )
    if not rate.allowed:
        raise DomainError("RATE_LIMITED", {"retry_after_seconds": rate.retry_after_seconds})
    ready_count = int(
        (
            await session.execute(
                select(func.count()).select_from(Document).where(
                    Document.owner_id == UUID(current_user.id), Document.status == "ready"
                )
            )
        ).scalar_one()
    )
    if ready_count == 0:
        raise DomainError("NO_READY_DOCUMENTS")
    answer_id = uuid4()
    started = time.perf_counter()

    async def stream() -> AsyncIterator[str]:
        meta_payload = {"answer_id": str(answer_id), "ready_doc_count": ready_count}
        yield f"event: meta\ndata: {json.dumps(meta_payload)}\n\n"
        try:
            complete: dict[str, object] | None = None
            async for event, value in stream_answer(
                session, UUID(current_user.id), question, TeiEmbeddingAdapter(), llm=llm
            ):
                if await request.is_disconnected():
                    return
                if event == "token":
                    delta_payload = json.dumps({"text": value}, ensure_ascii=False)
                    yield f"event: delta\ndata: {delta_payload}\n\n"
                else:
                    complete = cast("dict[str, object]", value)
            if complete is None:
                raise RuntimeError("empty answer")
            citations = cast("list[dict[str, object]]", complete["citations"])
            citations_payload = json.dumps({"items": citations}, ensure_ascii=False)
            yield f"event: citations\ndata: {citations_payload}\n\n"
            latency_ms = int((time.perf_counter() - started) * 1000)
            done_payload = {
                "type": complete["answer_type"],
                "latency_ms": latency_ms,
                "uncited": not citations,
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
            session.add(
                Answer(
                    id=answer_id,
                    owner_id=UUID(current_user.id),
                    conversation_id=conversation_id,
                    turn_index=0,
                    answer_type=complete["answer_type"],
                    latency_ms=latency_ms,
                    citation_count=len(citations),
                    cited_doc_count=len({item["document_id"] for item in citations}),
                    prompt_version=complete["prompt_version"],
                    model_id=get_settings().llm_model,
                    created_at=datetime.now(UTC),
                )
            )
            await record_event(
                session,
                "answer_rendered",
                user_id=UUID(current_user.id),
                props={
                    "latency_ms": latency_ms,
                    "answer_type": complete["answer_type"],
                    "citation_count": len(citations),
                },
            )
            await session.commit()
        except LLMError as exc:
            # T-301: phân loại lỗi theo mã thật (SERVICE_BUSY/ANSWER_TIMEOUT/
            # ANSWER_INTERRUPTED) thay vì gộp chung một mã — client (IR-01)
            # cần biết có nên ẩn thẻ nguồn hay không theo từng trường hợp.
            yield f'event: error\ndata: {{"code":"{exc.code}"}}\n\n'
        except Exception:
            yield 'event: error\ndata: {"code":"SERVICE_BUSY"}\n\n'

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
