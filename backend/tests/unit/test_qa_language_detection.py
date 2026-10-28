"""Kiểm thử `detect_language()` (T-403) — trước phiên này không có test
nào cho hàm này. Môi trường sandbox không cài được gói `lingua` (xem
"Ghi chú triển khai thực tế" T-403), nên các ca dưới đây xác nhận đúng
nhánh fallback heuristic — nhánh duy nhất thực thi được ở đây."""

from __future__ import annotations

from app.modules.qa.service import detect_language


def test_short_question_defaults_to_vietnamese_other() -> None:
    assert detect_language("abc") == ("vi", "other")


def test_vietnamese_diacritics_detected_as_vietnamese() -> None:
    lang, detected = detect_language("Thời hạn thanh toán với đối tác A là bao lâu?")
    assert lang == "vi"
    assert detected == "vi"


def test_english_common_words_detected_as_english() -> None:
    lang, detected = detect_language("What is the payment term for partner A in the contract?")
    assert lang == "en"
    assert detected == "en"


def test_mixed_language_question_does_not_crash() -> None:
    lang, _detected = detect_language("Payment term của đối tác A là gì?")
    assert lang in {"vi", "en"}
