"""Ký và xác minh payload ngắn hạn bằng HMAC-SHA256 (T-101 §5 bước 3-4).

Dùng cho cookie giao dịch OIDC `cwd_oidc_tx` — không thêm phụ thuộc
ngoài (`itsdangerous`) vì chỉ cần một primitive đơn giản, dùng lại
`hmac`/`hashlib` đã có sẵn trong `app.core.logging`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


class BadSignature(Exception):
    """Chữ ký không hợp lệ hoặc payload đã hết hạn."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def sign(payload: dict[str, Any], *, secret_key: bytes) -> str:
    """Trả về chuỗi `<base64(payload+ts)>.<base64(hmac)>`."""
    body = {"data": payload, "ts": time.time()}
    body_bytes = json.dumps(body, separators=(",", ":")).encode("utf-8")
    body_b64 = _b64url_encode(body_bytes)
    signature = hmac.new(secret_key, body_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{body_b64}.{_b64url_encode(signature)}"


def unsign(token: str, *, secret_key: bytes, max_age_seconds: float) -> dict[str, Any]:
    """Xác minh chữ ký và hạn dùng, trả về `payload` gốc. Ném
    `BadSignature` nếu chữ ký sai, payload hỏng, hoặc đã hết hạn."""
    try:
        body_b64, sig_b64 = token.split(".", 1)
    except ValueError as exc:
        raise BadSignature("Định dạng token không hợp lệ") from exc

    expected_sig = hmac.new(secret_key, body_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception as exc:  # noqa: BLE001
        raise BadSignature("Không giải mã được chữ ký") from exc

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise BadSignature("Chữ ký không khớp")

    try:
        body = json.loads(_b64url_decode(body_b64))
    except Exception as exc:  # noqa: BLE001
        raise BadSignature("Không giải mã được payload") from exc

    age = time.time() - body["ts"]
    if age > max_age_seconds:
        raise BadSignature(f"Token đã hết hạn ({age:.0f}s > {max_age_seconds:.0f}s)")

    result: dict[str, Any] = body["data"]
    return result
