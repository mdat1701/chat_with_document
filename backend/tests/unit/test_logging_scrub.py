"""Kiểm thử bộ lọc nội dung `scrub()` (T-007 §7) — bằng chứng cho
Pilot Gate G-04. Đây là test quan trọng nhất của task: chứng minh 6
trường nhạy cảm KHÔNG BAO GIỜ lọt ra log, kể cả lồng sâu nhiều cấp.
"""

import json
import logging

import pytest

from app.core.logging import BLOCKED_FIELDS, _JsonFormatter, hash_user_id, scrub


def test_all_six_blocked_fields_are_removed_at_top_level() -> None:
    payload = {
        "question": "Thời hạn thanh toán là bao lâu?",
        "answer": "30 ngày",
        "content": "nội dung tài liệu",
        "text": "văn bản",
        "file_name": "HopDong.pdf",
        "prompt": "system prompt",
        "latency_ms": 120,  # trường hợp lệ phải được giữ lại
    }
    cleaned = scrub(payload)
    assert set(cleaned) == {"latency_ms"}
    for field in BLOCKED_FIELDS:
        assert field not in cleaned


def test_blocked_field_removed_at_three_levels_of_nesting() -> None:
    payload = {"a": {"b": {"content": "bí mật", "ok": 1}}}
    cleaned = scrub(payload)
    assert "content" not in cleaned["a"]["b"]
    assert cleaned["a"]["b"]["ok"] == 1


def test_blocked_field_removed_inside_list_of_dicts() -> None:
    payload = {"items": [{"text": "x"}, {"keep": "y"}]}
    cleaned = scrub(payload)
    assert cleaned["items"] == [{}, {"keep": "y"}]


def test_dev_mode_logs_warning_naming_the_blocked_field(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.core.logging.scrub"):
        scrub({"nested": {"prompt": "x"}})
    assert any("prompt" in record.message for record in caplog.records)
    assert any("nested.prompt" in record.message for record in caplog.records)


def test_hash_user_id_is_deterministic_and_does_not_leak_raw_id() -> None:
    h1 = hash_user_id("user-123", secret_key=b"secret")
    h2 = hash_user_id("user-123", secret_key=b"secret")
    assert h1 == h2
    assert "user-123" not in h1
    assert len(h1) == 64  # hex SHA-256


def test_hash_user_id_differs_with_different_secret() -> None:
    h1 = hash_user_id("user-123", secret_key=b"secret-a")
    h2 = hash_user_id("user-123", secret_key=b"secret-b")
    assert h1 != h2


def test_json_formatter_output_never_contains_blocked_field_values() -> None:
    formatter = _JsonFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="answer_rendered",
        args=(),
        exc_info=None,
    )
    record.props = {"question": "câu hỏi bí mật", "latency_ms": 100}
    output = json.loads(formatter.format(record))
    assert "câu hỏi bí mật" not in json.dumps(output)
    assert output["props"] == {"latency_ms": 100}


def test_json_formatter_includes_traceback_when_logger_exception_is_used() -> None:
    """Lỗi thật phát hiện khi chạy TC-013 thủ công: `logger.exception(...)`
    ghi đúng một dòng log nhưng KHÔNG CÓ traceback nào — `_JsonFormatter`
    trước đây bỏ qua hoàn toàn `record.exc_info`, khiến mọi lỗi không
    lường trước trong toàn backend không thể chẩn đoán được từ log."""
    import sys

    formatter = _JsonFormatter()
    logger = logging.getLogger("test-exc-trace")
    try:
        raise ValueError("boom")
    except ValueError:
        record = logger.makeRecord(
            logger.name, logging.ERROR, __file__, 1, "đã xảy ra lỗi", (), sys.exc_info()
        )
    output = json.loads(formatter.format(record))
    assert "error_trace" in output
    assert "ValueError: boom" in output["error_trace"]
