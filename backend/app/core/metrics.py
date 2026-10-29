"""Metric Prometheus cơ bản (T-007 §5 bước 9, SADD §4.3).

RED (Rate/Errors/Duration) cho mọi endpoint ngay từ Sprint 0; metric
nghiệp vụ cụ thể (gắn nhãn `answer_type`, `error_code`...) được dùng
dần từ Sprint 2-5 (T-204, T-303, T-501) — khai báo sẵn tên ở đây để
không phải sửa chỗ khác khi thêm.
"""

from prometheus_client import Counter, Gauge, Histogram

# --- RED chung cho mọi endpoint (gắn ở FastAPI middleware, T-008) ---
http_requests_total = Counter(
    "http_requests_total", "Tổng số request", ["route", "method", "status"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "Độ trễ xử lý request", ["route", "method"]
)

# --- Metric nghiệp vụ (đăng ký tên trước, dùng dần từ Sprint 2+) ---
answer_latency_seconds = Histogram(
    "answer_latency_seconds", "Độ trễ từ câu hỏi tới câu trả lời đầy đủ", ["answer_type"]
)
answers_uncited_total = Counter(
    "answers_uncited_total", "Số câu trả lời có nội dung nhưng không có trích dẫn hợp lệ (KR2.3)"
)
retrieval_top_score = Histogram(
    "retrieval_top_score", "Điểm rerank cao nhất mỗi lượt truy xuất (theo dõi trôi chất lượng)"
)
ingestion_queue_depth = Histogram(
    "ingestion_queue_depth", "Độ sâu hàng đợi ingestion tại thời điểm đẩy job"
)
documents_failed_total = Counter("documents_failed_total", "Số tài liệu xử lý lỗi", ["error_code"])
auth_me_total = Counter("auth_me_total", "Kết quả xác thực GET /me", ["outcome"])
csrf_rejected_total = Counter("csrf_rejected_total", "Số request bị từ chối vì CSRF")
sse_connections = Gauge("sse_connections", "Số kết nối SSE đang mở")

# --- Rate limit (T-105) ---
ratelimit_unavailable_total = Counter(
    "ratelimit_unavailable_total",
    "Số lần check_rate_limit() fail-open vì Redis không sẵn sàng (T-105 §5 bước 7)",
)
ratelimit_rejected_total = Counter(
    "ratelimit_rejected_total", "Số request bị chặn 429 RATE_LIMITED", ["scope"]
)

# --- LLM adapter resilience (T-301) ---
llm_ttft_seconds = Histogram(
    "llm_ttft_seconds", "Thời gian từ lúc gọi LLM tới khi nhận token đầu tiên (TTFT)"
)
llm_tokens_total = Counter(
    "llm_tokens_total", "Số mẩu (chunk) token trao đổi với LLM", ["direction"]
)
llm_errors_total = Counter("llm_errors_total", "Số lỗi khi gọi LLM theo mã lỗi", ["code"])
circuit_breaker_state = Gauge(
    "circuit_breaker_state", "Trạng thái circuit breaker gọi LLM (0=closed, 1=open)"
)
