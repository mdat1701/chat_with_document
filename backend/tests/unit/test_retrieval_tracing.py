"""Kiểm thử span OTel `retrieval.vector`/`retrieval.fts`/`retrieval.rerank`
(T-401 §5 bước 8) — trước phiên này không có span thủ công nào trong
`app/modules/retrieval`, chỉ có instrumentation HTTP/Celery tự động.
Dùng `InMemorySpanExporter` để xác nhận span thật sự được tạo, không chỉ
đọc code suy luận."""

from __future__ import annotations

from uuid import uuid4

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.modules.retrieval import service
from tests.unit.test_retrieval_service import _chunk, _FakeSession

_exporter = InMemorySpanExporter()


def _attach_exporter_once() -> None:
    # OTel chỉ cho phép `set_tracer_provider()` MỘT LẦN cho mỗi tiến
    # trình (tự bảo vệ khỏi bị ghi đè nhầm). Một test khác chạy trước
    # (ví dụ dùng `TestClient` như context manager, kích hoạt
    # `lifespan` → `configure_tracing()`) có thể đã set provider thật
    # rồi — nên THÊM processor của mình vào provider hiện có thay vì cố
    # thay thế nó, và chỉ làm việc này một lần (gọi lại sẽ nhân đôi số
    # span ghi nhận ở các lần export tiếp theo).
    provider = trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        trace.set_tracer_provider(provider)
    provider.add_span_processor(SimpleSpanProcessor(_exporter))


_attach_exporter_once()


@pytest.fixture
def span_exporter():
    _exporter.clear()
    yield _exporter


def _span_names(exporter: InMemorySpanExporter) -> list[str]:
    return [span.name for span in exporter.get_finished_spans()]


async def test_retrieve_emits_vector_and_fts_spans_with_candidate_counts(
    span_exporter: InMemorySpanExporter,
) -> None:
    chunk = _chunk(1)
    session = _FakeSession(vector_rows=[(chunk, "A.pdf", 0.9)], fts_rows=[])

    await service.retrieve(session, uuid4(), [0.1, 0.2], "câu hỏi", min_score=0.25)

    names = _span_names(span_exporter)
    assert "retrieval.vector" in names
    assert "retrieval.fts" in names
    vector_span = next(
        s for s in span_exporter.get_finished_spans() if s.name == "retrieval.vector"
    )
    assert vector_span.attributes is not None
    assert vector_span.attributes["candidate_count"] == 1


async def test_retrieve_emits_rerank_span_with_fallback_flag_on_failure(
    span_exporter: InMemorySpanExporter,
) -> None:
    class _FailingReranker:
        def rerank(self, _query: str, _documents: list[str]) -> list[float]:
            raise RuntimeError("TEI reranker unavailable")

    chunk = _chunk(1)
    session = _FakeSession(vector_rows=[(chunk, "A.pdf", 0.9)], fts_rows=[])

    await service.retrieve(
        session, uuid4(), [0.1, 0.2], "câu hỏi", min_score=0.25, reranker=_FailingReranker()
    )

    rerank_span = next(
        s for s in span_exporter.get_finished_spans() if s.name == "retrieval.rerank"
    )
    assert rerank_span.attributes is not None
    assert rerank_span.attributes["fallback_to_rrf"] is True
