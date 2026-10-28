"""Kiểm thử `app.modules.qa.service.stream_answer` — trước phiên này
`app/modules/qa` không có test đơn vị nào. Bao phủ 2 lỗi đã sửa:

- T-304: khi cổng bằng chứng (T-302) không có bằng chứng, KHÔNG được gọi LLM.
- T-303: trích dẫn trỏ tới `document_id` không có trong bằng chứng truy xuất
  phải bị loại, không được chấp nhận chỉ vì đúng cú pháp `[doc:... p:...]`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.modules.qa import service
from app.modules.retrieval.service import Evidence
from app.ports.llm_port import LLMRequest


class _FakeEmbedding:
    dimensions = 4

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3, 0.4] for _ in texts]


class _ScriptedLLM:
    def __init__(self, text: str) -> None:
        self._text = text
        self.called = False

    async def stream(self, _request: LLMRequest) -> AsyncIterator[str]:
        self.called = True
        yield self._text


async def test_stream_answer_skips_llm_when_evidence_gate_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _empty_retrieve(*_args: object, **_kwargs: object) -> list[Evidence]:
        return []

    monkeypatch.setattr(service, "retrieve", _empty_retrieve)
    monkeypatch.setattr(service, "diversify_evidence", lambda evidence, **_k: evidence)
    llm = _ScriptedLLM("không nên được gọi")

    events = [
        event
        async for event in service.stream_answer(
            session=object(),
            owner_id=uuid4(),
            question="Thủ đô của Pháp là gì?",
            embedding=_FakeEmbedding(),
            llm=llm,
        )
    ]

    assert llm.called is False
    assert events[-1][0] == "complete"
    assert events[-1][1]["answer_type"] == "not_found"
    assert events[-1][1]["citations"] == []


async def test_stream_answer_rejects_citation_to_unretrieved_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_doc_id = uuid4()
    fake_doc_id = uuid4()
    evidence = [Evidence(real_doc_id, "Thật.pdf", 1, 2, "nội dung thật", 0.9)]

    async def _fake_retrieve(*_args: object, **_kwargs: object) -> list[Evidence]:
        return evidence

    monkeypatch.setattr(service, "retrieve", _fake_retrieve)
    monkeypatch.setattr(service, "diversify_evidence", lambda ev, **_k: ev)
    hallucinated = f"Câu trả lời bịa [doc:{fake_doc_id} p:1-1]."
    llm = _ScriptedLLM(hallucinated)

    events = [
        event
        async for event in service.stream_answer(
            session=object(),
            owner_id=uuid4(),
            question="Câu hỏi có bằng chứng thật nhưng LLM bịa trích dẫn",
            embedding=_FakeEmbedding(),
            llm=llm,
        )
    ]

    assert llm.called is True
    complete = events[-1][1]
    assert complete["answer_type"] == "not_found"
    assert complete["citations"] == []


async def test_stream_answer_accepts_citation_to_retrieved_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    doc_id = uuid4()
    evidence = [Evidence(doc_id, "A.pdf", 3, 4, "nội dung", 0.9)]

    async def _fake_retrieve(*_args: object, **_kwargs: object) -> list[Evidence]:
        return evidence

    monkeypatch.setattr(service, "retrieve", _fake_retrieve)
    monkeypatch.setattr(service, "diversify_evidence", lambda ev, **_k: ev)
    llm = _ScriptedLLM(f"Câu trả lời đúng [doc:{doc_id} p:3-4].")

    events = [
        event
        async for event in service.stream_answer(
            session=object(),
            owner_id=uuid4(),
            question="Câu hỏi có đáp án rõ",
            embedding=_FakeEmbedding(),
            llm=llm,
        )
    ]

    complete = events[-1][1]
    assert complete["answer_type"] == "answered"
    assert complete["citations"] == [
        {
            "document_id": str(doc_id),
            "document_name": "A.pdf",
            "page_start": 3,
            "page_end": 4,
        }
    ]
