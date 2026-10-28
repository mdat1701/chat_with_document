import unicodedata
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


def test_extract_and_chunk_accepts_mixed_scan_and_text_pdf(tmp_path: Path) -> None:
    """T-202 §6 'PDF hỗn hợp': dưới ngưỡng `empty_page_ratio` (mặc định
    80%) vẫn phải xử lý được, không bị từ chối như PDF_NO_TEXT — chỉ các
    trang scan đơn giản không tạo ra đoạn nào."""
    path = tmp_path / "mixed.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Nội dung có văn bản thật. " * 10)
    document.new_page()  # trang scan (rỗng)
    document.new_page()  # trang scan (rỗng)
    document.save(path)
    document.close()

    chunks = service.extract_and_chunk(path, service.ChunkConfig())

    assert chunks
    assert all(chunk.page_start == 1 and chunk.page_end == 1 for chunk in chunks)


def test_extract_and_chunk_normalizes_vietnamese_text_to_nfc(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T-403/T-202: dấu tiếng Việt phải ở dạng NFC (tổ hợp), không phải
    NFD (tách rời) — nếu không, so khớp FTS/embedding sẽ lệch. PyMuPDF với
    font mặc định không dựng đúng glyph cho văn bản NFD chèn thủ công, nên
    test này giả lập trực tiếp đầu ra `page.get_text("blocks")` ở dạng NFD
    thay vì chèn qua `insert_text` (không phản ánh đúng cách PDF thật lưu
    glyph tổ hợp)."""
    path = tmp_path / "vietnamese.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "placeholder")
    document.save(path)
    document.close()

    nfc_text = "Thời hạn thanh toán là ba mươi ngày kể từ ngày ký."
    nfd_text = unicodedata.normalize("NFD", nfc_text)
    assert nfd_text != nfc_text  # xác nhận dữ liệu test thật sự ở dạng NFD
    fake_block = (0.0, 0.0, 100.0, 100.0, nfd_text, 0, 0)

    class _FakePage:
        def get_text(self, _mode: str) -> list[tuple]:
            return [fake_block]

    class _FakePdf:
        needs_pass = False
        page_count = 1

        def __enter__(self) -> "_FakePdf":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self):
            return iter([_FakePage()])

        def __len__(self) -> int:
            return 1

    monkeypatch.setattr(service.fitz, "open", lambda _path: _FakePdf())

    chunks = service.extract_and_chunk(
        path, service.ChunkConfig(target_tokens=50, overlap_tokens=5, min_chars_per_page=1)
    )

    content = " ".join(chunk.content for chunk in chunks)
    assert content == nfc_text
    assert content == unicodedata.normalize("NFC", content)


def test_extract_and_chunk_never_exceeds_target_tokens_per_chunk(tmp_path: Path) -> None:
    path = tmp_path / "long.pdf"
    document = fitz.open()
    document.new_page().insert_text((72, 72), "từ " * 200)
    document.save(path)
    document.close()

    chunks = service.extract_and_chunk(
        path, service.ChunkConfig(target_tokens=20, overlap_tokens=2, min_chars_per_page=1)
    )

    assert chunks
    assert all(len(chunk.content.split()) <= 20 for chunk in chunks)
