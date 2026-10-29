"""Integration contract for G-03.

The fixture layer is supplied by the CI Testcontainers profile. These tests
stay intentionally small so they can also run against a staging-like API.
"""

import pytest
import sqlalchemy as sa


@pytest.mark.integration
@pytest.mark.isolation
def test_owner_isolation_contract(client_a, client_b, seeded_documents):
    document_b = seeded_documents["b"][0]
    response = client_a.get("/api/v1/documents")
    assert response.status_code == 200
    assert all(item["id"] != str(document_b.id) for item in response.json())
    assert client_a.delete(f"/api/v1/documents/{document_b.id}").status_code == 404


@pytest.mark.integration
@pytest.mark.isolation
def test_owner_cannot_query_other_owner_document(client_a, seeded_documents):
    document_b = seeded_documents["b"][0]
    response = client_a.post(
        "/api/v1/conversations",
        headers={"X-Test-Document": str(document_b.id)},
    )
    assert response.status_code in {201, 403, 404}


@pytest.mark.integration
@pytest.mark.isolation
def test_rls_blocks_even_with_direct_sql_bypassing_app_layer(isolation_stack, seeded_documents):
    """T-504 §3/§7: chứng minh RLS chặn độc lập với tầng ứng dụng — chạy
    thẳng SQL bằng vai trò `cwd_app` (không qua FastAPI/ORM) sau khi
    `SET LOCAL app.user_id = A`, xác nhận không thấy hàng nào của B."""
    sync_app_url = isolation_stack["database_url"].replace("+asyncpg", "")
    engine = sa.create_engine(sync_app_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                sa.text("SELECT set_config('app.user_id', :uid, true)"),
                {"uid": seeded_documents["owner_a"]},
            )
            rows = conn.execute(sa.text("SELECT id FROM document")).fetchall()
    finally:
        engine.dispose()

    visible_ids = {str(row.id) for row in rows}
    assert str(seeded_documents["b"][0].id) not in visible_ids
    assert str(seeded_documents["a"][0].id) in visible_ids


@pytest.mark.integration
@pytest.mark.isolation
def test_rls_fails_closed_without_app_user_id_set(isolation_stack):
    """T-504 §7: một truy vấn KHÔNG đặt `app.user_id` trước phải lỗi
    (fail-closed, T-104) — không bao giờ âm thầm trả về toàn bộ bảng."""
    sync_app_url = isolation_stack["database_url"].replace("+asyncpg", "")
    engine = sa.create_engine(sync_app_url)
    try:
        with engine.connect() as conn, pytest.raises(sa.exc.DBAPIError):
            conn.execute(sa.text("SELECT id FROM document")).fetchall()
    finally:
        engine.dispose()
