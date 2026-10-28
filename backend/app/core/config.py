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
    redis_url: str = "redis://localhost:6379/0"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
