# Báo cáo thực thi — TC-004 Tải lên 1 PDF hợp lệ, theo dõi trạng thái tới "ready"

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:22:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Postgres 17 thật + Redis giả lập (`fakeredis` TCP) + ClamAV giả lập + TEI giả lập; worker xử lý được mô phỏng bằng cách gọi thẳng `process_document.run()` (Celery thật không chạy được — `fakeredis` thiếu `EVALSHA`/Lua scripting mà Celery cần, xem Ghi chú) |
| Kết luận chung | **PASS** (KQ1/KQ2/KQ4 pass thật; KQ3 — cập nhật realtime không cần tải lại trang — không kiểm chứng được do giới hạn của stub, xem Ghi chú) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Tệp được chấp nhận vào hàng đợi ngay | `POST /api/v1/documents` trả `201`, tài liệu xuất hiện ngay với badge "⏳ Đang xử lý..." | **PASS** | [02_dang_xu_ly.png](./02_dang_xu_ly.png) |
| KQ2 | Thanh tiến trình chạy xong, dòng hàng đợi biến mất | Upload hoàn tất ngay (tệp nhỏ), chuyển thẳng sang mục trong danh sách tài liệu | **PASS** | [02_dang_xu_ly.png](./02_dang_xu_ly.png) |
| KQ3 | Badge trạng thái cập nhật realtime qua SSE, không cần F5 | **Không kiểm chứng được** — xem Ghi chú: `fakeredis` không chuyển tiếp message `PUBLISH`/`SUBSCRIBE` giữa 2 kết nối TCP khác nhau (đã tự kiểm chứng độc lập bằng script Python riêng), nên SSE không thể bắn tới trình duyệt trong môi trường thử nghiệm này | **KHÔNG XÁC ĐỊNH** (giới hạn hạ tầng test, không phải lỗi ứng dụng) | [03_sse_tu_cap_nhat_san_sang.png](./03_sse_tu_cap_nhat_san_sang.png) (cho thấy UI VẪN "Đang xử lý" dù DB đã "ready") |
| KQ4 | Bộ đếm tài liệu tăng đúng 1 | `3/50` sau khi tải — tăng đúng 1 so với trước (`2/50`) | **PASS** | [02_dang_xu_ly.png](./02_dang_xu_ly.png) |

## Xác nhận thêm: pipeline xử lý tài liệu hoạt động đúng (ngoài phạm vi SSE)

Sau khi gọi trực tiếp `process_document.run(document_id)` (mô phỏng Celery worker — xem Ghi chú), xác nhận bằng Postgres:
- `document.status` chuyển đúng từ `processing` → `ready`, `page_count=1`.
- Bảng `chunk` có đúng 1 dòng (văn bản đã trích xuất + chia đoạn + sinh embedding giả lập qua TEI stub).
- Tải lại trang (không qua SSE, chỉ fetch lại danh sách) → UI hiển thị đúng "Sẵn sàng · 1 trang" — xác nhận tầng binding dữ liệu đúng, vấn đề ở KQ3 chỉ nằm ở kênh đẩy realtime của môi trường thử nghiệm.

## Ghi chú / Sai lệch

**3 lỗi thật phát hiện và đã sửa trong lúc chạy ca này (không có lỗi nào là lỗi của bản thân pipeline nghiệp vụ — toàn bộ đều là lỗi hạ tầng/kết nối CSDL, chỉ lộ ra khi chạy thật bằng ORM trên Postgres thật, chưa từng bị unit test với DB giả bắt được):**

1. **`app/modules/documents/models.py`, `feedback/models.py`, `qa/models.py`**: các cột `Mapped[datetime]` không khai báo tường minh `DateTime(timezone=True)` — SQLAlchemy 2.0 mặc định hiểu là "không có múi giờ", lệch với cột Postgres thật (`TIMESTAMP WITH TIME ZONE`, đúng theo migration) và với giá trị `datetime.now(UTC)` (có múi giờ) mà code luôn tạo ra. Mọi `INSERT` qua ORM vào `document`/`feedback`/`answer` đều lỗi `"can't subtract offset-naive and offset-aware datetimes"`. Đã thêm `DateTime(timezone=True)` tường minh cho cả 5 cột liên quan.
2. **`app/core/config.py::Settings.worker_database_url_or_default()`**: dùng `str.replace("cwd:cwd_local_only@", "cwd_worker:cwd_worker_local_only@")` — chỉ đúng khi `DATABASE_URL` khớp **chính xác** chuỗi mặc định của `.env.example`. Với bất kỳ `DATABASE_URL` nào khác (kể cả dùng đúng vai trò `cwd_app` do migration tạo ra), hàm này **âm thầm trả nguyên** `database_url` — worker chạy nhầm bằng vai trò API (không `BYPASSRLS`), lỗi khó hiểu `"unrecognized configuration parameter app.user_id"`. Đã sửa bằng `sqlalchemy.engine.make_url()` để đổi đúng user/password bất kể giá trị gốc, thêm 3 unit test.
3. **(Nghiêm trọng nhất) `app/workers/ingestion_tasks.py::process_document` + `reap_stuck`, `app/workers/retention_tasks.py::purge_expired`**: cả 3 task Celery đều gọi **2 lệnh `asyncio.run()` tách rời** trong cùng một hàm (một cho use case chính, một cho phát sự kiện/SSE sau đó), cả hai cùng dùng chung một `AsyncEngine` singleton (`get_worker_engine()`). asyncpg bắt buộc một connection phải được dùng lại TRONG CHÍNH event loop đã tạo ra nó — lệnh `asyncio.run()` thứ hai mở một event loop MỚI rồi cố lấy lại connection đã pool từ event loop thứ nhất (đã đóng), vỡ ngay ở bước `pool_pre_ping` với lỗi `AttributeError: 'NoneType' object has no attribute 'send'`. **Hậu quả thật: mọi tài liệu xử lý thành công vẫn khiến Celery coi task là lỗi/thử lại ngay ở bước phát sự kiện phân tích cuối cùng** — tài liệu vẫn chuyển đúng sang `ready`, nhưng worker log lỗi/retry không cần thiết. Đã sửa cả 3 nơi bằng cách gộp thành **một** `asyncio.run()` duy nhất cho mỗi task.
4. **`app/workers/celery_app.py`**: không module task nào (`ingestion_tasks`, `retention_tasks`, ...) tự import `app.modules.identity.models` — cột `document.owner_id`/`answer.owner_id` tham chiếu `"app_user.id"` bằng chuỗi, SQLAlchemy chỉ phân giải được nếu bảng đó đã đăng ký trong cùng registry `Base.metadata`. Worker **thật** sẽ crash ngay ở `flush()` đầu tiên của bất kỳ task nào đụng bảng có FK sang `app_user` (gần như mọi task) với lỗi `NoReferencedTableError`. Đã thêm import đủ 5 file `models.py` vào `celery_app.py` (điểm nạp chung, giống hệt cách `migrations/env.py` đã làm).

Xác nhận toàn bộ 4 fix bằng `ruff check`, `mypy`, `lint-imports` (3 hợp đồng vẫn giữ), `pytest` (178 passed, 13 skipped — tăng 3 so với trước nhờ test mới cho mục 2, không có lỗi nào bị phá).

**Giới hạn còn lại:**
- Không chạy được Celery worker thật (do `fakeredis` thiếu hỗ trợ `EVALSHA`) — đã gọi thẳng hàm `process_document.run()` để mô phỏng, xác nhận đúng logic nghiệp vụ nhưng chưa xác nhận hành vi hàng đợi/retry/concurrency thật của Celery.
- KQ3 (SSE realtime) không kiểm chứng được do giới hạn `fakeredis` (không chuyển tiếp pub/sub giữa các kết nối) — cần Redis thật (Testcontainers/staging) để xác nhận.
