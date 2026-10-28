"""`CeleryQueueAdapter` là nơi DUY NHẤT gọi `celery_app.send_task`
trực tiếp (T-006 §5 bước 2) — kiểm thử bằng mock, không cần Redis."""

from unittest.mock import patch

from app.adapters.celery_queue import CeleryQueueAdapter


def test_enqueue_calls_send_task_with_task_name_and_payload() -> None:
    adapter = CeleryQueueAdapter()
    fake_result = type("R", (), {"id": "job-123"})()
    with patch(
        "app.adapters.celery_queue.celery_app.send_task", return_value=fake_result
    ) as mock_send:
        job_id = adapter.enqueue("ingestion.process", {"document_id": "abc"})

    mock_send.assert_called_once_with("ingestion.process", kwargs={"document_id": "abc"})
    assert job_id == "job-123"
