"""Pilot access-management CLI (T-103).

The CLI deliberately has no HTTP surface.  It is intended to run next to the
API with the same database and Redis configuration.
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select

from app.core.db import get_session_factory
from app.core.models import AuditLog
from app.core.redis_client import get_redis
from app.modules.identity.models import VALID_ROLES, AppUser, UserRole
from app.modules.identity.sessions import delete_all_sessions_for_user

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate(email: str, role: str) -> None:
    if not EMAIL_RE.fullmatch(email):
        raise ValueError(f"Email không hợp lệ: {email}")
    if role not in VALID_ROLES:
        raise ValueError(f"Role không hợp lệ: {role}")


async def _audit(session: Any, action: str, user_id: UUID | None) -> None:
    actor = _actor_id()
    session.add(
        AuditLog(
            ts=datetime.now(UTC),
            actor_id=actor,
            action=action,
            target_type="app_user",
            target_id=str(user_id) if user_id else None,
            outcome="ok",
        )
    )


def _actor_id() -> UUID | None:
    raw = __import__("os").environ.get("CWD_CLI_ACTOR")
    try:
        return UUID(raw) if raw else None
    except ValueError:
        return None


async def grant_access(email: str, role: str) -> int:
    _validate(email, role)
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            user = (
                await session.execute(select(AppUser).where(AppUser.email == email))
            ).scalar_one_or_none()
            changed = user is None or not user.active
            if user is None:
                user = AppUser(id=uuid4(), email=email, active=True, granted_at=datetime.now(UTC))
                session.add(user)
                await session.flush()
            else:
                user.active = True
                user.granted_at = datetime.now(UTC)
                user.revoked_at = None
            role_row = await session.get(UserRole, {"user_id": user.id, "role": role})
            if role_row is None:
                session.add(UserRole(user_id=user.id, role=role))
                changed = True
            await _audit(session, "access_granted", user.id)
    print(f"{'Đã cấp quyền' if changed else 'Không thay đổi'} {email} (role={role})")
    return 0


async def revoke_access(email: str, confirmed: bool) -> int:
    if not EMAIL_RE.fullmatch(email):
        print(f"Email không hợp lệ: {email}", file=sys.stderr)
        return 1
    if not confirmed:
        print(f"Xác nhận thu hồi quyền cho {email} bằng --yes", file=sys.stderr)
        return 1
    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            user = (
                await session.execute(select(AppUser).where(AppUser.email == email))
            ).scalar_one_or_none()
            if user is None:
                print(f"Không tìm thấy người dùng: {email}", file=sys.stderr)
                return 1
            user.active = False
            user.revoked_at = datetime.now(UTC)
            await _audit(session, "access_revoked", user.id)
            user_id = user.id
    try:
        await delete_all_sessions_for_user(get_redis(), str(user_id))
    except Exception as exc:
        print(
            f"Quyền đã thu hồi trong CSDL nhưng chưa xóa được phiên: {type(exc).__name__}",
            file=sys.stderr,
        )
        return 2
    print(f"Đã thu hồi quyền {email}")
    return 0


async def list_users(active_only: bool) -> int:
    factory = get_session_factory()
    async with factory() as session:
        query = select(AppUser).order_by(AppUser.email)
        if active_only:
            query = query.where(AppUser.active.is_(True))
        users = (await session.execute(query)).scalars().all()
        for user in users:
            roles = (
                await session.execute(select(UserRole.role).where(UserRole.user_id == user.id))
            ).scalars().all()
            granted = (
                user.granted_at.isoformat(sep=" ", timespec="minutes")
                if user.granted_at
                else "-"
            )
            print(f"{user.email:<30} {','.join(roles):<15} {str(user.active).lower():<6} {granted}")
    return 0


def _read_access_file(path: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    current: dict[str, str] = {}
    for raw_line in open(path, encoding="utf-8"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            if current:
                entries.append((current["email"], current.get("role", "user")))
                current = {}
            line = line[1:].strip()
        key, separator, value = line.partition(":")
        if separator and key.strip() in {"email", "role"}:
            current[key.strip()] = value.strip().strip("'\"")
    if current:
        entries.append((current["email"], current.get("role", "user")))
    for email, role in entries:
        _validate(email, role)
    return entries


async def sync_access(path: str, confirmed: bool) -> int:
    entries = _read_access_file(path)
    wanted = {email.lower(): (email, role) for email, role in entries}
    factory = get_session_factory()
    async with factory() as session:
        users = (await session.execute(select(AppUser))).scalars().all()
        to_revoke = [user for user in users if user.active and user.email.lower() not in wanted]
    if to_revoke and not confirmed:
        print(
            "Các tài khoản sau sẽ bị thu hồi: "
            + ", ".join(user.email for user in to_revoke)
            + "; dùng --yes để xác nhận.",
            file=sys.stderr,
        )
        return 1
    for email, role in wanted.values():
        await grant_access(email, role)
    for user in to_revoke:
        result = await revoke_access(user.email, True)
        if result != 0:
            return result
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    grant = sub.add_parser("grant-access")
    grant.add_argument("--email", required=True)
    grant.add_argument("--role", default="user")
    revoke = sub.add_parser("revoke-access")
    revoke.add_argument("--email", required=True)
    revoke.add_argument("--yes", action="store_true")
    listing = sub.add_parser("list-users")
    listing.add_argument("--active-only", action="store_true")
    sync = sub.add_parser("sync-access")
    sync.add_argument("--file", required=True)
    sync.add_argument("--yes", action="store_true")
    return parser


async def _run(args: argparse.Namespace) -> int:
    if args.command == "grant-access":
        return await grant_access(args.email, args.role)
    if args.command == "revoke-access":
        return await revoke_access(args.email, args.yes)
    if args.command == "sync-access":
        return await sync_access(args.file, args.yes)
    return await list_users(args.active_only)


def main() -> None:
    try:
        raise SystemExit(asyncio.run(_run(build_parser().parse_args())))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
