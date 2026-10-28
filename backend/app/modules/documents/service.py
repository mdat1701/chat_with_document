"""Vòng đời tài liệu và dùng chung thao tác xóa cho API/retention."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import worker_session_scope
from app.modules.documents.models import Chunk, Document


async def delete_document_use_case(
    session: AsyncSession, document_id: UUID
) -> str | None:
    document = (
        await session.execute(
            select(Document).where(Document.id == document_id).with_for_update()
        )
    ).scalar_one_or_none()
    if document is None:
        return None
    blob_key = document.blob_key
    await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await session.delete(document)
    await session.commit()
    return blob_key


async def _reconcile_orphan_blobs(older_than_hours: int) -> int:
    settings = get_settings()
    root = Path(settings.blob_dir)
    if not root.exists():
        return 0
    cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)
    async with worker_session_scope() as session:
        known = set(
            (
                await session.execute(select(Document.blob_key))
            ).scalars().all()
        )
    removed = 0
    for path in root.glob("owner/*/*.pdf"):
        if not path.is_file() or path.stat().st_mtime > cutoff.timestamp():
            continue
        key = path.relative_to(root).as_posix()
        if key not in known:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def reconcile_orphan_blobs_use_case(older_than_hours: int = 24) -> int:
    return asyncio.run(_reconcile_orphan_blobs(older_than_hours))
