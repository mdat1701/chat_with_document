"""Ánh xạ danh tính OIDC sang app_user; kiểm tra danh sách cấp quyền;
quản lý vai trò (user/manager/evaluator/admin) và phiên đăng nhập.

Story: US-001, US-002, US-023.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity import repository
from app.modules.identity.models import AppUser
from app.ports.oidc_port import OIDCClaims


class LoginDecision(Enum):
    ALLOWED = auto()
    DENIED_NOT_FOUND = auto()
    DENIED_INACTIVE = auto()


@dataclass(frozen=True)
class LoginOutcome:
    decision: LoginDecision
    user: AppUser | None = None
    roles: list[str] | None = None


async def complete_login(session: AsyncSession, claims: OIDCClaims) -> LoginOutcome:
    """Xác thực OIDC thành công KHÔNG đủ để vào ứng dụng (AC-001.2) —
    tài khoản phải tồn tại và `active=True` (T-101 §5 bước 5).

    1. Tra theo `oidc_subject` (đã từng đăng nhập trước đây).
    2. Nếu không thấy, tra theo `email` (đã được T-103 cấp quyền bằng
       CLI nhưng chưa từng đăng nhập).
    3. Chỉ **điền `oidc_subject`** khi tài khoản thực sự được phép vào
       (active=True) — quyết định có chủ đích: không liên kết danh
       tính OIDC cho tài khoản bị từ chối, dù việc liên kết tự nó
       không rò rỉ gì (người dùng đã tự chứng minh sở hữu email qua
       IdP), để tránh ghi dữ liệu cho một lượt đăng nhập bị từ chối.
    """
    user = await repository.get_by_oidc_subject(session, claims.sub)
    found_by_email_only = False

    if user is None:
        user = await repository.get_by_email(session, claims.email)
        found_by_email_only = user is not None

    if user is None:
        return LoginOutcome(decision=LoginDecision.DENIED_NOT_FOUND)

    if not user.active:
        return LoginOutcome(decision=LoginDecision.DENIED_INACTIVE, user=user)

    if found_by_email_only:
        await repository.link_oidc_subject(
            session, user=user, oidc_subject=claims.sub, display_name=claims.display_name
        )

    roles = await repository.get_roles(session, user.id)
    return LoginOutcome(decision=LoginDecision.ALLOWED, user=user, roles=roles)
