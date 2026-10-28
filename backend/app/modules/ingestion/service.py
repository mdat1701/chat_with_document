"""Bước quét an toàn và kiểm tra cấu trúc của pipeline ingestion (T-201)."""

from __future__ import annotations

import asyncio
import re
import socket
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Final
from uuid import UUID

import fitz
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.db import worker_session_scope
from app.core.metrics import documents_failed_total
from app.core.redis_client import get_redis
from app.modules.documents.models import Chunk, Document
from app.ports.embedding_port import EmbeddingPort

_CHUNK_SIZE: Final = 1024 * 1024


class InfrastructureError(RuntimeError):
    """Lỗi hạ tầng có thể retry bởi Celery."""


class UnsafeFileError(RuntimeError):
    """Tệp bị ClamAV từ chối, không retry."""


class PdfValidationError(ValueError):
    def __init__(self, code: str, page_count: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.page_count = page_count


@dataclass(frozen=True)
class ChunkConfig:
    target_tokens: int = 500
    overlap_tokens: int = 50
    min_chars_per_page: int = 20
    empty_page_ratio: float = 0.8


@dataclass(frozen=True)
class ExtractedChunk:
    ordinal: int
    page_start: int
    page_end: int
    heading_path: str | None
    content: str


def extract_and_chunk(pdf_path: str | Path, cfg: ChunkConfig) -> list[ExtractedChunk]:
    """Extract ordered page text and split it while preserving page bounds."""
    if cfg.target_tokens <= 0 or cfg.overlap_tokens < 0:
        raise ValueError("Invalid chunk configuration")
    if cfg.overlap_tokens >= cfg.target_tokens:
        raise ValueError("overlap_tokens must be smaller than target_tokens")

    page_words: list[tuple[str, int]] = []
    empty_pages = 0
    try:
        with fitz.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf, start=1):
                blocks = page.get_text("blocks")
                blocks.sort(key=lambda block: (block[1], block[0]))
                text = "\n".join(str(block[4]) for block in blocks)
                normalized = unicodedata.normalize("NFC", text)
                normalized = normalized.replace("\u00ad", "")
                if len(normalized.strip()) < cfg.min_chars_per_page:
                    empty_pages += 1
                page_words.extend((word, page_number) for word in re.findall(r"\S+", normalized))
            page_count = len(pdf)
    except Exception as exc:
        raise PdfValidationError("PDF_CORRUPTED") from exc

    if page_count and empty_pages / page_count >= cfg.empty_page_ratio:
        raise PdfValidationError("PDF_NO_TEXT", page_count)
    if not page_words:
        raise PdfValidationError("PDF_NO_TEXT", page_count)

    chunks: list[ExtractedChunk] = []
    step = cfg.target_tokens - cfg.overlap_tokens
    for start in range(0, len(page_words), step):
        selected = page_words[start : start + cfg.target_tokens]
        if not selected:
            break
        content = " ".join(word for word, _ in selected).strip()
        if content:
            chunks.append(
                ExtractedChunk(
                    ordinal=len(chunks),
                    page_start=selected[0][1],
                    page_end=selected[-1][1],
                    heading_path=None,
                    content=content,
                )
            )
        if start + cfg.target_tokens >= len(page_words):
            break
    return chunks


async def _scan_with_clamav(path: Path) -> None:
    settings = get_settings()
    try:
        with socket.create_connection(
            (settings.clamav_host, settings.clamav_port), timeout=60
        ) as connection:
            connection.sendall(b"zINSTREAM\0")
            with path.open("rb") as source:
                while chunk := source.read(_CHUNK_SIZE):
                    connection.sendall(len(chunk).to_bytes(4, "big") + chunk)
            connection.sendall(b"\0\0\0\0")
            response = connection.recv(4096).decode("utf-8", errors="replace")
    except (OSError, TimeoutError) as exc:
        raise InfrastructureError("ClamAV unavailable") from exc
    if "FOUND" in response:
        raise UnsafeFileError("malware detected")
    if "OK" not in response:
        raise InfrastructureError("ClamAV returned an invalid response")


def _validate_pdf(path: Path) -> int:
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass:
                raise PdfValidationError("PDF_ENCRYPTED")
            page_count = pdf.page_count
    except PdfValidationError:
        raise
    except Exception as exc:
        raise PdfValidationError("PDF_CORRUPTED") from exc
    if page_count > get_settings().max_pages:
        raise PdfValidationError("TOO_MANY_PAGES", page_count)
    return int(page_count)


async def _set_failed(document_id: UUID, error_code: str, page_count: int | None = None) -> None:
    async with worker_session_scope() as session:
        document = (
            await session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None or document.status in {"failed", "ready", "deleting"}:
            return
        document.status = "failed"
        document.error_code = error_code
        if page_count is not None:
            document.page_count = page_count
        await session.commit()
    documents_failed_total.labels(error_code=error_code).inc()
    await _publish_status(document_id, "failed", error_code, page_count)


async def _publish_status(
    document_id: UUID, status: str, error_code: str | None, page_count: int | None
) -> None:
    async with worker_session_scope() as session:
        document = (
            await session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None:
            return
        payload = {
            "id": str(document_id),
            "status": status,
            "error_code": error_code,
            "page_count": page_count,
        }
        import json

        await get_redis().publish(f"doc-status:{document.owner_id}", json.dumps(payload))


async def _index_document(
    document_id: UUID, chunks: list[ExtractedChunk], embedder: EmbeddingPort
) -> None:
    if not chunks:
        await _set_failed(document_id, "PDF_NO_TEXT")
        return
    vectors: list[list[float]] = []
    for offset in range(0, len(chunks), 32):
        batch = [chunk.content for chunk in chunks[offset : offset + 32]]
        vectors.extend(embedder.embed_batch(batch))
    if len(vectors) != len(chunks):
        raise InfrastructureError("Embedding count mismatch")
    async with worker_session_scope() as session:
        document = (
            await session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None or document.status != "processing":
            return
        await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        session.add_all(
            [
                Chunk(
                    document_id=document_id,
                    owner_id=document.owner_id,
                    ordinal=chunk.ordinal,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    heading_path=chunk.heading_path,
                    content=chunk.content,
                    embedding=vector,
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
        )
        document.status = "ready"
        document.ready_at = datetime.now(UTC)
        await session.commit()
        await _publish_status(document_id, "ready", None, document.page_count)


async def _process_document(document_id: UUID, embedder: EmbeddingPort | None = None) -> None:
    async with worker_session_scope() as session:
        document = (
            await session.execute(select(Document).where(Document.id == document_id))
        ).scalar_one_or_none()
        if document is None or document.status in {"failed", "ready", "deleting"}:
            return
        blob_path = Path(get_settings().blob_dir) / document.blob_key

    if not blob_path.is_file():
        await _set_failed(document_id, "INGESTION_FAILED")
        return

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(suffix=".pdf", delete=False) as temporary:
            temp_path = Path(temporary.name)
            with blob_path.open("rb") as source:
                while chunk := source.read(_CHUNK_SIZE):
                    temporary.write(chunk)
        try:
            await _scan_with_clamav(temp_path)
        except UnsafeFileError:
            blob_path.unlink(missing_ok=True)
            await _set_failed(document_id, "FILE_REJECTED")
            return
        try:
            page_count = _validate_pdf(temp_path)
        except PdfValidationError as exc:
            await _set_failed(document_id, exc.code, exc.page_count)
            return
        chunk_cfg = ChunkConfig(
            target_tokens=get_settings().chunk_size_tokens,
            overlap_tokens=get_settings().chunk_overlap_tokens,
        )
        try:
            chunks = extract_and_chunk(temp_path, chunk_cfg)
        except PdfValidationError as exc:
            await _set_failed(document_id, exc.code, exc.page_count)
            return
        async with worker_session_scope() as session:
            document = (
                await session.execute(select(Document).where(Document.id == document_id))
            ).scalar_one_or_none()
            if document is not None and document.status == "processing":
                document.page_count = page_count
                await session.commit()
        if embedder is not None:
            try:
                await _index_document(document_id, chunks, embedder)
            except RuntimeError as exc:
                raise InfrastructureError("Embedding failed") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def process_document_use_case(document_id: str, embedder: EmbeddingPort | None = None) -> None:
    """Điểm vào đồng bộ cho Celery; worker vẫn dùng worker DB role."""
    asyncio.run(_process_document(UUID(document_id), embedder))
