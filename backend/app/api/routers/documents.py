"""Document upload API (T-108)."""

from __future__ import annotations

import asyncio
import hashlib
import unicodedata
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.celery_queue import CeleryQueueAdapter
from app.api.deps import CurrentUser, get_current_user, get_db_session
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.metrics import sse_connections
from app.core.models import AuditLog
from app.core.ratelimit import check_rate_limit
from app.core.redis_client import get_redis
from app.modules.analytics.service import record_event
from app.modules.documents.models import Document
from app.modules.documents.service import delete_document_use_case
from app.modules.identity.models import AppUser
from app.ports.queue_port import QueuePort

router = APIRouter(prefix="/documents", tags=["documents"])
_PDF_MAGIC = b"%PDF-"


@router.get("")
async def list_documents(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[dict[str, object]]:
    rows = (
        await session.execute(
            select(Document)
            .where(Document.owner_id == UUID(current_user.id), Document.status != "deleting")
            .order_by(Document.uploaded_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "size_bytes": item.size_bytes,
            "page_count": item.page_count,
            "status": item.status,
            "error_code": item.error_code,
        }
        for item in rows
    ]


@router.get("/events")
async def document_events(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> StreamingResponse:
    async def stream() -> AsyncIterator[str]:
        pubsub = get_redis().pubsub()
        await pubsub.subscribe(f"doc-status:{current_user.id}")
        sse_connections.inc()
        try:
            event_id = 0
            while not await request.is_disconnected():
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
                if message and message["type"] == "message":
                    event_id += 1
                    yield f"id: {event_id}\nevent: status\ndata: {message['data']}\n\n"
                else:
                    yield ": ping\n\n"
                await asyncio.sleep(0)
        finally:
            sse_connections.dec()
            await pubsub.unsubscribe()
            await pubsub.close()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def get_queue() -> QueuePort:
    return CeleryQueueAdapter()


def _safe_name(filename: str | None) -> str:
    name = unicodedata.normalize("NFC", Path(filename or "document.pdf").name).strip()
    return name or "document.pdf"


async def _unique_name(
    session: AsyncSession, owner_id: object, name: str, mode: str
) -> str:
    existing = (
        await session.execute(
            select(Document.name).where(
                Document.owner_id == owner_id,
                func.lower(Document.name) == name.lower(),
                Document.status != "deleting",
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        return name
    if mode == "reject":
        raise DomainError("DUPLICATE_NAME", {"name": name})
    if mode == "replace":
        await session.execute(
            update(Document)
            .where(
                Document.owner_id == owner_id,
                func.lower(Document.name) == name.lower(),
                Document.status != "deleting",
            )
            .values(status="deleting")
        )
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    index = 2
    while True:
        candidate = f"{stem} ({index}){suffix}"
        found = (
            await session.execute(
                select(Document.id).where(
                    Document.owner_id == owner_id,
                    func.lower(Document.name) == candidate.lower(),
                    Document.status != "deleting",
                )
            )
        ).scalar_one_or_none()
        if found is None:
            return candidate
        index += 1


@router.post("", status_code=201)
async def upload_document(
    file: UploadFile,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    queue: Annotated[QueuePort, Depends(get_queue)],
    content_length: Annotated[int | None, Header()] = None,
    on_duplicate: Annotated[str, Query(pattern="^(reject|replace|keep_both)$")] = "reject",
) -> dict[str, object]:
    settings = get_settings()
    limit = await check_rate_limit(
        get_redis(),
        key=f"rl:upload:{current_user.id}",
        limit=60,
        window_seconds=3600,
        scope="upload",
    )
    if not limit.allowed:
        raise DomainError("RATE_LIMITED", {"retry_after_seconds": limit.retry_after_seconds})
    if content_length is not None and content_length > settings.max_file_size_bytes:
        raise DomainError("FILE_TOO_LARGE", {"max_mb": settings.max_file_size_bytes // 1_048_576})

    prefix = await file.read(len(_PDF_MAGIC))
    if prefix != _PDF_MAGIC:
        raise DomainError("FILE_NOT_PDF")

    owner_id = current_user.id
    owner_uuid = UUID(owner_id)
    owner = (
        await session.execute(
            select(AppUser).where(AppUser.id == owner_uuid).with_for_update()
        )
    ).scalar_one_or_none()
    if owner is None:
        raise DomainError("SESSION_EXPIRED")
    count = (
        await session.execute(
            select(func.count()).select_from(Document).where(
                Document.owner_id == owner_uuid, Document.status != "deleting"
            )
        )
    ).scalar_one()
    if count >= settings.max_documents:
        raise DomainError("QUOTA_EXCEEDED", {"max": settings.max_documents})

    name = await _unique_name(session, owner_uuid, _safe_name(file.filename), on_duplicate)
    document_id = uuid4()
    uploaded_at = datetime.now(UTC)
    blob_key = f"owner/{owner_id}/{document_id}.pdf"
    path = Path(settings.blob_dir) / blob_key
    path.parent.mkdir(parents=True, exist_ok=True)
    size_bytes = 0
    digest = hashlib.sha256()
    try:
        with path.open("wb") as blob:
            blob.write(prefix)
            digest.update(prefix)
            size_bytes = len(prefix)
            while chunk := await file.read(1024 * 1024):
                size_bytes += len(chunk)
                if size_bytes > settings.max_file_size_bytes:
                    raise DomainError(
                        "FILE_TOO_LARGE",
                        {"max_mb": settings.max_file_size_bytes // 1_048_576},
                    )
                blob.write(chunk)
                digest.update(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        await session.rollback()
        raise

    document = Document(
        id=document_id,
        owner_id=owner_uuid,
        name=name,
        size_bytes=size_bytes,
        status="processing",
        blob_key=blob_key,
        sha256=digest.hexdigest(),
        uploaded_at=uploaded_at,
        expires_at=uploaded_at + timedelta(days=settings.retention_days),
    )
    session.add(document)
    try:
        await session.commit()
    except Exception:
        path.unlink(missing_ok=True)
        await session.rollback()
        raise
    try:
        queue.enqueue("ingestion.process", {"document_id": str(document_id)})
    except Exception:
        document.status = "failed"
        document.error_code = "INGESTION_FAILED"
        await session.commit()
        raise
    return {
        "id": str(document.id),
        "name": document.name,
        "size_bytes": document.size_bytes,
        "page_count": None,
        "status": document.status,
        "error_code": None,
        "uploaded_at": document.uploaded_at,
        "expires_at": document.expires_at,
    }


@router.post("/{document_id}/retry", status_code=202)
async def retry_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    queue: Annotated[QueuePort, Depends(get_queue)],
) -> dict[str, object]:
    document = (
        await session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == UUID(current_user.id),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise DomainError("DOC_NOT_FOUND")
    if document.status != "failed" or document.error_code not in {
        "UPLOAD_NETWORK",
        "INGESTION_FAILED",
    }:
        raise DomainError("RETRY_NOT_ALLOWED")
    document.status = "processing"
    document.error_code = None
    await session.commit()
    try:
        queue.enqueue("ingestion.process", {"document_id": str(document_id)})
    except Exception:
        document.status = "failed"
        document.error_code = "INGESTION_FAILED"
        await session.commit()
        raise
    return {"id": str(document_id), "status": "processing"}


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    document = (
        await session.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == UUID(current_user.id),
            )
        )
    ).scalar_one_or_none()
    if document is None:
        raise DomainError("DOC_NOT_FOUND")
    blob_key = await delete_document_use_case(session, document_id)
    if blob_key:
        (Path(get_settings().blob_dir) / blob_key).unlink(missing_ok=True)
    session.add(
        AuditLog(
            ts=datetime.now(UTC),
            actor_id=UUID(current_user.id),
            action="document_deleted",
            target_type="document",
            target_id=str(document_id),
            outcome="ok",
        )
    )
    await record_event(
        session, "document_deleted", user_id=UUID(current_user.id), props={"trigger": "user"}
    )
    await session.commit()
    return Response(status_code=204)
