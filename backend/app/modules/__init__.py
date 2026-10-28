"""9 module nghiệp vụ (bounded context) của hệ thống (SADD §2.2.1).

Mỗi module chỉ lộ ra ngoài qua `service.py`; không module nào import
trực tiếp `repository.py`/`models.py` của module khác (trừ ngoại lệ
`retrieval` đọc bảng `chunk` do `ingestion` ghi — xem pyproject.toml).
"""
