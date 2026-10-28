"""Pipeline xử lý PDF chạy trong worker: quét mã độc, kiểm tra cấu
trúc PDF, trích xuất theo trang, chia đoạn, embedding, ghi chunk,
chuyển trạng thái ready/failed.

Story: US-003, US-005, US-006.
"""


def process_document_use_case(document_id: str) -> None:
    """Điểm vào duy nhất mà `app.workers.ingestion_tasks` gọi (T-006).

    Logic thật (quét mã độc → kiểm tra PDF → trích xuất → chia đoạn →
    embedding) được cài đặt ở T-201, T-202, T-203.
    """
    raise NotImplementedError("Cài đặt ở T-201/T-202/T-203")
