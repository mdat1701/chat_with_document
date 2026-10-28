"""`OIDCPort` — cổng mà `modules.identity` dùng để nói chuyện với nhà
cung cấp danh tính, không import thư viện OIDC cụ thể (nguyên tắc P-01,
T-101 §5 bước 2). Đổi IdP (D-03: SSO nội bộ hay Keycloak) chỉ cần đổi
adapter, không sửa `modules/identity`.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class OIDCClaims:
    """Thông tin lấy được từ ID token sau khi xác thực thành công."""

    sub: str
    email: str
    display_name: str | None


class OIDCPort(Protocol):
    def build_authorize_url(
        self, *, state: str, nonce: str, code_challenge: str, redirect_uri: str
    ) -> str:
        """URL `authorize` của IdP để redirect trình duyệt tới (T-101 §3)."""
        ...

    def exchange_code(self, *, code: str, code_verifier: str, redirect_uri: str) -> OIDCClaims:
        """Đổi `code` lấy token qua back-channel, verify ID token (chữ ký
        JWKS, `iss`/`aud`/`exp`/`nonce`), trả về `OIDCClaims`.

        Ném `OIDCExchangeError` nếu token không hợp lệ hoặc IdP từ chối.
        """
        ...


class OIDCExchangeError(Exception):
    """`code` không đổi được lấy token hợp lệ (IdP từ chối, token sai
    chữ ký, hoặc claim không khớp)."""
