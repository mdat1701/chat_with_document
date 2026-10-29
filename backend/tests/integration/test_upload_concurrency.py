"""T-108 AC-007.2: 5 tệp tải lên ĐỒNG THỜI khi còn đúng 2 chỗ trống phải
cho đúng 2 tệp qua, 3 tệp còn lại nhận `422 QUOTA_EXCEEDED` — không có
trường hợp vượt `max_documents`. Đây là ca khó nhất của T-108, cần
Postgres thật (`SELECT ... FOR UPDATE` tuần tự hoá) nên dùng
Testcontainers như `test_owner_isolation.py` (T-504), tự `pytest.skip`
khi không có Docker thay vì mock `AsyncSession` (không mô phỏng đúng
ngữ nghĩa khóa hàng của Postgres).
"""

from __future__ import annotations

import asyncio
import io

import httpx
import pytest

from tests.integration.conftest import _create_session, _insert_document, _insert_user


@pytest.mark.integration
def test_five_concurrent_uploads_at_two_remaining_slots_admits_exactly_two(
    isolation_stack: dict[str, str], app_env: None
) -> None:
    asyncio.run(_run(isolation_stack))


async def _run(isolation_stack: dict[str, str]) -> None:
    from app.api.main import app as fastapi_app
    from app.api.routers import documents as documents_module

    class _NoopQueue:
        def enqueue(self, _task_name: str, _payload: dict[str, object]) -> str:
            return "noop"

    max_documents = 50  # mặc định Settings.max_documents — không hard-code ở test nếu có thể
    owner_id = _insert_user(isolation_stack["admin_sync_url"], email="quota-race@example.com")
    for i in range(max_documents - 2):
        _insert_document(
            isolation_stack["admin_sync_url"], owner_id=owner_id, name=f"existing-{i}.pdf"
        )
    sid, csrf_token = _create_session(isolation_stack["redis_url"], user_id=owner_id)

    fastapi_app.dependency_overrides[documents_module.get_queue] = lambda: _NoopQueue()
    try:
        transport = httpx.ASGITransport(app=fastapi_app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={"cwd_sid": sid},
            headers={"X-CSRF-Token": csrf_token},
        ) as client:

            async def _upload(index: int) -> httpx.Response:
                pdf_bytes = b"%PDF-1.4\n" + f"race-{index}".encode() * 10
                return await client.post(
                    "/api/v1/documents",
                    files={
                        "file": (
                            f"race-{index}.pdf",
                            io.BytesIO(pdf_bytes),
                            "application/pdf",
                        )
                    },
                )

            responses = await asyncio.gather(*(_upload(i) for i in range(5)))
    finally:
        fastapi_app.dependency_overrides.pop(documents_module.get_queue, None)

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 201, 422, 422, 422], [
        (r.status_code, r.text) for r in responses
    ]
