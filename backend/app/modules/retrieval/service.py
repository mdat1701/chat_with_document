"""Truy vấn vector trong phạm vi owner_id, cổng bằng chứng
(evidence gate) và kiểm tra trích dẫn trước khi trả cho qa.

Story: US-011 - US-014.

Ngoại lệ duy nhất theo SADD Sec 2.2.1: được phép đọc bảng chunk do
ingestion ghi (ignore_imports khai báo trong pyproject.toml).
"""
