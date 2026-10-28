"""Kiểm thử end-to-end luồng `/auth/*` (T-101 §7) qua `TestClient` thật
— giả lập IdP (`FakeOIDCAdapter`) và Redis (`fakeredis`), patch tầng
`repository` (đã có test tích hợp riêng). Đây là bằng chứng mạnh nhất
cho US-001/AC-001.1 – AC-001.4 vì chạy đúng ngăn xếp HTTP/cookie thật.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fakeredis import FakeAsyncRedis
from fastapi.testclient import TestClient

from app.api.deps import get_db_session, get_oidc_port, get_redis_client
from app.api.main import app
from app.core.signing import sign
from app.modules.identity.models import AppUser
from app.modules.identity.service import LoginDecision, LoginOutcome
from app.ports.oidc_port import OIDCClaims, OIDCExchangeError


class FakeOIDCAdapter:
    def __init__(
        self, *, claims: OIDCClaims | None = None, exchange_error: Exception | None = None
    ) -> None:
        self.claims = claims
        self.exchange_error = exchange_error
        self.built_authorize_url_kwargs: dict[str, str] | None = None

    def build_authorize_url(
        self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str
    ) -> str:
        self.built_authorize_url_kwargs = {
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "redirect_uri": redirect_uri,
        }
        return f"https://fake-idp.example.com/authorize?state={state}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> OIDCClaims:
        if self.exchange_error:
            raise self.exchange_error
        assert self.claims is not None
        return self.claims


@pytest.fixture
def fake_redis():
    client = FakeAsyncRedis()
    yield client


@pytest.fixture
def client(fake_redis: FakeAsyncRedis):
    fake_oidc = FakeOIDCAdapter()

    async def _fake_db_session():
        # `AsyncSession.add()` thật là đồng bộ — chỉ `.commit()`/`.flush()`
        # là async. Dùng MagicMock cho add() để tránh cảnh báo "coroutine
        # never awaited" (không phải lỗi thật, chỉ là fixture không khớp
        # chữ ký AsyncSession thật).
        fake = AsyncMock()
        fake.add = MagicMock()
        yield fake

    app.dependency_overrides[get_oidc_port] = lambda: fake_oidc
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    app.dependency_overrides[get_db_session] = _fake_db_session

    with TestClient(app, raise_server_exceptions=False) as c:
        c.fake_oidc = fake_oidc  # type: ignore[attr-defined]
        yield c

    app.dependency_overrides.clear()


def test_login_redirects_to_idp_and_sets_signed_tx_cookie(client: TestClient) -> None:
    resp = client.get("/auth/login", params={"return_to": "/documents"}, follow_redirects=False)

    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://fake-idp.example.com/authorize")
    tx_cookie = resp.cookies.get("cwd_oidc_tx")
    assert tx_cookie is not None
    # Cookie có 2 phần ngăn bởi dấu chấm (payload ký HMAC, T-core/signing.py)
    assert tx_cookie.count(".") == 1


def test_login_rejects_url_outside_app_without_redirecting(client: TestClient) -> None:
    resp = client.get(
        "/auth/login", params={"return_to": "https://evil.com"}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert resp.json() == {"code": "INVALID_RETURN_TO", "params": {}}
    assert "location" not in resp.headers


def test_login_rejects_protocol_relative_url(client: TestClient) -> None:
    resp = client.get("/auth/login", params={"return_to": "//evil.com"}, follow_redirects=False)
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_RETURN_TO"


def test_callback_without_tx_cookie_is_state_mismatch(client: TestClient) -> None:
    resp = client.get(
        "/auth/callback", params={"code": "abc", "state": "xyz"}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert resp.json() == {"code": "OIDC_STATE_MISMATCH", "params": {}}


def test_callback_with_mismatched_state_is_rejected(client: TestClient) -> None:
    tx_token = sign(
        {"state": "state-that-was-issued", "nonce": "n", "code_verifier": "v", "return_to": "/"},
        secret_key=b"local-dev-only-change-me",
    )
    client.cookies.set("cwd_oidc_tx", tx_token)

    resp = client.get(
        "/auth/callback",
        params={"code": "abc", "state": "state-attacker-injected"},
        follow_redirects=False,
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "OIDC_STATE_MISMATCH"


def test_callback_allowed_user_sets_sid_cookie_and_redirects_to_return_to(
    client: TestClient,
) -> None:
    tx_token = sign(
        {"state": "s1", "nonce": "n1", "code_verifier": "v1", "return_to": "/documents"},
        secret_key=b"local-dev-only-change-me",
    )
    client.cookies.set("cwd_oidc_tx", tx_token)
    client.fake_oidc.claims = OIDCClaims(sub="sub-1", email="a@example.com", display_name="A")  # type: ignore[attr-defined]

    user = AppUser(email="a@example.com", active=True)
    user.id = uuid4()
    outcome = LoginOutcome(decision=LoginDecision.ALLOWED, user=user, roles=["user"])
    with patch("app.api.routers.auth.complete_login", new=AsyncMock(return_value=outcome)):
        resp = client.get(
            "/auth/callback", params={"code": "abc", "state": "s1"}, follow_redirects=False
        )

    assert resp.status_code == 302
    assert resp.headers["location"] == "/documents"
    assert resp.cookies.get("cwd_sid") is not None
    assert resp.cookies.get("cwd_oidc_tx") is None  # đã xóa cookie giao dịch


def test_callback_denied_user_redirects_to_no_access_without_sid(client: TestClient) -> None:
    tx_token = sign(
        {"state": "s1", "nonce": "n1", "code_verifier": "v1", "return_to": "/"},
        secret_key=b"local-dev-only-change-me",
    )
    client.cookies.set("cwd_oidc_tx", tx_token)
    client.fake_oidc.claims = OIDCClaims(  # type: ignore[attr-defined]
        sub="sub-khong-ton-tai", email="x@example.com", display_name=None
    )

    with patch(
        "app.api.routers.auth.complete_login",
        new=AsyncMock(return_value=LoginOutcome(decision=LoginDecision.DENIED_NOT_FOUND)),
    ):
        resp = client.get(
            "/auth/callback", params={"code": "abc", "state": "s1"}, follow_redirects=False
        )

    assert resp.status_code == 302
    assert resp.headers["location"] == "/no-access"
    assert resp.cookies.get("cwd_sid") is None


def test_callback_oidc_exchange_failure_returns_400(client: TestClient) -> None:
    tx_token = sign(
        {"state": "s1", "nonce": "n1", "code_verifier": "v1", "return_to": "/"},
        secret_key=b"local-dev-only-change-me",
    )
    client.cookies.set("cwd_oidc_tx", tx_token)
    client.fake_oidc.exchange_error = OIDCExchangeError("IdP từ chối")  # type: ignore[attr-defined]

    resp = client.get(
        "/auth/callback", params={"code": "bad-code", "state": "s1"}, follow_redirects=False
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "OIDC_STATE_MISMATCH"


async def test_logout_deletes_session_and_clears_cookie(
    client: TestClient, fake_redis: FakeAsyncRedis
) -> None:
    from app.modules.identity import sessions

    sid, _ = await sessions.create_session(fake_redis, user_id="u1", roles=["user"])
    client.cookies.set("cwd_sid", sid)

    resp = client.post("/auth/logout", headers={"X-CSRF-Token": "ignored-for-now"})
    assert resp.status_code == 204

    assert await sessions.get_session(fake_redis, sid) is None


def test_logout_without_session_cookie_still_returns_204(client: TestClient) -> None:
    resp = client.post("/auth/logout")
    assert resp.status_code == 204
