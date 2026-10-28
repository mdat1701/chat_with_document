"""Kiểm tra nhanh 5 dịch vụ hạ tầng cục bộ (T-002 §5 bước 8).

Dùng sau `make up` để xác nhận PostgreSQL, Redis, MinIO, ClamAV, TEI
đều sẵn sàng trước khi bắt đầu code. Không phụ thuộc gì ngoài thư viện
chuẩn + các client đã có trong `backend/pyproject.toml` dev extras.

Chạy:
    python scripts/smoke_infra.py
"""

from __future__ import annotations

import os
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

# Chuỗi thử chuẩn EICAR (vô hại, dùng để kiểm tra antivirus — T-002 §7).
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_postgres() -> CheckResult:
    try:
        import asyncpg  # type: ignore[import-untyped]
    except ImportError:
        return CheckResult("PostgreSQL", False, "thiếu thư viện asyncpg")

    import asyncio

    url = os.environ.get(
        "DATABASE_URL", "postgresql://cwd:cwd_local_only@localhost:5432/cwd"
    ).replace("postgresql+asyncpg://", "postgresql://")

    async def _run() -> str:
        conn = await asyncpg.connect(url, timeout=5)
        try:
            rows = await conn.fetch(
                "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'unaccent', 'citext')"
            )
            found = sorted(r["extname"] for r in rows)
            missing = sorted({"vector", "unaccent", "citext"} - set(found))
            if missing:
                raise RuntimeError(f"thiếu extension: {missing}")
            return f"extensions OK: {found}"
        finally:
            await conn.close()

    try:
        detail = asyncio.run(_run())
        return CheckResult("PostgreSQL", True, detail)
    except Exception as exc:  # noqa: BLE001 — smoke test, báo lỗi gì cũng được
        return CheckResult("PostgreSQL", False, str(exc))


def check_redis() -> CheckResult:
    try:
        import redis  # type: ignore[import-untyped]
    except ImportError:
        return CheckResult("Redis", False, "thiếu thư viện redis")

    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.from_url(url, socket_connect_timeout=5)
        pong = client.ping()
        return CheckResult("Redis", bool(pong), "PING -> PONG" if pong else "không phản hồi")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("Redis", False, str(exc))


def check_minio() -> CheckResult:
    endpoint = os.environ.get("S3_ENDPOINT", "http://localhost:9000")
    try:
        with urllib.request.urlopen(f"{endpoint}/minio/health/live", timeout=5) as resp:
            ok = resp.status == 200
            return CheckResult("MinIO", ok, f"HTTP {resp.status}")
    except (urllib.error.URLError, OSError) as exc:
        return CheckResult("MinIO", False, str(exc))


def check_clamav() -> CheckResult:
    """Gửi lệnh PING rồi chuỗi EICAR qua giao thức clamd (INSTREAM)."""
    host = os.environ.get("CLAMAV_HOST", "localhost")
    port = int(os.environ.get("CLAMAV_PORT", "3310"))
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.sendall(b"zPING\0")
            pong = sock.recv(64)
            if b"PONG" not in pong:
                return CheckResult("ClamAV", False, f"PING không trả PONG: {pong!r}")

        with socket.create_connection((host, port), timeout=10) as sock:
            sock.sendall(b"zINSTREAM\0")
            chunk = EICAR
            sock.sendall(len(chunk).to_bytes(4, "big") + chunk)
            sock.sendall((0).to_bytes(4, "big"))  # chunk rỗng = kết thúc
            reply = sock.recv(256).decode(errors="replace")
            infected = "FOUND" in reply
            return CheckResult("ClamAV", infected, reply.strip())
    except OSError as exc:
        return CheckResult("ClamAV", False, str(exc))


def check_tei() -> CheckResult:
    import json

    url = os.environ.get("TEI_EMBED_URL", "http://localhost:8080") + "/embed"
    payload = json.dumps({"inputs": "Thời hạn thanh toán là bao lâu?"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
            vector = (
                body[0] if isinstance(body, list) and body and isinstance(body[0], list) else body
            )
            dim = len(vector)
            return CheckResult("TEI (bge-m3)", dim == 1024, f"{dim} chiều")
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        return CheckResult("TEI (bge-m3)", False, str(exc))


CHECKS = [check_postgres, check_redis, check_minio, check_clamav, check_tei]


def main() -> int:
    results = [check() for check in CHECKS]
    width = max(len(r.name) for r in results)
    print(f"{'Dịch vụ'.ljust(width)}  Kết quả  Chi tiết")
    for r in results:
        status = "OK " if r.ok else "LỖI"
        print(f"{r.name.ljust(width)}  {status}     {r.detail}")

    ok_count = sum(r.ok for r in results)
    print(f"\n{ok_count}/{len(results)} dịch vụ sẵn sàng.")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
