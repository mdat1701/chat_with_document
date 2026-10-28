from pathlib import Path

import fitz
import pytest

from app.modules.ingestion import service


def _write_pdf(path: Path, pages: int = 1) -> None:
    document = fitz.open()
    for _ in range(pages):
        document.new_page()
    document.save(path)
    document.close()


def test_validate_pdf_accepts_regular_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "valid.pdf"
    _write_pdf(path)
    monkeypatch.setattr(service, "get_settings", lambda: type("S", (), {"max_pages": 300})())

    assert service._validate_pdf(path) == 1


def test_validate_pdf_reports_page_count_for_limit_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "too-many-pages.pdf"
    _write_pdf(path, pages=2)
    monkeypatch.setattr(service, "get_settings", lambda: type("S", (), {"max_pages": 1})())

    with pytest.raises(service.PdfValidationError) as error:
        service._validate_pdf(path)

    assert error.value.code == "TOO_MANY_PAGES"
    assert error.value.page_count == 2


def test_validate_pdf_reports_corrupt_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"%PDF-corrupt")
    monkeypatch.setattr(service, "get_settings", lambda: type("S", (), {"max_pages": 300})())

    with pytest.raises(service.PdfValidationError) as error:
        service._validate_pdf(path)

    assert error.value.code == "PDF_CORRUPTED"


def test_extract_and_chunk_preserves_page_ranges(tmp_path: Path) -> None:
    path = tmp_path / "pages.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "A " * 30)
    document.new_page().insert_text((72, 72), "B " * 30)
    document.save(path)
    document.close()

    chunks = service.extract_and_chunk(
        path,
        service.ChunkConfig(target_tokens=5, overlap_tokens=1, min_chars_per_page=1),
    )

    assert chunks
    assert all(chunk.page_start <= chunk.page_end for chunk in chunks)
    assert {chunk.page_start for chunk in chunks} == {1, 2}


def test_extract_and_chunk_rejects_scan_only_pdf(tmp_path: Path) -> None:
    path = tmp_path / "scan.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(service.PdfValidationError, match="PDF_NO_TEXT"):
        service.extract_and_chunk(path, service.ChunkConfig())
