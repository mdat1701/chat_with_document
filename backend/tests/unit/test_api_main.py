"""Kiểm thử khung ứng dụng FastAPI (T-008 §7) — chạy thật qua
TestClient, không mock FastAPI/Starlette."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.errors import DomainError


@pytest.fixture
def client() -> TestClient:
    from app.api.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_healthz_returns_200_without_touching_dependencies(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readyz_returns_503_with_per_component_detail_when_all_unreachable(
    client: TestClient,
) -> None:
    resp = client.get("/readyz")
    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "not_ready"
    assert body["checks"] == {
        "postgres": "unreachable",
        "redis": "unreachable",
        "tei": "unreachable",
    }


def test_business_route_is_mounted_under_api_v1() -> None:
    from app.api.main import app
    from app.api.router import api_router

    @api_router.get("/_test-route")
    async def _probe() -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(app) as c:
        resp = c.get("/api/v1/_test-route")
    assert resp.status_code == 200
    assert resp.json() == {"ok": "true"}


def test_domain_error_raised_from_route_maps_to_its_http_status_and_code() -> None:
    from app.api.main import app
    from app.api.router import api_router

    @api_router.get("/_test-domain-error")
    async def _raise_domain_error() -> None:
        raise DomainError("NOT_AUTHORIZED")

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/_test-domain-error")
    assert resp.status_code == 403
    assert resp.json() == {"code": "NOT_AUTHORIZED", "params": {}}


def test_unmapped_exception_falls_back_without_leaking_detail() -> None:
    from app.api.main import app
    from app.api.router import api_router

    @api_router.get("/_test-unmapped-error")
    async def _raise_value_error() -> None:
        raise ValueError("thông tin nội bộ không được lộ ra ngoài")

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/_test-unmapped-error")
    assert resp.status_code == 503
    body = resp.json()
    assert body["code"] == "SERVICE_BUSY"
    assert "thông tin nội bộ" not in resp.text


def test_validation_error_maps_to_question_invalid() -> None:
    from pydantic import BaseModel

    from app.api.main import app
    from app.api.router import api_router

    class Body(BaseModel):
        text: str

    @api_router.post("/_test-validation")
    async def _validate(_body: Body) -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.post("/api/v1/_test-validation", json={})
    assert resp.status_code == 400
    assert resp.json() == {"code": "QUESTION_INVALID", "params": {}}


def test_docs_enabled_in_local_env(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200


def test_stub_auth_guard_raises_outside_local_env() -> None:
    from unittest.mock import patch

    from app.api.deps import assert_stub_auth_allowed
    from app.core.config import Settings

    fake_settings = Settings(app_env="staging")
    with patch("app.api.deps.get_settings", return_value=fake_settings):
        with pytest.raises(RuntimeError, match="STUB"):
            assert_stub_auth_allowed()


def test_stub_auth_guard_passes_in_local_env() -> None:
    from app.api.deps import assert_stub_auth_allowed

    assert_stub_auth_allowed()  # không raise — app_env mặc định "local"
