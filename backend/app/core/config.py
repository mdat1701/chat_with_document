"""Cấu hình ứng dụng — đọc từ biến môi trường (`.env`), không hard-code
giá trị DF-01 – DF-10 trong code (nguyên tắc P-06, SADD §1.2).

Mở rộng đầy đủ ở T-105 (`GET /config` expose các giá trị DF-* cho
client). Task T-005 chỉ cần `database_url` để Alembic kết nối CSDL.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://cwd:cwd_local_only@localhost:5432/cwd"
    # Vai trò CSDL riêng cho worker (BYPASSRLS — T-005); mặc định đoán từ
    # database_url nếu không khai báo (xem Settings.worker_database_url_or_default).
    worker_database_url: str | None = None

    redis_url: str = "redis://localhost:6379/0"
    # DB Redis riêng cho broker Celery, tách khỏi phiên/rate limit (SADD §2.3)
    # để maxmemory-policy khác nhau giữa hai mục đích dùng.
    celery_broker_url: str = "redis://localhost:6379/1"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "cwd_minio"
    s3_secret_key: str = "cwd_minio_local_only"
    s3_bucket: str = "cwd-documents"

    clamav_host: str = "localhost"
    clamav_port: int = 3310

    tei_embed_url: str = "http://localhost:8080"

    # Giá trị mặc định DF-01 – DF-10 (PRD §0.3). Expose qua GET /config ở T-105.
    max_file_size_bytes: int = 20_971_520
    max_documents: int = 50
    max_pages: int = 300
    retention_days: int = 90
    max_question_length: int = 2000
    answer_timeout_ms: int = 60_000

    oidc_issuer: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""

    llm_provider: str = "fake"

    # "local" | "staging" | "production". Stub auth (T-008 deps.py) chỉ
    # chạy khi "local" — mặc định "local" để không chặn dev/test.
    app_env: str = "local"
    service_name: str = "cwd-backend"
    # Để trống ở local -> exporter no-op (T-007 §6 "OTel Collector không
    # chạy ở local"); đặt URL OTLP/HTTP thật ở staging/prod.
    otel_exporter_endpoint: str = ""
    # Khóa HMAC cho user_hash (T-007 §5 bước 4) — PHẢI đổi ở staging/prod,
    # giá trị dưới đây chỉ dùng cho local/test.
    analytics_hash_secret: str = "local-dev-only-change-me"

    def worker_database_url_or_default(self) -> str:
        """`worker_database_url` nếu khai báo, ngược lại đổi user/password
        `cwd` -> `cwd_worker` trong `database_url` (T-006 §5 bước 5)."""
        if self.worker_database_url:
            return self.worker_database_url
        return self.database_url.replace("cwd:cwd_local_only@", "cwd_worker:cwd_worker_local_only@")


@lru_cache
def get_settings() -> Settings:
    return Settings()
