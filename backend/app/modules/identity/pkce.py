"""PKCE S256 (RFC 7636) — T-101 §3."""

import base64
import hashlib
import secrets


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)[:128]


def derive_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
