# T-007 — Logging có lọc nội dung, tracing và danh mục lỗi

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng; trực tiếp phục vụ US-020, Pilot Gate G-04) |
| Module (SADD §2.2.1) | `core` |
| API liên quan | — (áp dụng cho mọi API) |
| Vai trò chính | TL (hỗ trợ: BE) |
| Ước lượng | 2d |
| Phụ thuộc | T-001, T-008 |
| Trạng thái | Done (phần `core`) — exception handler FastAPI hoãn sang T-008 |

## 1. Mục tiêu

Dựng tầng quan sát của `core` ngay từ Sprint 0 theo nguyên tắc **P-03: nội dung là dữ liệu nhạy cảm** — văn bản tài liệu, câu hỏi và câu trả lời **không bao giờ** xuất hiện trong log, trace, metric hay analytics. Làm việc này trước khi viết code nghiệp vụ sẽ rẻ hơn nhiều so với đi dọn rò rỉ ở Sprint 5 (nguyên tắc IP-05). Task cũng định nghĩa cơ chế ánh xạ lỗi miền → `ErrorCode` mà toàn bộ API sẽ dùng.

## 2. Tiêu chí chấp nhận

- Logger JSON có cấu trúc với đúng bộ trường chuẩn của SADD §4.3.
- Bộ lọc **chặn** mọi trường có tên `question`, `answer`, `content`, `text`, `file_name`, `prompt` ở mọi logger — kể cả khi lập trình viên vô tình truyền vào.
- Có **kiểm thử tự động** chứng minh bộ lọc hoạt động (bằng chứng cho Pilot Gate G-04).
- OpenTelemetry khởi tạo được, `trace_id` lan từ `api` sang `worker` qua header của task Celery.
- Mọi lỗi miền đều quy về một `ErrorCode` trong danh mục SDD §3.4.3; API **không** trả nguyên văn thông báo nội bộ ra client.

## 3. Hợp đồng / cấu hình cụ thể

Trường log chuẩn (SADD §4.3) — không thêm trường tự do ngoài danh sách này:

```
ts, level, service, trace_id, span_id, user_hash, route, status, latency_ms, error_code
```

Danh sách trường bị chặn (allow-list đảo ngược):

```python
# app/core/logging.py
BLOCKED_FIELDS = frozenset({
    "question", "answer", "content", "text", "file_name", "prompt",
})

def scrub(payload: dict) -> dict:
    """Loại bỏ trường nhạy cảm ở MỌI cấp lồng nhau.
    Ở môi trường dev: ghi cảnh báo để lập trình viên biết mình truyền nhầm.
    Ở production: loại bỏ im lặng, không làm hỏng request.
    """
```

Ánh xạ lỗi miền → `ErrorCode` (danh mục đầy đủ ở SDD §3.4.3):

```python
# app/core/errors.py
class DomainError(Exception):
    code: str          # ví dụ "QUOTA_EXCEEDED"
    http_status: int   # ví dụ 422

# Quy ước phản hồi lỗi chung (SADD §2.4.2):
# { "code": "<ErrorCode>", "params": { ... } }
```

Danh mục `ErrorCode` cần khai báo sẵn ở Sprint 0 (SDD §3.4.3 + bổ sung của SADD, xem D-05):

```
FILE_NOT_PDF, FILE_TOO_LARGE, TOO_MANY_PAGES, PDF_ENCRYPTED, PDF_CORRUPTED,
PDF_NO_TEXT, QUOTA_EXCEEDED, DUPLICATE_NAME, UPLOAD_NETWORK,
ANSWER_NETWORK, SERVICE_BUSY, ANSWER_TIMEOUT, ANSWER_INTERRUPTED,
SESSION_EXPIRED, NOT_AUTHORIZED, DOC_NOT_FOUND,
QUESTION_INVALID, NO_READY_DOCUMENTS, RATE_LIMITED,
FILE_REJECTED, INGESTION_FAILED            # cho so SDD §3.4.3 — xem D-05
```

Span cần có (SADD §4.3), đặt tên đúng để dashboard dùng lại được:

```
api    : http.request → qa.rewrite → retrieval.vector → retrieval.fts
         → retrieval.rerank → llm.stream → qa.validate_citations
worker : ingest.scan → ingest.extract → ingest.embed → ingest.index
```

## 4. Thay đổi dữ liệu

Không có bảng mới. (Bảng `analytics_event` và `audit_log` đã tạo ở T-005; việc **ghi** sự kiện thuộc T-404.)

## 5. Các bước triển khai

1. Viết `app/core/logging.py`: logger JSON (ví dụ `structlog` hoặc `logging` + formatter JSON), cấu hình bộ trường chuẩn ở Mục 3.
2. Cài processor `scrub()` vào **pipeline logger**, không phải vào từng lời gọi — để không thể quên. Xử lý đệ quy cho dict lồng nhau và danh sách.
3. Ở môi trường dev: khi `scrub()` loại một trường, ghi `WARNING` nêu rõ tên trường và vị trí gọi, giúp dev sửa ngay. Ở production: loại im lặng, tăng counter metric.
4. Thêm `user_hash` = HMAC-SHA256 của `user_id` với khóa bí mật (không log `user_id` thô, không log email).
5. Khởi tạo OpenTelemetry SDK, tự động instrument FastAPI, SQLAlchemy, Redis và HTTP client; exporter trỏ tới OTel Collector (cấu hình qua biến môi trường, có thể tắt ở local).
6. Lan truyền `trace_id` sang Celery: inject context vào header task khi enqueue, extract ở worker — để một lần tải tệp xem được xuyên suốt `api` → `worker`.
7. Viết `app/core/errors.py` với `DomainError` và bảng ánh xạ sang HTTP status; thêm exception handler toàn cục trong FastAPI (T-008) trả đúng định dạng `{code, params}`.
8. Khai báo hằng số `ErrorCode` như Mục 3; đánh dấu `FILE_REJECTED`, `INGESTION_FAILED` là **đề xuất bổ sung** vào SDD §3.4.3 (D-05) kèm comment.
9. Đăng ký metric Prometheus cơ bản: RED cho mọi endpoint; chừa chỗ cho các metric nghiệp vụ sẽ thêm sau (`answer_latency_seconds`, `answers_uncited_total`, `retrieval_top_score`, `ingestion_queue_depth`).
10. Viết test bộ lọc (Mục 7) và đưa vào CI như một job bắt buộc — đây là bằng chứng cho G-04.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| Dev log cả object `Document` (có `name` tệp) | `file_name` bị chặn; nếu tên trường khác (`name`), code review phải bắt — cân nhắc chặn thêm `name` ở ngữ cảnh tài liệu |
| Ngoại lệ Python chứa nội dung trong message (ví dụ lỗi parse kèm đoạn văn bản) | Exception handler **không** log `str(exc)` thô cho lỗi từ thư viện xử lý PDF/LLM; chỉ log loại ngoại lệ + `error_code` |
| Trace attribute chứa prompt | Chỉ ghi số token và độ trễ vào span, **không** ghi nội dung prompt (SADD §4.3) |
| OTel Collector không chạy ở local | Exporter ở chế độ no-op, ứng dụng vẫn chạy bình thường |
| Lỗi chưa được ánh xạ | Trả `SERVICE_BUSY` (hoặc 500 với `code` chung), log đầy đủ phía server; **không** rò rỉ stack trace ra client |

## 7. Kiểm thử bắt buộc

- [x] Gọi logger với payload chứa cả 6 trường bị chặn → bản ghi log đầu ra **không** chứa trường nào trong số đó — `test_all_six_blocked_fields_are_removed_at_top_level`
- [x] Payload lồng nhau 3 cấp có `content` ở cấp sâu nhất → vẫn bị loại — `test_blocked_field_removed_at_three_levels_of_nesting` (+ test cho list lồng dict)
- [x] Ở chế độ dev, việc loại trường sinh ra cảnh báo nêu đúng tên trường **và vị trí** (`nested.prompt`) — `test_dev_mode_logs_warning_naming_the_blocked_field`
- [ ] Một request HTTP tạo span `http.request` với `trace_id`; enqueue task Celery từ request đó → log của worker mang cùng `trace_id` — **chưa xác minh end-to-end** (cần FastAPI app thật từ T-008 + Redis); đã xác nhận `CeleryInstrumentor` kích hoạt được không lỗi (idempotent khi gọi lại)
- [ ] `DomainError("QUOTA_EXCEEDED")` ném từ tầng module → API trả `422 {"code":"QUOTA_EXCEEDED"}` — `DomainError`/`ERROR_HTTP_STATUS` đã đúng (test `test_domain_error_quota_exceeded_maps_to_422`), **nhưng chưa có exception handler FastAPI thật** để xác nhận toàn luồng HTTP (hoãn sang T-008)
- [x] Không có bản ghi log nào chứa email hay `user_id` thô (chỉ `user_hash`) — `test_hash_user_id_is_deterministic_and_does_not_leak_raw_id`

## 8. Định nghĩa Hoàn thành

- [x] Bộ lọc nội dung hoạt động và có test chạy trong CI (7 test trong `test_logging_scrub.py`, tất cả xanh)
- [ ] `trace_id` lan được từ api sang worker, kiểm chứng bằng **một luồng thật** — hạ tầng (CeleryInstrumentor) đã bật ở cả hai phía (cùng `celery_app`), nhưng chưa chạy thật vì chưa có FastAPI app (T-008) + Redis
- [x] Danh mục `ErrorCode` khai báo đủ 21 mã, khớp SDD §3.4.3 + bổ sung D-05 — `test_all_twenty_one_catalog_codes_are_declared` (tham số hóa đủ 21 giá trị) + `test_catalog_has_exactly_21_codes_no_more_no_less`
- [x] Kết quả test bộ lọc được lưu làm bằng chứng cho Pilot Gate G-04 — 13 test trong `test_logging_scrub.py` + `test_errors.py`, chạy được độc lập (không cần hạ tầng ngoài), phù hợp đưa vào CI `test-backend` (T-003)

### Ghi chú triển khai thực tế

Phần **không phụ thuộc hạ tầng** của task (bộ lọc, `ErrorCode`, cấu hình OTel,
metric Prometheus) đã viết đầy đủ và **xác minh thật bằng 13 test đơn vị**
(không mock phần lõi — `scrub()`, `DomainError`, `hash_user_id` chạy thật).

Phần phụ thuộc T-008 (chưa tồn tại khi làm task này) **chưa hoàn tất**:
- Exception handler toàn cục FastAPI (bước 7) — sẽ thêm khi viết `app/api/main.py` ở T-008, dùng lại `DomainError`/`ERROR_HTTP_STATUS` đã có sẵn ở đây.
- Middleware ghi `http_requests_total`/`http_request_duration_seconds` (bước 9) — cũng gắn vào T-008.
- Kiểm chứng `trace_id` lan api→worker bằng luồng thật — cần FastAPI app + Redis chạy thật, không có trong môi trường này.

Đã xác nhận bằng cách chạy thật (không mock): `CeleryInstrumentor().instrument()` kích hoạt được, idempotent khi gọi lại (log cảnh báo, không crash) — quan sát được log JSON thật trong lúc kiểm thử thủ công, xác nhận `_JsonFormatter` hoạt động đúng.

**Quyết định kỹ thuật tự đưa ra:** thêm `otel_exporter_endpoint` (rỗng ở local → dùng `ConsoleSpanExporter` thay vì no-op hoàn toàn, để dev vẫn thấy span khi debug) và `analytics_hash_secret` cho `hash_user_id` — task không nêu tên biến cụ thể.

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §4.3 (khả năng quan sát), nguyên tắc P-03, §2.4.2 (quy ước lỗi chung)
- [SDD UI/UX v0.3](../../design/SDD_UI_UX_Blueprint.md) §3.4.3 (danh mục mã lỗi hiển thị)
- [User Stories v0.4](../../design/User_Stories.md) US-020 (AC-020.1, AC-020.2)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0, nguyên tắc IP-05, quyết định D-05, Pilot Gate G-04
