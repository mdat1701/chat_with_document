"""`/auth/login`, `/auth/callback`, `/auth/logout` (T-101).

Mẫu BFF (ADR-08): back-end giữ token, trình duyệt chỉ nhận cookie
phiên `HttpOnly`. Không route nào ở đây nằm dưới `/api/v1` — được gắn
trực tiếp vào `app` ở `main.py`, giống `/healthz`/`/readyz` (T-008),
vì đây là luồng redirect trình duyệt, không phải API JSON gọi bằng JS.
"""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.api.deps import get_db_session, get_oidc_port, get_redis_client
from app.core.config import Settings, get_settings
from app.core.signing import BadSignature, sign, unsign
from app.modules.identity import pkce, sessions
from app.modules.identity.service import LoginDecision, complete_login
from app.modules.identity.validation import is_safe_return_to
from app.ports.oidc_port import OIDCExchangeError, OIDCPort

logger = logging.getLogger("app.api.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

TX_COOKIE_NAME = "cwd_oidc_tx"
TX_COOKIE_MAX_AGE = 300  # 5 phút (T-101 §3)
SID_COOKIE_NAME = "cwd_sid"


def _callback_redirect_uri(request: Request) -> str:
    return str(request.url_for("auth_callback"))


def _internal_auth_error(code: str) -> JSONResponse:
    """`INVALID_RETURN_TO`/`OIDC_STATE_MISMATCH` là mã lỗi **nội bộ của
    luồng OIDC** (T-101 §6, không nằm trong danh mục dùng chung SDD
    §3.4.3) — trả thẳng `JSONResponse` đúng hợp đồng `{code, params}`
    thay vì `DomainError` (vốn chỉ chấp nhận mã trong danh mục chung)."""
    return JSONResponse(status_code=400, content={"code": code, "params": {}})


@router.get("/login")
async def auth_login(
    return_to: str = "/",
    *,
    oidc: OIDCPort = Depends(get_oidc_port),
    settings: Settings = Depends(get_settings),
    request: Request,
) -> Response:
    if not is_safe_return_to(return_to):
        return _internal_auth_error("INVALID_RETURN_TO")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    code_verifier = pkce.generate_code_verifier()
    code_challenge = pkce.derive_code_challenge(code_verifier)

    tx_token = sign(
        {"state": state, "nonce": nonce, "code_verifier": code_verifier, "return_to": return_to},
        secret_key=settings.analytics_hash_secret.encode(),
    )

    authorize_url = oidc.build_authorize_url(
        state=state,
        nonce=nonce,
        code_challenge=code_challenge,
        redirect_uri=_callback_redirect_uri(request),
    )

    response = RedirectResponse(authorize_url, status_code=302)
    response.set_cookie(
        TX_COOKIE_NAME,
        tx_token,
        max_age=TX_COOKIE_MAX_AGE,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response


@router.get("/callback", name="auth_callback")
async def auth_callback(
    code: str,
    state: str,
    *,
    oidc: OIDCPort = Depends(get_oidc_port),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
    request: Request,
    cwd_oidc_tx: str | None = Cookie(default=None),
) -> Response:
    if cwd_oidc_tx is None:
        logger.warning("OIDC_STATE_MISMATCH: thiếu cookie giao dịch")
        return _internal_auth_error("OIDC_STATE_MISMATCH")

    try:
        tx = unsign(
            cwd_oidc_tx,
            secret_key=settings.analytics_hash_secret.encode(),
            max_age_seconds=TX_COOKIE_MAX_AGE,
        )
    except BadSignature as exc:
        logger.warning("OIDC_STATE_MISMATCH: %s", exc)
        return _internal_auth_error("OIDC_STATE_MISMATCH")

    if not secrets.compare_digest(tx["state"], state):
        logger.warning("OIDC_STATE_MISMATCH: state không khớp")
        return _internal_auth_error("OIDC_STATE_MISMATCH")

    try:
        claims = oidc.exchange_code(
            code=code,
            code_verifier=tx["code_verifier"],
            redirect_uri=_callback_redirect_uri(request),
        )
    except OIDCExchangeError as exc:
        logger.warning("Đổi code thất bại: %s", type(exc).__name__)
        return _internal_auth_error("OIDC_STATE_MISMATCH")

    outcome = await complete_login(session, claims)
    await session.commit()

    if outcome.decision != LoginDecision.ALLOWED:
        await _audit(session, action="login_denied", actor_id=None)
        response = RedirectResponse("/no-access", status_code=302)
        response.delete_cookie(TX_COOKIE_NAME)
        return response

    assert outcome.user is not None  # noqa: S101 — bất biến sau ALLOWED
    sid, _ = await sessions.create_session(
        redis, user_id=str(outcome.user.id), roles=outcome.roles or []
    )
    await _audit(session, action="login_success", actor_id=outcome.user.id)

    response = RedirectResponse(tx["return_to"], status_code=302)
    response.delete_cookie(TX_COOKIE_NAME)
    response.set_cookie(SID_COOKIE_NAME, sid, httponly=True, secure=True, samesite="lax", path="/")
    return response


@router.post("/logout", status_code=204)
async def auth_logout(
    *,
    redis: Redis = Depends(get_redis_client),
    session: AsyncSession = Depends(get_db_session),
    cwd_sid: str | None = Cookie(default=None),
) -> Response:
    if cwd_sid is not None:
        data = await sessions.get_session(redis, cwd_sid)
        if data is not None:
            await sessions.delete_session(redis, cwd_sid, user_id=data.user_id)
            await _audit(session, action="logout", actor_id=data.user_id)

    response = Response(status_code=204)
    response.delete_cookie(SID_COOKIE_NAME)
    return response


async def _audit(session: AsyncSession, *, action: str, actor_id: object) -> None:
    from app.core.models import AuditLog

    session.add(AuditLog(ts=datetime.now(UTC), actor_id=actor_id, action=action, outcome="ok"))
    await session.commit()
