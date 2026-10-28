"""Adapter vào: router FastAPI, schema I/O, SSE, dependency auth.

Chỉ gọi use case trong `app.modules.*`, không chứa logic nghiệp vụ
(SADD §2.2.1 — api và workers chỉ là adapter vào).
"""
