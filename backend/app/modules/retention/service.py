"""Tác vụ retention và xử lý job ingestion bị treo."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import worker_session_scope
from app.modules.documents.models import Document
from app.modules.documents.service import delete_document_use_case


@dataclass(frozen=True)
class DeletedDocument:
    owner_id: UUID
    document_id: UUID


async def _purge_expired(batch_size: int) -> list[DeletedDocument]:
    """Trả về `owner_id`/`document_id` của từng tài liệu đã xóa — để lớp
    gọi (`app.workers`, được phép import `app.modules.analytics`, khác
    `app.modules.retention` theo ranh giới độc lập module SADD §2.2.1)
    phát sự kiện `document_deleted{trigger=retention}` và ghi `audit_log`
    (T-404, T-206 §5 bước 8)."""
    removed: list[DeletedDocument] = []
    async with worker_session_scope() as session:
        documents = (
            await session.execute(
                select(Document)
                .where(
                    Document.expires_at < datetime.now(UTC),
                    Document.status != "deleting",
                )
                .with_for_update(skip_locked=True)
                .limit(batch_size)
            )
        ).scalars().all()
        for document in documents:
            owner_id, document_id = document.owner_id, document.id
            blob_key = await delete_document_use_case(session, document_id)
            if blob_key:
                (Path(get_settings().blob_dir) / blob_key).unlink(missing_ok=True)
            removed.append(DeletedDocument(owner_id=owner_id, document_id=document_id))
    return removed


def purge_expired_use_case(batch_size: int = 100) -> list[DeletedDocument]:
    """Điểm vào mà `app.workers.retention_tasks.purge_expired` gọi
    (T-006). Trả về `owner_id`/`document_id` của từng tài liệu đã xóa."""
    return asyncio.run(_purge_expired(batch_size))


def reap_stuck_ingestion_use_case(stuck_after_minutes: int = 10) -> int:
    """Điểm vào mà `app.workers.ingestion_tasks.reap_stuck` gọi
    (T-006). Trả về số job bị chuyển sang `failed`. Logic thật ở T-207."""
    return asyncio.run(_reap_stuck(stuck_after_minutes))


async def _reap_stuck(stuck_after_minutes: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(minutes=stuck_after_minutes)
    async with worker_session_scope() as session:
        documents = (
            await session.execute(
                select(Document).where(
                    Document.status == "processing",
                    Document.uploaded_at < cutoff,
                )
            )
        ).scalars().all()
        for document in documents:
            document.status = "failed"
            document.error_code = "INGESTION_FAILED"
        await session.commit()
        return len(documents)
