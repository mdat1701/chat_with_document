"""Kiểm thử validate cấu hình khi khởi động (T-105 §5 bước 1) — trước
phiên này không có test nào xác nhận cấu hình sai thực sự chặn khởi
động thay vì chạy với giá trị vô nghĩa."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_zero_max_pages_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(max_pages=0)


def test_negative_max_documents_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(max_documents=-1)


def test_zero_max_file_size_bytes_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(max_file_size_bytes=0)


def test_valid_settings_construct_without_error() -> None:
    settings = Settings(max_pages=300, max_documents=50, max_file_size_bytes=20_971_520)
    assert settings.max_pages == 300
