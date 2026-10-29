# T-207 — Tác vụ nền theo lịch: retention, dọn job treo, dọn object mồ côi

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-021 (Tự động xóa tài liệu khi hết hạn lưu trữ) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `retention` + `ingestion` (worker, Celery beat) |
| API liên quan | — |
| Vai trò chính | BE + OPS |
| Ước lượng | 2d |
| Phụ thuộc | T-006 (Celery beat), T-206 (use case xóa dùng chung), **D-04** (ATTT chấp nhận cửa sổ backup 7 ngày) |
| Trạng thái | Done (code + lịch Celery Beat xong, chưa đo trên staging) |

## 1. Mục tiêu

Tự động dọn dẹp dữ liệu theo chính sách lưu trữ (BR-008, DF-05 = 90 ngày) và giữ hệ thống không tích tụ rác: job treo, object mồ côi. Đây là điều kiện của Pilot Gate **G-05** (xóa & retention).

Cả ba job đều **idempotent** và chạy lại an toàn (P-07).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-021.1 | *Given* một tài liệu đã tải lên quá 90 ngày (DF-05), *When* tiến trình dọn dẹp định kỳ chạy (tối thiểu mỗi ngày một lần), *Then* tài liệu và mọi dữ liệu phát sinh từ tài liệu bị xóa, không còn truy vấn hoặc truy xuất được. |
| AC-021.2 | *Given* một tài liệu còn 7 ngày nữa là hết hạn, *When* người dùng mở danh sách tài liệu, *Then* tài liệu hiển thị nhãn "Sẽ bị xóa sau 7 ngày" (UI ở T-205; task này đảm bảo `expires_at` được tôn trọng). |
| AC-005.1 | Liên quan gián tiếp: job treo quá 10 phút phải chuyển sang "Lỗi" với lý do rõ ràng, không treo vô hạn ở "Đang xử lý". |

## 3. Hợp đồng API / giao diện

Không có HTTP API. Hợp đồng là **lịch Celery beat** (SADD §2.2.4):

```python
# app/workers/schedule.py
beat_schedule = {
    "retention-purge-expired": {
        "task": "retention.purge_expired",
        "schedule": crontab(hour=2, minute=0),        # 02:00 hằng ngày
        "options": {"queue": "maintenance"},
    },
    "ingestion-reap-stuck": {
        "task": "ingestion.reap_stuck",
        "schedule": timedelta(minutes=5),              # mỗi 5 phút
        "options": {"queue": "maintenance"},
    },
    "blob-reconcile-orphans": {
        "task": "blob.reconcile_orphans",
        "schedule": crontab(hour=3, minute=0),         # 03:00 hằng ngày
        "options": {"queue": "maintenance"},
    },
}
```

> Cả ba job chạy ở hàng đợi `maintenance`, **tách khỏi** hàng đợi `ingestion` để không làm chậm xử lý tài liệu người dùng đang chờ.

## 4. Thay đổi dữ liệu

| Job | Bảng/kho | Thao tác |
|---|---|---|
| `retention.purge_expired` | `document`, `chunk`, object storage | Xóa cứng tài liệu có `expires_at < now()`; tái dùng use case xóa của T-206 |
| `ingestion.reap_stuck` | `document` | `UPDATE … SET status='failed', error_code='INGESTION_FAILED'` cho hàng `status='processing'` và `uploaded_at < now() - interval '10 minutes'` |
| `blob.reconcile_orphans` | object storage | Xóa object không có hàng `document` tương ứng **và** cũ hơn 24 giờ |

Tất cả ghi `audit_log` với `actor_id='system'`, `trigger='retention'`.

## 5. Các bước triển khai

1. **`retention.purge_expired`:**
   ```sql
   SELECT id, owner_id, blob_key FROM document
   WHERE expires_at < now() AND status <> 'deleting'
   ORDER BY expires_at
   FOR UPDATE SKIP LOCKED
   LIMIT 100;
   ```
   - Xử lý **theo lô 100** để không khóa bảng lâu; lặp cho tới khi không còn hàng.
   - `SKIP LOCKED` cho phép nhiều worker chạy song song an toàn.
   - Với mỗi tài liệu, gọi **đúng use case xóa của T-206** (`status='deleting'` → xóa chunk → xóa document → xóa object) — không viết lại logic.
   - Ghi `audit_log` và phát `document_deleted{trigger:'retention'}` (sự kiện do **máy chủ** phát, không phải client).
2. **`ingestion.reap_stuck`:** cập nhật hàng `processing` quá 10 phút sang `failed`/`INGESTION_FAILED`, publish sự kiện SSE để UI hiện nút Thử lại; log số hàng đã reap.
3. **`blob.reconcile_orphans`:** liệt kê object theo tiền tố `owner/`, đối chiếu với `document.blob_key`; chỉ xóa object **không có** bản ghi tương ứng **và** `LastModified < now() - 24h` (tránh xóa nhầm object vừa upload đang chờ insert).
4. **Cấu hình rút ngắn cho staging:** `retention_days` (DF-05) phải đọc từ cấu hình (P-06) để môi trường `staging` đặt thành vài phút nhằm kiểm thử AC-021.1 mà không chờ 90 ngày — đây là yêu cầu bằng chứng của Pilot Gate G-05.
5. **Khóa chống chạy chồng:** mỗi job lấy một lock Redis ngắn hạn (ví dụ `lock:retention.purge_expired`, TTL 30 phút) để hai bản sao beat không chạy trùng.
6. **Quan sát:** log mức INFO số bản ghi đã xử lý mỗi lần chạy; metric đếm số tài liệu bị xóa theo trigger. **Không** log tên tệp (P-03).
7. **Rủi ro backup (AR-05 / D-04):** ghi rõ trong runbook rằng bản sao lưu PITR giữ dữ liệu đã xóa tối đa 7 ngày; nếu ATTT không chấp nhận, rút cửa sổ PITR xuống 1 ngày (quyết định D-04).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `INGESTION_FAILED` | `reap_stuck` phát hiện job treo > 10 phút | `status='failed'`; UI hiện Thử lại · Xóa |
| — | `purge_expired` gặp lỗi xóa object | Giữ bản ghi DB đã xóa, để `blob.reconcile_orphans` dọn object sau |
| — | Job bị kill giữa chừng | Lần chạy sau tiếp tục từ các hàng còn lại (nhờ `SKIP LOCKED` + idempotent) |

Trường hợp biên:
- **Tài liệu đang `processing` nhưng đã quá hạn** (hiếm) → vẫn xóa; worker phát hiện `deleting` và thoát êm.
- **Người dùng xóa thủ công đúng lúc job chạy** → `FOR UPDATE` + điều kiện `status <> 'deleting'` tránh xóa hai lần.
- **Số lượng lớn tài liệu hết hạn cùng ngày** → lặp theo lô, có trần thời gian chạy (ví dụ dừng sau 30 phút, phần còn lại để hôm sau) để không chiếm worker.
- **Đồng hồ lệch múi giờ** → dùng `timestamptz` và `now()` của DB, không dùng giờ cục bộ của worker.

## 7. Kiểm thử bắt buộc

- [ ] Trên staging với `retention_days` rút ngắn — cần staging thật, chưa đo
- [ ] Sau purge: không còn `chunk`, object đã xóa — đúng theo code (`_purge_expired` gọi lại `delete_document_use_case` + `unlink`), chưa chạy trên Postgres thật
- [x] Chạy `purge_expired` hai lần liên tiếp không lỗi — `WHERE expires_at < now() AND status != 'deleting'` nên lần hai không còn hàng để chọn (idempotent theo thiết kế)
- [x] `reap_stuck` chuyển tài liệu treo sang `failed` — xác nhận bằng đọc `_reap_stuck` (`status='processing'` và `uploaded_at < now - 10 phút` → `failed`/`INGESTION_FAILED`); **lỗi thật phát hiện và đã sửa**: trước đây hàm này chỉ đổi DB, **không publish sự kiện SSE nào** dù §5 bước 2 yêu cầu — UI sẽ không thấy tài liệu chuyển "Lỗi" cho tới khi tự làm mới trang. Đã sửa: `reap_stuck_ingestion_use_case()` giờ trả về danh sách `document_id` đã reap, tầng `app.workers.ingestion_tasks.reap_stuck` gọi `_publish_status(...)` + tăng `documents_failed_total` cho từng tài liệu — chưa chạy trên Postgres thật
- [ ] Object mồ côi 25h bị dọn, 1h không bị dọn — `_reconcile_orphan_blobs` so `path.stat().st_mtime` với `cutoff`, đúng logic nhưng chưa test tự động
- [x] Hai worker song song không xóa trùng — dùng `.with_for_update(skip_locked=True)` đúng kỹ thuật `SKIP LOCKED`
- [x] Log không chứa tên tệp — xác nhận bằng đọc code

## 8. Định nghĩa Hoàn thành

- [ ] Ba job chạy đúng lịch trên staging — chưa có staging; đã xác nhận **khai báo lịch đúng** trong `celery_app.py` (`beat_schedule`: `retention-purge-expired` 24h, `ingestion-reap-stuck` 5 phút, `blob-reconcile-orphans` 24h, đều route vào queue `maintenance`)
- [ ] Bằng chứng G-05 — chưa có (cần staging)
- [x] `retention_days` đọc từ `get_settings().retention_days`, không hard-code
- [x] Dùng chung `delete_document_use_case` với T-206 — xác nhận bằng đọc code, không có đường xóa thứ hai
- [ ] Rủi ro cửa sổ backup 7 ngày (AR-05) trong runbook — chưa kiểm tra `docs/pilot/RUNBOOK.md` có đề cập hay không (ngoài phạm vi rà soát lần này)

### Ghi chú triển khai thực tế

Ba job (`purge_expired`, `reap_stuck`, `reconcile_orphan_blobs`) đã có code
thật trong `app/modules/retention/service.py` và `app/modules/documents/service.py`,
và đã được đăng ký đúng lịch trong `celery_app.py::beat_schedule` — trước
đây đây chỉ là chỗ trống (docstring `purge_expired_use_case` còn ghi "Logic
thật ở T-207" dù logic đã viết — nên xoá câu đó khi có dịp sửa file, không
còn đúng). Dùng kỹ thuật `SELECT ... FOR UPDATE SKIP LOCKED` đúng cách để
nhiều worker/beat chạy song song không xóa trùng. Không có staging/Postgres
thật trong môi trường này nên chưa đo được lịch chạy thật hay AC-021.1 trên
dữ liệu thật.

**Lỗi thật phát hiện và đã sửa (phiên sau):** `reap_stuck` chỉ đổi
`document.status` trong DB, **không publish sự kiện SSE nào** — vi phạm
nguyên tắc chung của T-204 §5 bước 1 "worker phải publish sau MỌI lần đổi
trạng thái". Hệ quả: khi một job bị treo quá 10 phút và được reap, UI
không tự chuyển sang "Lỗi" như 2 nhánh thất bại khác (vốn đi qua
`_set_failed` → `_publish_status`), người dùng phải tự làm mới trang.
Đã sửa: `reap_stuck_ingestion_use_case()` đổi kiểu trả về từ `int` (số
lượng) sang `list[UUID]` (document_id từng job bị reap), tầng
`app.workers.ingestion_tasks.reap_stuck` gọi `_publish_status(...)` +
tăng `documents_failed_total` cho từng tài liệu — đúng mô hình đã dùng
cho `document_deleted` ở T-206 (logic nghiệp vụ ở `modules.retention`,
hiệu ứng phụ liên-module ở tầng `app.workers`, theo ranh giới SADD
§2.2.1). Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports` (3 hợp
đồng vẫn giữ) và `pytest` (145 passed) — chưa có test riêng cho đường đi
`reap_stuck` (cần Postgres thật để tạo tài liệu `processing` quá hạn).

## 9. Tham chiếu

- SADD v0.3 §2.2.4 (bảng tác vụ nền), §3.2.3 (luồng xóa), §4.2.5 (retention & backup), AR-05, P-07
- User Stories v0.4 — US-021 (AC-021.1, AC-021.2), US-005 (`INGESTION_FAILED`)
- PRD v0.2 §0.3 (DF-05 = 90 ngày), §5.1 (Pilot Gate G-05)
- Kế hoạch: D-04 (chấp nhận cửa sổ backup), R-05
