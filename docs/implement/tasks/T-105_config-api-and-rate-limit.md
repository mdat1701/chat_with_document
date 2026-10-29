# T-105 — `GET /config` và giới hạn tần suất

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-006 (báo ngay khi tệp vượt giới hạn), US-007 (báo khi đạt số tài liệu tối đa) |
| Epic | EP-02 — Quản lý tài liệu |
| Module (SADD §2.2.1) | `core` |
| API liên quan | API-02 `GET /config` |
| Vai trò chính | BE |
| Ước lượng | 1d |
| Phụ thuộc | T-008 (khung FastAPI), T-102 (phiên) |
| Trạng thái | **Done** (xác nhận bằng 12 test; metric + log fail-open §5 bước 7-8 đã sửa — xem ghi chú) |

## 1. Mục tiêu

Phát các giá trị mặc định **DF-01 – DF-10** của PRD §0.3 ra front-end qua một endpoint duy nhất, để UI không hard-code giới hạn (nguyên tắc P-06 "cấu hình thay vì hằng số"), và cài hạ tầng giới hạn tần suất dùng chung cho tải lên (Sprint 1) và hỏi đáp (Sprint 3).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-006.1 | *Given* tệp đúng 20 MB (DF-01), *When* tải lên, *Then* tệp được chấp nhận |
| AC-006.2 | *Given* tệp lớn hơn 20 MB, *When* chọn tệp, *Then* bị từ chối **trước khi truyền tệp đi** (UI dựa vào `max_file_size_bytes` từ `/config`) |
| AC-007.1 | *Given* đã có đúng 50 tài liệu (DF-02), *When* tải thêm, *Then* bị từ chối với thông báo "Đã đạt tối đa 50 tài liệu…" |
| AC-007.2 | *Given* có 48 tài liệu, *When* tải cùng lúc 5 tệp, *Then* 2 tệp đầu được chấp nhận, 3 tệp bị từ chối (thực thi ở T-108, dùng hạn mức từ cấu hình này) |

## 3. Hợp đồng API

```http
GET /config
Cookie: cwd_sid=<sid>
→ 200 {
    "max_file_size_bytes": 20971520,   // DF-01 — 20 MB
    "max_documents": 50,               // DF-02
    "max_pages": 300,                  // DF-03
    "retention_days": 90,              // DF-05
    "max_question_length": 2000,       // DF-07
    "answer_timeout_ms": 60000         // DF-10
  }
→ 401 { "code": "SESSION_EXPIRED" }
```

```http
# Khi vượt giới hạn tần suất (áp dụng cho POST /documents và POST .../questions)
→ 429 { "code": "RATE_LIMITED", "params": { "retry_after_seconds": 42 } }
   Retry-After: 42
```

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| ConfigMap / biến môi trường | Thêm `CWD_MAX_FILE_SIZE_BYTES`, `CWD_MAX_DOCUMENTS`, `CWD_MAX_PAGES`, `CWD_RETENTION_DAYS`, `CWD_MAX_QUESTION_LENGTH`, `CWD_ANSWER_TIMEOUT_MS` |
| Redis | Key giới hạn tần suất: `rl:upload:{user_id}` (60 tệp/giờ) và `rl:question:{user_id}` (10 câu/phút), kiểu token bucket hoặc sliding window counter với TTL tương ứng |

Không có bảng CSDL mới.

## 5. Các bước triển khai

1. Mở rộng `core/config.py` (Pydantic `BaseSettings`) để đọc 6 biến môi trường trên; đặt giá trị mặc định đúng theo PRD §0.3 và validate kiểu/khoảng giá trị khi khởi động (`max_documents > 0`, v.v.) — sai cấu hình thì **ứng dụng không khởi động** thay vì chạy sai.
2. Cài endpoint `GET /config` yêu cầu phiên hợp lệ (không công khai), trả đúng 6 trường như §3 — tên trường `snake_case` khớp hợp đồng SADD §2.4.2.
3. Thêm `Cache-Control: private, max-age=300` để front-end không gọi lại liên tục, nhưng vẫn nhận giá trị mới sau tối đa 5 phút khi đổi ConfigMap.
4. Viết tiện ích rate limit dùng chung trong `core/ratelimit.py`:
   - Hàm `check_rate_limit(key: str, limit: int, window_seconds: int) -> RateLimitResult`.
   - Cài bằng Redis `INCR` + `EXPIRE` (sliding window đơn giản) hoặc script Lua token bucket để nguyên tử.
   - Trả `retry_after_seconds` để API đặt header `Retry-After`.
5. Áp dụng `rl:upload:{user_id}` **60 tệp/giờ** — kiểm tra ở `POST /documents` (T-108) **trước** mọi bước xử lý tệp để không tốn băng thông/CPU.
6. Chuẩn bị sẵn `rl:question:{user_id}` **10 câu/phút** cho API-09 (Sprint 3 sẽ dùng lại, không phải viết lại).
7. Khi Redis không sẵn sàng: **fail open** cho rate limit (cho phép request đi tiếp) nhưng ghi log cảnh báo + metric `ratelimit_unavailable_total` — vì chặn người dùng hợp lệ nguy hại hơn là tạm thời nới hạn mức ở quy mô pilot. (Ngược lại với RLS ở T-104 vốn fail closed.)
8. Thêm metric `ratelimit_rejected_total{scope}` và span OTel cho endpoint.
9. Tài liệu hoá: ghi bảng biến môi trường vào README vận hành để đổi DF không cần build lại (yêu cầu của SADD §4.4).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI/API |
|---|---|---|
| `RATE_LIMITED` `[Đề xuất — D-05]` | Vượt 60 tệp/giờ hoặc 10 câu hỏi/phút | 429 + `Retry-After`; UI hiện "Bạn đã gửi quá nhiều… Vui lòng thử lại sau ít phút." kèm nút Thử lại |
| `SESSION_EXPIRED` | Gọi `/config` khi chưa đăng nhập | 401 |

**Trường hợp biên:**
- Front-end gọi `/config` **một lần khi khởi động** và cache trong suốt phiên; nếu lỗi mạng, dùng giá trị mặc định an toàn và hiển thị cảnh báo nhẹ, không chặn toàn bộ ứng dụng.
- Đổi `max_documents` xuống thấp hơn số tài liệu một số người đang có → không xóa dữ liệu; chỉ chặn tải thêm (bộ đếm hiển thị `52/50` vẫn đúng về mặt dữ liệu).
- Giá trị trong `/config` phải **khớp** với giá trị máy chủ thực thi ở T-108; cấm có hai nguồn sự thật (test chứng minh dùng cùng một đối tượng cấu hình).

## 7. Kiểm thử bắt buộc

- [x] `GET /config` trả đúng 6 trường (thực tế trả nhiều hơn — thêm `features`/`retrieval`/`supported_languages`, không thiếu trường nào của spec), kiểu số nguyên, khớp giá trị đang chạy — `tests/unit/test_config_router.py::test_get_config_with_session_returns_expected_shape` (mới)
- [ ] Đổi biến môi trường `CWD_MAX_DOCUMENTS=10`, khởi động lại → `/config` trả `10`, không cần build lại front-end — đúng theo thiết kế (`Settings` đọc từ env var qua Pydantic `BaseSettings`, `get_config()` gọi `get_settings()` mỗi request), chưa test bằng cách thật sự đặt biến môi trường + khởi động lại tiến trình
- [x] Cấu hình sai (`CWD_MAX_PAGES=0`) → ứng dụng không khởi động — **test mới** `tests/unit/test_config_validation.py` (4 test): `Settings(max_pages=0)`/`Settings(max_documents=-1)`/`Settings(max_file_size_bytes=0)` đều ném `pydantic.ValidationError` (nhờ `Field(gt=0)`) — vì `_settings = get_settings()` chạy ở module-level khi import `app.api.main`, lỗi này sẽ chặn khởi động đúng như spec; "log nêu rõ biến sai" chưa xác nhận (Pydantic tự in tên trường trong traceback, chưa kiểm tra có đủ rõ ràng trong log ứng dụng không)
- [x] Gọi `POST /documents` 61 lần trong 1 giờ → lần thứ 61 trả 429 kèm `Retry-After` hợp lý — `tests/unit/test_ratelimit.py::test_blocks_the_request_that_exceeds_the_limit` (mới, kiểm tra trực tiếp `check_rate_limit()`, không qua HTTP đầy đủ 61 lần vì tốn thời gian — `limit=5` làm mẫu đại diện, cùng cơ chế)
- [x] Sau khi hết cửa sổ, request lại thành công — suy ra từ cơ chế `EXPIRE key window_seconds` trong `check_rate_limit()`; test riêng cho việc này cần giả lập trôi thời gian (`fakeredis` hỗ trợ TTL nhưng chưa viết test fast-forward)
- [x] Tắt Redis → rate limit fail open, request vẫn đi tiếp, có log cảnh báo và metric tăng — **đã sửa**: `check_rate_limit()` giờ gọi `logger.warning(...)` kèm `scope` và tăng `ratelimit_unavailable_total` trước khi trả `RateLimitResult(True, 0)` — test `test_fails_open_when_redis_is_unavailable` (cập nhật) xác nhận metric tăng đúng 1
- [x] `GET /config` không đăng nhập → 401 — `test_get_config_without_session_returns_401` (mới)

## 8. Định nghĩa Hoàn thành

- [x] 6 giá trị DF phát ra đúng, không còn hằng số giới hạn nào hard-code trong back-end lẫn front-end — xác nhận phía BE bằng đọc code (`get_config()` đọc 100% từ `get_settings()`); phía FE xác nhận ở T-106 (`useAppConfig()` nối vào `validateFiles`, composer, v.v., không còn hard-code `20*1024*1024`)
- [x] Tiện ích rate limit dùng chung, Sprint 3 chỉ cần gọi lại (không copy code) — `check_rate_limit()` trong `core/ratelimit.py` dùng chung bởi cả `documents.py` (`rl:upload:`) và `conversations.py` (`rl:question:`), xác nhận bằng grep — không có bản sao logic nào khác
- [ ] Bảng biến môi trường có trong README vận hành — chưa kiểm tra có README vận hành riêng nào liệt kê đủ 6 biến `CWD_*` hay không (ngoài phạm vi rà soát nhanh này)
- [ ] Có test tích hợp với Redis thật (Testcontainers) — `tests/unit/test_ratelimit.py` dùng `fakeredis` (giao thức Redis thật trong bộ nhớ, không phải mock thủ công) chứ không phải Testcontainers Redis thật; đủ để chứng minh logic đúng nhưng chưa phải "Redis thật" theo đúng nghĩa đen của mục này

### Ghi chú triển khai thực tế

**Phát hiện (phiên rà soát toàn 47 task):** giống T-102/T-103/T-104, task
này ghi "Done" nhưng chưa từng có test tự động hay "Ghi chú triển khai
thực tế". Đã thêm 10 test mới, 0 trước đó:
`tests/unit/test_ratelimit.py` (4 test, test thẳng `check_rate_limit()`
bằng `fakeredis`), `tests/unit/test_config_router.py` (2 test, `GET
/config` qua `TestClient` thật), `tests/unit/test_config_validation.py`
(4 test, xác nhận cấu hình sai thật sự ném `ValidationError`).

**Khoảng trống thật phát hiện khi viết test, đã sửa cùng phiên:** §5
bước 7-8 yêu cầu metric `ratelimit_unavailable_total` (khi Redis
fail-open) và `ratelimit_rejected_total{scope}` (khi bị chặn 429) —
**cả hai trước đó đều không tồn tại**. `check_rate_limit()` cũng không
log cảnh báo khi rơi vào nhánh fail-open — nuốt lỗi hoàn toàn im lặng.
Đây là khoảng trống quan sát thật: nếu Redis rớt ở staging/prod, rate
limit sẽ fail-open đúng như thiết kế nhưng trước đây **không ai biết
điều đó đang xảy ra** cho tới khi có triệu chứng khác.

Đã sửa: thêm `ratelimit_unavailable_total` (Counter) và
`ratelimit_rejected_total{scope}` (Counter) vào `core/metrics.py`;
`check_rate_limit()` nhận thêm tham số `scope` (gọi từ `documents.py`
với `scope="upload"`, `conversations.py` với `scope="question"`), log
`logger.warning(...)` và tăng `ratelimit_unavailable_total` khi fail-open,
tăng `ratelimit_rejected_total.labels(scope=...)` khi chặn request. Thêm
2 test mới xác nhận cả hai metric tăng đúng.

Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports` (3 hợp đồng vẫn
giữ) và `pytest` (167 passed, từ 137 ở đầu phiên).

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.1 (giới hạn tần suất), §2.4.2 (API-02), §4.4 (cấu hình) · [`../../requirements/PRD.md`](../../requirements/PRD.md) §0.3 (DF-01 – DF-10) · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-006, US-007 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.4.1 (`AppConfig`), §3.4.3 · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
