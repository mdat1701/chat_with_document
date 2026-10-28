# T-404 — Ghi sự kiện đo lường tối thiểu (không chứa nội dung)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 4 |
| Story | US-020 |
| Epic | EP-05 — Phản hồi và đo lường MVP |
| Module (SADD §2.2.1) | `analytics` (phần ghi sự kiện — **trong phạm vi**), `core` (bộ lọc nội dung) |
| API liên quan | Xem §3 — **cần bổ sung một endpoint nhận sự kiện từ client** (chưa có trong API-01 – API-09) |
| Vai trò chính | BE (chính) + FE + QA |
| Ước lượng | 2 ngày công |
| Phụ thuộc | T-007 (bộ lọc log `core`), T-304 (`answer_rendered`), T-204 (sự kiện tài liệu) |
| Trạng thái | In progress (allow-list + hash đúng; 6/15 sự kiện phía BE đã nối trong phiên này; sự kiện phía FE vẫn thiếu) |

## 1. Mục tiêu

Ghi **đủ** danh mục sự kiện tối thiểu của PRD §5.2 để tính được phễu kích hoạt và MET-003, đồng thời **chứng minh được** rằng không sự kiện nào chứa nội dung tài liệu, câu hỏi, câu trả lời hay tên tệp.

Đây là yêu cầu **trong phạm vi MVP-lite** (BRD §5.1). Phần **tổng hợp báo cáo tuần** (`mv_weekly_usage`, job `analytics.rollup_daily`, US-019) là **post-MVP — không làm trong task này**.

Task này là bằng chứng chính cho Pilot Gate **G-04 (Quyền riêng tư và AI)**.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-020.1 | Kiểm tra dữ liệu thô của **toàn bộ** sự kiện ở PRD §5.2 → không sự kiện nào chứa nội dung câu hỏi, nội dung câu trả lời, tên tệp hay đoạn trích từ tài liệu |
| AC-020.2 | ATTT rà soát log và metric vận hành → có **xác nhận bằng văn bản** rằng chúng không chứa nội dung tài liệu |

## 3. Hợp đồng API / giao diện

### 3.1 Thuộc tính chung (mọi sự kiện — PRD §5.2)

```jsonc
{
  "event_name": "answer_rendered",
  "timestamp":  "2026-12-20T03:14:07Z",
  "user_id_hash": "9f2c…",      // HMAC-SHA256(user_id, secret) — KHÔNG phải user_id thô
  "session_id": "…",
  "app_version": "0.4.1",
  "props": { /* chỉ các khóa trong allow-list của từng sự kiện */ }
}
```

### 3.2 Danh mục sự kiện và nguồn phát (SDD §3.8.4)

| Sự kiện | Phát từ | `props` được phép |
|---|---|---|
| `session_started` | `features/auth` sau khi `GET /me` thành công | `is_first_session` |
| `empty_state_viewed` | `EmptyState` (mỗi `variant` một lần/phiên) | `state_code` (ES-01…ES-05) |
| `document_upload_started` | `UploadDropzone` | `file_size_bucket` |
| `document_upload_rejected_client` | `UploadDropzone` | `reason_code` |
| `document_processing_succeeded` | Bộ xử lý SSE / worker | `page_count`, `duration_ms` |
| `document_processing_failed` | Bộ xử lý SSE / worker | `error_code` |
| `document_deleted` | `DeleteConfirmDialog` sau 204; `trigger=retention` do máy chủ phát | `trigger` (`user`\|`retention`) |
| `question_submitted` | `ConversationStore` | `question_length`, `language`, `ready_doc_count` |
| `answer_rendered` | `ConversationStore` | `latency_ms`, `answer_type`, `citation_count` |
| `answer_failed` | `ConversationStore` | `error_code` |
| `retry_clicked` | `ConversationStore` | `context` |
| `citation_viewed` | `CitationChip` (hover ≥ 500 ms hoặc nhấn) | `citation_index` |

> **Tuyệt đối không** có trường: nội dung câu hỏi, nội dung câu trả lời, `file_name`, đoạn trích, `document_name`.

### 3.3 Khoảng trống hợp đồng cần xử lý

SADD §2.4.2 liệt kê API-01 – API-09 và ghi *"API-10 trở đi … post-MVP"*, **nhưng không có endpoint nào để client gửi sự kiện**. Hai phương án, chọn **PA-1** cho MVP-lite:

| PA | Mô tả | Đánh giá |
|---|---|---|
| **PA-1 (chọn)** | Thêm endpoint nội bộ `POST /events` (không đánh số API-xx, ghi bổ sung vào SADD §2.4.2): nhận mảng sự kiện đã gom theo lô, trả `204` | Ít thay đổi, giữ được sự kiện phía client (`empty_state_viewed`, `citation_viewed`) |
| PA-2 | Chỉ phát sự kiện phía máy chủ; bỏ các sự kiện chỉ có ở client | Mất phễu kích hoạt, không tính được MET-003 đầy đủ |

```
POST /events        (yêu cầu phiên hợp lệ + X-CSRF-Token)
Body: { "events": [ { event_name, timestamp, props }, … ] }   // tối đa 20 sự kiện/lô
→ 204
→ 400 { code: "EVENT_INVALID" }   // sai lược đồ; server vẫn loại khóa lạ thay vì từ chối cả lô
```
`user_id_hash`, `session_id`, `app_version` do **máy chủ** điền từ phiên — client không được tự gửi.

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `analytics_event(id, name, ts, user_hash, session_id, app_version, props jsonb)` | Tạo bảng + **phân vùng theo tháng** (SADD §3.1.1) |
| Chỉ mục `(name, ts)` trên từng phân vùng | Phục vụ truy vấn tổng hợp |
| Job tạo phân vùng tháng kế tiếp | Thêm vào Celery beat (chạy hằng tháng), tránh lỗi insert khi sang tháng mới |
| Bí mật `ANALYTICS_HASH_SECRET` | Khóa HMAC cho `user_hash`, lưu qua secret manager, **không** nằm trong repo |

**Không** tạo `mv_weekly_usage` và **không** đăng ký job `analytics.rollup_daily` — đó là post-MVP (US-019).

## 5. Các bước triển khai

1. **`core` — allow-list dùng chung:** khai báo lược đồ cho từng sự kiện (tên sự kiện → tập khóa `props` hợp lệ + kiểu). Hàm `track(name, props)` **loại bỏ** mọi khóa không khai báo; ở môi trường `dev` thì **ghi cảnh báo** nêu tên khóa bị loại (DR-05).
2. **BE — endpoint `POST /events`:** xác thực phiên + CSRF, giới hạn 20 sự kiện/lô, **chạy lại allow-list phía máy chủ** (không tin client), rồi insert `analytics_event`.
3. **BE — `user_hash`:** `HMAC-SHA256(user_id, ANALYTICS_HASH_SECRET)`; tuyệt đối không ghi `user_id` thô hay email vào bảng.
4. **BE — sự kiện phía máy chủ:** phát trực tiếp (không qua endpoint) cho `document_processing_succeeded/failed` (worker), `document_deleted{trigger=retention}` (job retention), `answer_rendered`/`answer_failed` (nếu chọn ghi ở server để chính xác `latency_ms`).
5. **FE — `shared/analytics`:** module **duy nhất** được phép gửi sự kiện (DR-05). Gom lô theo thời gian (ví dụ 5 giây) hoặc khi đủ 20 sự kiện; dùng `navigator.sendBeacon` khi rời trang để không mất sự kiện cuối.
6. **FE — gắn sự kiện vào đúng thành phần** theo bảng §3.2 (SDD §3.8.4). `empty_state_viewed` chỉ phát **một lần mỗi `variant` mỗi phiên**.
7. **Bộ lọc log/metric (`core`, mở rộng từ T-007):** chặn cứng các trường `question`, `answer`, `content`, `text`, `file_name`, `prompt` ở **mọi** logger và mọi span OTel; trace chỉ ghi số token và độ trễ.
8. **Canary test (bằng chứng G-04):** viết test tự động nạp một tài liệu chứa chuỗi canary duy nhất (ví dụ `ZZCANARY7781`), chạy trọn luồng upload → hỏi → trả lời → xóa, rồi **quét toàn bộ** `analytics_event`, log và metric để khẳng định chuỗi canary **không xuất hiện ở đâu**.
9. Viết tài liệu một trang mô tả danh mục sự kiện + allow-list để ATTT ký AC-020.2.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Client gửi khóa lạ trong `props` | Máy chủ **loại khóa đó**, vẫn ghi sự kiện; ở dev ghi cảnh báo. Không trả lỗi cho người dùng |
| Client gửi `user_id_hash`/`session_id` tự chế | Máy chủ **ghi đè** bằng giá trị từ phiên |
| Lỗi khi ghi `analytics_event` | **Nuốt lỗi** — không bao giờ làm hỏng luồng nghiệp vụ; chỉ tăng metric `analytics_write_failures_total` |
| Mất mạng phía client | Sự kiện trong hàng đợi bị bỏ; **không** lưu sự kiện vào `localStorage` (CN-06) |
| Sang tháng mới chưa có phân vùng | Job tạo phân vùng chạy trước; thêm fallback tạo phân vùng khi insert lỗi lần đầu |
| Người dùng chưa đăng nhập | Không phát sự kiện nào (không có `user_hash` hợp lệ) |

## 7. Kiểm thử bắt buộc

- [ ] Canary test tự động — chưa có, mới xác nhận bằng đọc code
- [ ] Unit test allow-list — **0 test cho `app/modules/analytics/`**; logic đúng khi đọc: `props` ngoài allow-list bị loại (`rejected_props`), log cảnh báo, sự kiện vẫn ghi với `safe_props`
- [x] Không sự kiện nào chứa `document_name`/`file_name` — cả `ALLOWED_EVENTS` và allow-list `props` đều không có trường tên tệp/tài liệu
- [x] `user_hash` khác nhau giữa 2 người, không đảo ngược được — HMAC-SHA256 với `analytics_hash_secret`, một chiều
- [ ] Đủ 12 sự kiện phát đúng thời điểm theo phễu — **đã nối thêm 3 sự kiện phía BE trong phiên này**: `document_processing_succeeded`/`document_processing_failed` (`app/workers/ingestion_tasks.py::_emit_processing_outcome_event`, sau khi pipeline kết thúc) và `document_deleted` cả 2 nhánh `trigger=user` (`app/api/routers/documents.py::delete_document`) và `trigger=retention` (`app/workers/retention_tasks.py::_emit_deleted_events`, dùng `owner_id` mà `purge_expired_use_case` giờ trả về thay vì chỉ đếm số lượng). Vẫn **chưa có lời gọi nào** cho `session_started`, `empty_state_viewed`, `document_upload_started`, `document_upload_rejected_client`, `retry_clicked`, `feedback_submitted` — đây đều là sự kiện phát từ **phía FE** theo thiết kế (SDD §3.8.4), cần làm cùng T-106/T-109/T-205/T-208/T-307
- [~] Ghi `analytics_event` lỗi không chặn câu trả lời — trong `conversations.py`, `session.add(Answer)` + `record_event` + `commit` chạy **sau** khi `event: done` đã được gửi cho client, nên người dùng vẫn thấy đủ câu trả lời trước khi có thể gặp lỗi lưu phía sau; tuy vậy lỗi commit vẫn khiến SSE kết thúc bằng `event: error` nối sau `done` — hơi khác "vẫn trả lời bình thường, không có dấu hiệu lỗi nào"
- [ ] Lint ranh giới chỉ `shared/analytics` được gửi sự kiện (DR-05) — chưa cấu hình (xem T-106)

## 8. Định nghĩa Hoàn thành

- [ ] AC-020.1 canary test trong CI — chưa có
- [ ] AC-020.2 xác nhận ATTT — chưa có (cần quy trình ngoài code)
- [ ] `POST /events` trong SADD §2.4.2 — chưa kiểm tra tài liệu SADD có cập nhật hay chưa (ngoài phạm vi rà soát code)
- [ ] `analytics_event` phân vùng theo tháng — chưa kiểm tra migration có tạo partition hay chỉ bảng thường (cần xem `migrations/versions/0001_baseline.py` kỹ hơn)
- [x] Không có `mv_weekly_usage`/`analytics.rollup_daily` — xác nhận bằng grep, không tồn tại trong code (đúng ADR-09)
- [ ] Tài liệu 1 trang bàn giao ATTT/PM — chưa có

### Ghi chú triển khai thực tế

Lõi an toàn (allow-list tên sự kiện + allow-list thuộc tính + hash một
chiều `user_id`) đã cài đúng trong `app/modules/analytics/service.py` và
kiểm tra tĩnh sạch.

**Đã sửa (phiên này):** nối thêm 3 sự kiện phía BE — tổng 6/15 tên sự
kiện giờ có lời gọi thật (`question_submitted`, `citation_viewed`,
`answer_rendered` từ trước + `document_processing_succeeded/_failed`,
`document_deleted`). Lưu ý ranh giới module (SADD §2.2.1): không thể gọi
`record_event()` trực tiếp từ `app.modules.ingestion`/`app.modules.retention`
(sẽ vi phạm hợp đồng "không phụ thuộc vòng giữa module nghiệp vụ" vì
`analytics` không nằm trong `ignore_imports` cho phép của 2 module đó) —
nên việc phát sự kiện được đặt ở tầng `app.workers`/`app.api` (lớp adapter
được phép import mọi module), đúng nguyên tắc P-01. Vì vậy
`purge_expired_use_case()` đổi kiểu trả về từ `int` (số lượng) sang
`list[UUID]` (owner_id từng tài liệu đã xóa) để `retention_tasks.py` có
đủ thông tin phát `document_deleted{trigger=retention}` — đã kiểm tra
không còn lời gọi nào khác phụ thuộc kiểu `int` cũ (`grep` xác nhận).

Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports` (3 hợp đồng vẫn
giữ) và `pytest` (105 passed) — **không có test đơn vị mới riêng** cho
`_emit_processing_outcome_event`/`_emit_deleted_events` (cần mock
`worker_session_scope`/`AsyncSession` ở độ phức tạp tương đương test
tích hợp, để lại cho đợt viết test tích hợp Celery).

**Chưa làm (còn lại, thuộc FE):** `session_started`, `empty_state_viewed`,
`document_upload_started`, `document_upload_rejected_client`,
`retry_clicked`, `feedback_submitted` — đều phát từ phía client theo
thiết kế gốc, cần làm cùng các task FE liên quan. Giữ "In progress".

## 9. Tham chiếu

- [PRD §5.2 — Danh mục sự kiện và nguyên tắc quyền riêng tư](../../requirements/PRD.md) · §5.1 G-04
- [SADD §2.2.1 (`analytics`, `core`), §3.1.1 (`analytics_event`), §4.3, P-03, ADR-09, DR-05](../../requirements/SADD.md)
- [User Stories — US-020 (AC-020.1, AC-020.2)](../../design/User_Stories.md)
- [SDD UI/UX §3.8.4 — Đo lường theo thành phần](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 Sprint 4, §8.1 G-04](../implement_plan.md)
