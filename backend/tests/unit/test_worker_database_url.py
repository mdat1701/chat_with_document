"""`Settings.worker_database_url_or_default()` (T-006 §5 bước 5).

Lỗi thật phát hiện khi chạy ingestion trên Postgres thật với
`DATABASE_URL` khác đúng chuỗi mặc định của `.env.example`: bản cũ dùng
`str.replace("cwd:cwd_local_only@", ...)`, âm thầm trả nguyên
`database_url` (vai trò API, không có BYPASSRLS) nếu không khớp hệt —
worker lỗi "unrecognized configuration parameter app.user_id" thay vì
dùng đúng vai trò `cwd_worker`."""

from __future__ import annotations

from app.core.config import Settings


def test_default_env_example_url_derives_cwd_worker_credentials() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://cwd:cwd_local_only@localhost:5432/cwd"
    )
    url = settings.worker_database_url_or_default()
    assert "cwd_worker:cwd_worker_local_only@" in url
    assert url.endswith("localhost:5432/cwd")


def test_non_default_database_url_still_derives_cwd_worker_credentials() -> None:
    """Trước đây lỗi: role khác 'cwd' (ví dụ 'cwd_app', đúng vai trò thật
    do migration tạo ra) khiến .replace() không khớp, trả nguyên URL cũ."""
    settings = Settings(
        database_url="postgresql+asyncpg://cwd_app:some_password@db.internal:5432/cwd"
    )
    url = settings.worker_database_url_or_default()
    assert "cwd_worker:cwd_worker_local_only@" in url
    assert "cwd_app" not in url
    assert url.endswith("db.internal:5432/cwd")


def test_explicit_worker_database_url_overrides_derivation() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://cwd:x@localhost:5432/cwd",
        worker_database_url="postgresql+asyncpg://custom_worker:y@other-host:5432/cwd",
    )
    assert settings.worker_database_url_or_default() == (
        "postgresql+asyncpg://custom_worker:y@other-host:5432/cwd"
    )
