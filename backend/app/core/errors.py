"""Ánh xạ lỗi miền → `ErrorCode` (T-007, SDD §3.4.3 + bổ sung SADD).

Quy ước phản hồi lỗi chung (SADD §2.4.2): `{"code": "<ErrorCode>",
"params": {...}}`. API KHÔNG trả nguyên văn thông báo nội bộ/stack
trace ra client — chỉ `code` (+ `params` không nhạy cảm).
"""

from __future__ import annotations

from typing import Any

# Danh mục đầy đủ (SDD §3.4.3). FILE_REJECTED và INGESTION_FAILED là đề
# xuất bổ sung của SADD, cần cập nhật lại SDD §3.4.3 (D-05).
ERROR_HTTP_STATUS: dict[str, int] = {
    "FILE_NOT_PDF": 415,
    "FILE_TOO_LARGE": 413,
    "TOO_MANY_PAGES": 422,
    "PDF_ENCRYPTED": 422,
    "PDF_CORRUPTED": 422,
    "PDF_NO_TEXT": 422,
    "QUOTA_EXCEEDED": 422,
    "DUPLICATE_NAME": 409,
    "UPLOAD_NETWORK": 502,
    "ANSWER_NETWORK": 502,
    "SERVICE_BUSY": 503,
    "ANSWER_TIMEOUT": 504,
    "ANSWER_INTERRUPTED": 502,
    "SESSION_EXPIRED": 401,
    "NOT_AUTHORIZED": 403,
    "DOC_NOT_FOUND": 404,
    "QUESTION_INVALID": 400,
    "NO_READY_DOCUMENTS": 409,
    "RATE_LIMITED": 429,
    # Bổ sung SADD (D-05 — chưa có trong SDD §3.4.3):
    "FILE_REJECTED": 422,
    "INGESTION_FAILED": 500,
}


class DomainError(Exception):
    """Lỗi nghiệp vụ từ `modules/*`. API (T-008) bắt lớp này ở exception
    handler toàn cục và trả đúng `{code, params}` — không bao giờ lộ
    `str(exc)` thô cho lỗi từ thư viện xử lý PDF/LLM (T-007 §6)."""

    def __init__(self, code: str, params: dict[str, Any] | None = None) -> None:
        if code not in ERROR_HTTP_STATUS:
            raise ValueError(f"ErrorCode chưa khai báo trong ERROR_HTTP_STATUS: {code!r}")
        self.code = code
        self.http_status = ERROR_HTTP_STATUS[code]
        self.params = params or {}
        super().__init__(code)

    def to_response_body(self) -> dict[str, Any]:
        return {"code": self.code, "params": self.params}


# Lỗi không ánh xạ được (bug, thư viện ngoài tầm kiểm soát) -> trả về
# mã chung, không rò rỉ chi tiết (T-007 §6 "Lỗi chưa được ánh xạ").
FALLBACK_ERROR_CODE = "SERVICE_BUSY"
