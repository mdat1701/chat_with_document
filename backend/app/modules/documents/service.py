"""Vòng đời tài liệu: tạo, xóa, kiểm tra hạn mức trong giao dịch,
xử lý trùng tên, phát trạng thái qua SSE.

Story: US-003 - US-010, US-021.
"""


def reconcile_orphan_blobs_use_case(older_than_hours: int = 24) -> int:
    """Điểm vào mà `app.workers.blob_tasks.reconcile_orphans` gọi
    (T-006). Xóa object trong kho tệp không có bản ghi `document`
    tương ứng (tải lên bị gián đoạn). Trả về số object đã xóa. Logic
    thật ở T-207."""
    raise NotImplementedError("Cài đặt ở T-207")
