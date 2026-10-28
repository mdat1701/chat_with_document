"""Điểm vào ứng dụng `api` (T-008). Chạy bằng:

uvicorn app.api.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.deps import assert_stub_auth_allowed
from app.api.health import router as health_router
from app.api.router import api_router
from app.api.routers.auth import router as auth_router
from app.core.config import get_settings
from app.core.errors import ERROR_HTTP_STATUS, FALLBACK_ERROR_CODE, DomainError
from app.core.logging import configure_logging, hash_user_id
from app.core.metrics import http_request_duration_seconds, http_requests_total
from app.core.tracing import configure_tracing, instrument_fastapi

logger = logging.getLogger("app.api")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    configure_tracing()
    # T-008 §6 "Stub auth bị lọt lên staging/production": dừng khởi động
    # ngay nếu app_env != "local" trong khi T-102 chưa thay get_current_user.
    assert_stub_auth_allowed()
    logger.info("Ứng dụng khởi động, app_env=%s", get_settings().app_env)
    yield
    logger.info("Ứng dụng nhận SIGTERM, tắt êm")


_settings = get_settings()

app = FastAPI(
    title="Chat với tài liệu",
    # Tắt docs công khai ở ngoài local (T-008 §3).
    docs_url="/docs" if _settings.app_env == "local" else None,
    redoc_url="/redoc" if _settings.app_env == "local" else None,
    lifespan=lifespan,
)

instrument_fastapi(app)

# Health endpoints KHÔNG đặt dưới /api/v1 để hạ tầng (probe K8s) gọi trực tiếp.
app.include_router(health_router)
# /auth/* là luồng redirect trình duyệt (T-101), không phải API JSON — cũng
# không đặt dưới /api/v1.
app.include_router(auth_router)
app.include_router(api_router, prefix="/api/v1")


RequestHandler = Callable[[Request], Awaitable[Response]]


@app.middleware("http")
async def log_requests(request: Request, call_next: RequestHandler) -> Response:
    """Ghi route, status, latency_ms, user_hash cho mọi request (T-008 §5
    bước 8) — không log query string hay body (có thể chứa câu hỏi)."""
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - start) * 1000)

    user_id = getattr(request.state, "user_id", None)
    user_hash = (
        hash_user_id(user_id, secret_key=_settings.analytics_hash_secret.encode())
        if user_id
        else None
    )
    logger.info(
        "http_request",
        extra={
            "route": request.url.path,
            "status": response.status_code,
            "latency_ms": latency_ms,
            "user_hash": user_hash,
        },
    )
    http_requests_total.labels(
        route=request.url.path, method=request.method, status=response.status_code
    ).inc()
    http_request_duration_seconds.labels(route=request.url.path, method=request.method).observe(
        latency_ms / 1000
    )
    return response


@app.exception_handler(DomainError)
async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.http_status, content=exc.to_response_body())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    # Không trả chi tiết lỗi validate mặc định của FastAPI (có thể lặp lại
    # nội dung request) — map về một ErrorCode chung cho lỗi đầu vào.
    return JSONResponse(
        status_code=ERROR_HTTP_STATUS["QUESTION_INVALID"],
        content={"code": "QUESTION_INVALID", "params": {}},
    )


@app.exception_handler(Exception)
async def handle_unmapped_error(_request: Request, exc: Exception) -> JSONResponse:
    # Lỗi chưa được ánh xạ: log đầy đủ phía server, KHÔNG rò rỉ ra client
    # (T-007 §6 "Lỗi chưa được ánh xạ").
    logger.exception("Lỗi chưa được ánh xạ sang ErrorCode: %s", type(exc).__name__)
    return JSONResponse(
        status_code=ERROR_HTTP_STATUS[FALLBACK_ERROR_CODE],
        content={"code": FALLBACK_ERROR_CODE, "params": {}},
    )
