"""Khởi tạo OpenTelemetry (T-007 §5 bước 5-6, SADD §4.3).

`trace_id` lan truyền từ `api` sang `worker` qua header của task
Celery bằng `CeleryInstrumentor` chính thức của OTel (tự inject ở
producer khi `send_task`, tự extract ở consumer khi task chạy) — không
cần tự viết cơ chế truyền tay.

Span đặt tên theo SADD §4.3:
    api    : http.request -> qa.rewrite -> retrieval.vector ->
             retrieval.fts -> retrieval.rerank -> llm.stream ->
             qa.validate_citations
    worker : ingest.scan -> ingest.extract -> ingest.embed -> ingest.index
"""

from __future__ import annotations

from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Tracer

from app.core.config import get_settings

_configured = False


def configure_tracing() -> None:
    """Gọi một lần khi khởi động `api` hoặc `worker`. Idempotent."""
    global _configured
    if _configured:
        return

    settings = get_settings()
    resource = Resource.create({SERVICE_NAME: settings.service_name})
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter: Any = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    elif settings.app_env == "dev":
        # Local không có OTel Collector (T-007 §6): in ra console thay vì
        # no-op hoàn toàn, để dev vẫn thấy span khi cần debug.
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    # production mà chưa cấu hình endpoint: không thêm processor nào
    # (span vẫn tạo được nhưng không xuất đi đâu — không chặn ứng dụng).

    trace.set_tracer_provider(provider)
    _configured = True


def get_tracer(name: str) -> Tracer:
    return trace.get_tracer(name)


def instrument_fastapi(app: Any) -> None:
    """Gọi từ `app/api/main.py` (T-008)."""
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)


def instrument_celery() -> None:
    """Gọi từ `app/workers/celery_app.py` VÀ nơi tạo adapter producer
    (`app/adapters/celery_queue.py`) — cần ở cả hai phía để trace_id lan
    đúng từ lúc enqueue tới lúc worker xử lý."""
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]
