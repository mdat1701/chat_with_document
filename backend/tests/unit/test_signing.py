"""Kiểm thử ký/xác minh payload HMAC (T-101 cookie giao dịch `cwd_oidc_tx`)."""

import time
from unittest.mock import patch

import pytest

from app.core.signing import BadSignature, sign, unsign

SECRET = b"test-secret-key"


def test_sign_then_unsign_round_trips() -> None:
    token = sign({"state": "abc", "nonce": "xyz"}, secret_key=SECRET)
    payload = unsign(token, secret_key=SECRET, max_age_seconds=300)
    assert payload == {"state": "abc", "nonce": "xyz"}


def test_unsign_rejects_wrong_secret() -> None:
    token = sign({"a": 1}, secret_key=SECRET)
    with pytest.raises(BadSignature, match="không khớp"):
        unsign(token, secret_key=b"khoa-khac", max_age_seconds=300)


def test_unsign_rejects_tampered_payload() -> None:
    token = sign({"a": 1}, secret_key=SECRET)
    body_b64, sig_b64 = token.split(".", 1)
    tampered = body_b64 + "x." + sig_b64  # đổi payload nhưng giữ chữ ký cũ
    with pytest.raises(BadSignature):
        unsign(tampered, secret_key=SECRET, max_age_seconds=300)


def test_unsign_rejects_malformed_token() -> None:
    with pytest.raises(BadSignature, match="Định dạng"):
        unsign("khong-co-dau-cham", secret_key=SECRET, max_age_seconds=300)


def test_unsign_rejects_expired_token() -> None:
    token = sign({"a": 1}, secret_key=SECRET)
    future = time.time() + 301
    with patch("app.core.signing.time.time", return_value=future):
        with pytest.raises(BadSignature, match="hết hạn"):
            unsign(token, secret_key=SECRET, max_age_seconds=300)


def test_unsign_accepts_token_just_before_expiry() -> None:
    token = sign({"a": 1}, secret_key=SECRET)
    almost_expired = time.time() + 299
    with patch("app.core.signing.time.time", return_value=almost_expired):
        unsign(token, secret_key=SECRET, max_age_seconds=300)  # không raise
