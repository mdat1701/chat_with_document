"""Hiện thực `OIDCPort` bằng `authlib` (T-101 §5 bước 1-2). Duy nhất
nơi gọi tới IdP — `modules.identity` chỉ biết `OIDCPort`.

Hỗ trợ cả hai phương án D-03 (SSO nội bộ hoặc Keycloak) vì cả hai đều
là OIDC chuẩn — chỉ khác `oidc_issuer` trong cấu hình.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlencode

import httpx
from authlib.jose import JsonWebKey, jwt
from authlib.jose.errors import JoseError

from app.core.config import Settings, get_settings
from app.ports.oidc_port import OIDCClaims, OIDCExchangeError


class AuthlibOIDCAdapter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._discovery: dict[str, str] | None = None
        self._jwks: dict[str, object] | None = None

    def _discover(self) -> dict[str, str]:
        if self._discovery is None:
            url = self._settings.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration"
            resp = httpx.get(url, timeout=5.0)
            resp.raise_for_status()
            self._discovery = resp.json()
        return self._discovery

    def build_authorize_url(
        self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str
    ) -> str:
        endpoint = self._discover()["authorization_endpoint"]
        params = {
            "response_type": "code",
            "client_id": self._settings.oidc_client_id,
            "redirect_uri": redirect_uri,
            "scope": "openid profile email",
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{endpoint}?{urlencode(params)}"

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> OIDCClaims:
        token_endpoint = self._discover()["token_endpoint"]
        try:
            resp = httpx.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._settings.oidc_client_id,
                    "client_secret": self._settings.oidc_client_secret,
                    "code_verifier": code_verifier,
                },
                timeout=5.0,
            )
            resp.raise_for_status()
            id_token = resp.json()["id_token"]
        except (httpx.HTTPError, KeyError) as exc:
            raise OIDCExchangeError(f"IdP từ chối đổi code: {exc}") from exc

        try:
            claims = self._verify_id_token(id_token)
        except JoseError as exc:
            raise OIDCExchangeError(f"ID token không hợp lệ: {exc}") from exc

        return OIDCClaims(
            sub=str(claims["sub"]),
            email=str(claims["email"]),
            display_name=str(name) if (name := claims.get("name")) else None,
        )

    def _verify_id_token(self, id_token: str) -> dict[str, object]:
        if self._jwks is None:
            jwks_url = self._discover()["jwks_uri"]
            resp = httpx.get(jwks_url, timeout=5.0)
            resp.raise_for_status()
            self._jwks = JsonWebKey.import_key_set(resp.json())

        claims = jwt.decode(
            id_token,
            self._jwks,
            claims_options={
                "iss": {"essential": True, "value": self._settings.oidc_issuer},
                "aud": {"essential": True, "value": self._settings.oidc_client_id},
                "exp": {"essential": True},
            },
        )
        claims.validate()
        return dict(claims)


@lru_cache
def get_oidc_adapter() -> AuthlibOIDCAdapter:
    return AuthlibOIDCAdapter(get_settings())
