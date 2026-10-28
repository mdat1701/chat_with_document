"""Adapter hạ tầng cho các port trong `app.ports` (SADD §2.2.1):
bedrock_llm, openai_compat_llm (vLLM), tei_embedding, s3_blob,
celery_queue, redis_bus, clamav.

Chỉ `app.adapters` được phép import thư viện client hạ tầng cụ thể
(boto3, httpx tới TEI, redis, celery, …).
"""
