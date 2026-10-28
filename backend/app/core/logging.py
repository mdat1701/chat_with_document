"""Logging JSON có cấu trúc + bộ lọc nội dung (T-007, nguyên tắc P-03).

Nguyên tắc: "nội dung là dữ liệu nhạy cảm" — văn bản tài liệu, câu hỏi
và câu trả lời KHÔNG BAO GIỜ xuất hiện trong log, trace, metric hay
analytics. `scrub()` chạy trong pipeline logger (không phải ở từng lời
gọi riêng lẻ) để không ai quên gọi nó (T-007 §5 bước 2).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import sys
import time
from typing import Any

# Trường chuẩn của mọi bản ghi log (SADD §4.3) — không thêm trường tự
# do ngoài danh sách này khi log có cấu trúc.
STANDARD_FIELDS = frozenset(
    {
        "ts",
        "level",
        "service",
        "trace_id",
        "span_id",
        "user_hash",
        "route",
        "status",
        "latency_ms",
        "error_code",
    }
)

# Chặn ở MỌI cấp lồng nhau, bất kể bản ghi log hay payload nghiệp vụ nào
# truyền qua logger (T-007 §2).
BLOCKED_FIELDS = frozenset({"question", "answer", "content", "text", "file_name", "prompt"})

_IS_DEV = os.environ.get("APP_ENV", "dev") != "production"
_scrub_warning_logger = logging.getLogger("app.core.logging.scrub")


def scrub(payload: Any, *, _path: str = "") -> Any:
    """Loại bỏ `BLOCKED_FIELDS` khỏi `payload`, đệ quy qua dict/list lồng
    nhau. Ở dev: ghi WARNING nêu rõ tên trường + vị trí. Ở production:
    loại im lặng (không làm hỏng request)."""
    if isinstance(payload, dict):
        cleaned: dict[str, Any] = {}
        for key, value in payload.items():
            path = f"{_path}.{key}" if _path else str(key)
            if key in BLOCKED_FIELDS:
                if _IS_DEV:
                    _scrub_warning_logger.warning(
                        "scrub() đã loại trường nhạy cảm '%s' tại '%s' — "
                        "kiểm tra lại nơi gọi logger, không log nội dung (P-03)",
                        key,
                        path,
                    )
                continue
            cleaned[key] = scrub(value, _path=path)
        return cleaned
    if isinstance(payload, list):
        return [scrub(item, _path=_path) for item in payload]
    return payload


def hash_user_id(user_id: str, *, secret_key: bytes) -> str:
    """`user_hash` = HMAC-SHA256(user_id, secret_key) — KHÔNG log
    `user_id` thô hay email (T-007 §5 bước 4)."""
    return hmac.new(secret_key, user_id.encode("utf-8"), hashlib.sha256).hexdigest()


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.time(),
            "level": record.levelname,
            "service": getattr(record, "service", "backend"),
            "message": record.getMessage(),
        }
        optional_fields = (
            "trace_id",
            "span_id",
            "user_hash",
            "route",
            "status",
            "latency_ms",
            "error_code",
        )
        for field in optional_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        extra_props = getattr(record, "props", None)
        if extra_props:
            payload["props"] = scrub(extra_props)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: int = logging.INFO) -> None:
    """Gọi một lần khi khởi động `api`/`worker` (T-008/T-006)."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
