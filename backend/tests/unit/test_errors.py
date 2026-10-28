"""Kiểm thử `DomainError` và danh mục `ErrorCode` (T-007 §7)."""

import pytest

from app.core.errors import ERROR_HTTP_STATUS, FALLBACK_ERROR_CODE, DomainError


def test_domain_error_quota_exceeded_maps_to_422() -> None:
    err = DomainError("QUOTA_EXCEEDED", {"max": 50})
    assert err.http_status == 422
    assert err.to_response_body() == {"code": "QUOTA_EXCEEDED", "params": {"max": 50}}


def test_domain_error_without_params_defaults_to_empty_dict() -> None:
    err = DomainError("DOC_NOT_FOUND")
    assert err.to_response_body() == {"code": "DOC_NOT_FOUND", "params": {}}


def test_unknown_error_code_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="chưa khai báo"):
        DomainError("NOT_A_REAL_CODE")


@pytest.mark.parametrize(
    "code",
    [
        "FILE_NOT_PDF",
        "FILE_TOO_LARGE",
        "TOO_MANY_PAGES",
        "PDF_ENCRYPTED",
        "PDF_CORRUPTED",
        "PDF_NO_TEXT",
        "QUOTA_EXCEEDED",
        "DUPLICATE_NAME",
        "UPLOAD_NETWORK",
        "ANSWER_NETWORK",
        "SERVICE_BUSY",
        "ANSWER_TIMEOUT",
        "ANSWER_INTERRUPTED",
        "SESSION_EXPIRED",
        "NOT_AUTHORIZED",
        "DOC_NOT_FOUND",
        "QUESTION_INVALID",
        "NO_READY_DOCUMENTS",
        "RATE_LIMITED",
        "FILE_REJECTED",
        "INGESTION_FAILED",
    ],
)
def test_all_twenty_one_catalog_codes_are_declared(code: str) -> None:
    """Danh mục SDD §3.4.3 + bổ sung D-05 (T-007 §3) — đủ 21 mã."""
    assert code in ERROR_HTTP_STATUS


def test_catalog_has_exactly_21_codes_no_more_no_less() -> None:
    assert len(ERROR_HTTP_STATUS) == 21


def test_fallback_error_code_is_itself_a_valid_catalog_entry() -> None:
    assert FALLBACK_ERROR_CODE in ERROR_HTTP_STATUS
