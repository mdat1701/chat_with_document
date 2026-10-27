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
| Trạng thái | To do |

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

- [ ] Trên staging với `retention_days` rút ngắn còn vài phút: tài liệu tự động bị xóa; sau đó hỏi câu liên quan → `not_found`, không trích dẫn (AC-021.1, **bằng chứng cho G-05**).
- [ ] Sau khi purge: không còn hàng `chunk` nào của tài liệu đó; object đã bị xóa khỏi storage.
- [ ] Chạy `purge_expired` hai lần liên tiếp → lần hai không lỗi, không xóa nhầm tài liệu còn hạn (idempotent).
- [ ] Đặt thủ công một tài liệu `status='processing'` với `uploaded_at` 15 phút trước → `reap_stuck` chuyển sang `failed`/`INGESTION_FAILED` và UI nhận sự kiện SSE.
- [ ] Tạo object mồ côi cũ 25 giờ → bị dọn; object mồ côi mới 1 giờ → **không** bị dọn.
- [ ] Chạy hai worker song song → không lỗi khóa, không xóa trùng (`SKIP LOCKED`).
- [ ] Log của cả ba job không chứa tên tệp hay nội dung (P-03).

## 8. Định nghĩa Hoàn thành

- [ ] Ba job chạy đúng lịch trên staging, có log chứng minh.
- [ ] AC-021.1 có bằng chứng kiểm thử (ảnh chụp/log) để trình Pilot Gate **G-05**.
- [ ] `retention_days` đổi được qua cấu hình, không cần build lại (P-06).
- [ ] Use case xóa dùng chung với T-206 — không có hai đường xóa khác nhau.
- [ ] Rủi ro cửa sổ backup 7 ngày (AR-05) được ghi trong runbook và có quyết định D-04 (hoặc ticket chờ ATTT).

## 9. Tham chiếu

- SADD v0.3 §2.2.4 (bảng tác vụ nền), §3.2.3 (luồng xóa), §4.2.5 (retention & backup), AR-05, P-07
- User Stories v0.4 — US-021 (AC-021.1, AC-021.2), US-005 (`INGESTION_FAILED`)
- PRD v0.2 §0.3 (DF-05 = 90 ngày), §5.1 (Pilot Gate G-05)
- Kế hoạch: D-04 (chấp nhận cửa sổ backup), R-05
