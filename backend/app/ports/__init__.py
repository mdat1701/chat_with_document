"""Cổng (interface) mà module miền gọi vào, không phụ thuộc hạ tầng
cụ thể (SADD §1.2 nguyên tắc P-01).

Mỗi port dưới đây có >=1 adapter tương ứng trong `app.adapters`:
LLMPort, EmbeddingPort, RerankPort, BlobStorePort, QueuePort,
MalwareScanPort, EventBusPort.
"""
