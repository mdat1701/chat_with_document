"""Kiểm thử logic quyết định đăng nhập `complete_login` (T-101 §7).

Mock tầng `repository` (đã có test tích hợp riêng chạy trên Postgres
thật ở `tests/integration/test_identity_repository.py`) để cô lập và
kiểm chứng đúng NHÁNH QUYẾT ĐỊNH — đây là logic quan trọng nhất của
US-001/AC-001.2, không phụ thuộc cách SQLAlchemy map cột.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.modules.identity.models import AppUser
from app.modules.identity.service import LoginDecision, complete_login
from app.ports.oidc_port import OIDCClaims

CLAIMS = OIDCClaims(sub="oidc-sub-123", email="user@example.com", display_name="Người Dùng")


def _make_user(*, active: bool, oidc_subject: str | None = None) -> AppUser:
    user = AppUser()
    user.id = uuid4()
    user.oidc_subject = oidc_subject
    user.email = CLAIMS.email
    user.display_name = None
    user.active = active
    return user


@pytest.mark.parametrize("fake_session", [AsyncMock()])
async def test_denied_when_user_not_found_by_sub_or_email(fake_session: AsyncMock) -> None:
    with (
        patch("app.modules.identity.repository.get_by_oidc_subject", return_value=None),
        patch("app.modules.identity.repository.get_by_email", return_value=None),
    ):
        outcome = await complete_login(fake_session, CLAIMS)
    assert outcome.decision == LoginDecision.DENIED_NOT_FOUND
    assert outcome.user is None


async def test_denied_when_user_found_but_inactive() -> None:
    inactive_user = _make_user(active=False, oidc_subject=CLAIMS.sub)
    with patch("app.modules.identity.repository.get_by_oidc_subject", return_value=inactive_user):
        outcome = await complete_login(AsyncMock(), CLAIMS)
    assert outcome.decision == LoginDecision.DENIED_INACTIVE
    assert outcome.user is inactive_user


async def test_allowed_when_found_by_subject_and_active() -> None:
    active_user = _make_user(active=True, oidc_subject=CLAIMS.sub)
    with (
        patch("app.modules.identity.repository.get_by_oidc_subject", return_value=active_user),
        patch("app.modules.identity.repository.get_roles", return_value=["user"]),
    ):
        outcome = await complete_login(AsyncMock(), CLAIMS)
    assert outcome.decision == LoginDecision.ALLOWED
    assert outcome.roles == ["user"]


async def test_first_login_links_oidc_subject_when_found_by_email_only() -> None:
    """T-103 đã cấp quyền bằng email qua CLI, người dùng CHƯA từng đăng
    nhập (oidc_subject rỗng) — lần đăng nhập đầu phải điền oidc_subject."""
    user_without_subject = _make_user(active=True, oidc_subject=None)
    link_mock = AsyncMock()
    with (
        patch("app.modules.identity.repository.get_by_oidc_subject", return_value=None),
        patch("app.modules.identity.repository.get_by_email", return_value=user_without_subject),
        patch("app.modules.identity.repository.link_oidc_subject", link_mock),
        patch("app.modules.identity.repository.get_roles", return_value=["user"]),
    ):
        outcome = await complete_login(AsyncMock(), CLAIMS)

    link_mock.assert_awaited_once()
    assert link_mock.await_args.kwargs["oidc_subject"] == CLAIMS.sub
    assert outcome.decision == LoginDecision.ALLOWED


async def test_inactive_user_found_by_email_is_still_denied_without_linking() -> None:
    """Tài khoản bị thu hồi quyền (active=False) không được phép đăng
    nhập dù tìm thấy bằng email — không nên điền oidc_subject cho tài
    khoản bị từ chối (tránh rò rỉ liên kết danh tính không cần thiết)."""
    inactive_user = _make_user(active=False, oidc_subject=None)
    link_mock = AsyncMock()
    with (
        patch("app.modules.identity.repository.get_by_oidc_subject", return_value=None),
        patch("app.modules.identity.repository.get_by_email", return_value=inactive_user),
        patch("app.modules.identity.repository.link_oidc_subject", link_mock),
    ):
        outcome = await complete_login(AsyncMock(), CLAIMS)

    assert outcome.decision == LoginDecision.DENIED_INACTIVE
