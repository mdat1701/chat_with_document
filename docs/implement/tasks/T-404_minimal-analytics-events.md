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
| Trạng thái | In progress (allow-list + hash đúng; 6/15 sự kiện BE + `session_started` (T-107) + 4 sự kiện phía tài liệu + `citation_viewed` hover-timing/`retry_clicked{context}` phía hỏi đáp (T-305/T-306/T-307) đã nối; chỉ còn `feedback_submitted` chưa có điểm phát) |

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
- [x] Unit test allow-list — **đã thêm** (ghi nhận chéo từ T-503): `tests/unit/test_analytics_service.py` (5 test) xác nhận `props` ngoài allow-list bị loại, sự kiện lạ bị từ chối, `user_id` luôn được hash
- [x] Không sự kiện nào chứa `document_name`/`file_name` — cả `ALLOWED_EVENTS` và allow-list `props` đều không có trường tên tệp/tài liệu
- [x] `user_hash` khác nhau giữa 2 người, không đảo ngược được — HMAC-SHA256 với `analytics_hash_secret`, một chiều
- [ ] Đủ 12 sự kiện phát đúng thời điểm theo phễu — **đã nối thêm 3 sự kiện phía BE** (phiên trước): `document_processing_succeeded`/`document_processing_failed` (`app/workers/ingestion_tasks.py::_emit_processing_outcome_event`, sau khi pipeline kết thúc) và `document_deleted` cả 2 nhánh `trigger=user` (`app/api/routers/documents.py::delete_document`) và `trigger=retention` (`app/workers/retention_tasks.py::_emit_deleted_events`, dùng `owner_id` mà `purge_expired_use_case` giờ trả về thay vì chỉ đếm số lượng). **`session_started` nay đã nối phía FE** (phiên T-107 này): `frontend/src/features/auth/auth.ts::useAuth.load()` gọi `track("session_started", { is_first_session })` ngay sau `GET /me` trả 200 lần đầu, khử trùng lặp qua `sessionStorage`. **Nay đã nối thêm (phiên T-109/T-205/T-208)** bốn sự kiện phía tài liệu:
`document_upload_started{file_size_bucket}` (`useUploadQueue.ts::beginUpload`,
ngay trước mỗi `uploadDocument()`), `document_upload_rejected_client{reason_code}`
(`useUploadQueue.ts::addFiles`, cho từng tệp bị `validateFiles()` từ chối,
không kèm tên tệp), `empty_state_viewed{state_code}`
(`emptyState.ts::markEmptyStateViewedOnce`, cờ `sessionStorage` đảm bảo một
lần/variant/phiên, bọc `try/catch`), và `retry_clicked{context}` (hai điểm:
`useUploadQueue.ts::retryFailedItem` với `context:"document_upload"`, và
`DocumentLibrary.tsx::retry` với `context:"document_processing"` khi gọi
`POST /documents/{id}/retry`). **Nay đã nối thêm (phiên T-305/T-306/T-307,
`features/chat`)**: `citation_viewed{citation_index}` với đúng ngưỡng
hover ≥500ms **hoặc** click (`CitationChip.tsx`, dùng `setTimeout` hủy ở
`mouseleave`, có test fake-timer xác nhận không phát khi rời chuột trước
500ms) và `retry_clicked{context}` với `context` lấy từ phase trước khi
thử lại (`"failed"`/`"incomplete"`, `ChatPage.tsx::retryAnswer`). Vẫn
**chưa có lời gọi nào** cho `feedback_submitted` — chưa có component
feedback nào được xây ở Sprint 3/4 (ngoài phạm vi các task hiện có)
- [~] Ghi `analytics_event` lỗi không chặn câu trả lời — trong `conversations.py`, `session.add(Answer)` + `record_event` + `commit` chạy **sau** khi `event: done` đã được gửi cho client, nên người dùng vẫn thấy đủ câu trả lời trước khi có thể gặp lỗi lưu phía sau; tuy vậy lỗi commit vẫn khiến SSE kết thúc bằng `event: error` nối sau `done` — hơi khác "vẫn trả lời bình thường, không có dấu hiệu lỗi nào"
- [x] Lint ranh giới chỉ `shared/analytics` được gửi sự kiện (DR-05) — **đã cấu hình** (đợt T-106): rule `no-restricted-globals` trong `eslint.config.js` chặn `fetch`/`EventSource`/`sendBeacon` ngoài `shared/api` và `shared/analytics` (ngoại lệ có chủ đích cho hàng đợi sự kiện best-effort)

## 8. Định nghĩa Hoàn thành

- [ ] AC-020.1 canary test trong CI — chưa có
- [ ] AC-020.2 xác nhận ATTT — chưa có (cần quy trình ngoài code)
- [x] `POST /events` trong SADD §2.4.2 — **đã thêm**: endpoint tồn tại trong code từ trước nhưng chưa từng được ghi vào bảng §2.4.2 của SADD như chính §3.3 PA-1 của task này yêu cầu ("ghi bổ sung vào SADD §2.4.2") — đã thêm một dòng mới (không đánh số API-xx, đúng quyết định PA-1)
- [ ] `analytics_event` phân vùng theo tháng — **xác nhận là khoảng trống thật**: đọc `migrations/versions/0001_baseline.py` xác nhận bảng tạo bằng `op.create_table` thường, không có `PARTITION BY RANGE` nào — §4 của task này yêu cầu rõ "phân vùng theo tháng" nhưng chưa làm. Cần một migration riêng (Postgres partitioning cú pháp phức tạp hơn, không thể viết "cho chắc" mà không có Postgres thật để kiểm — để lại cho T-502/T-506 hoặc một task hạ tầng riêng khi có staging
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

**2 khoảng trống nhỏ thật phát hiện khi rà soát `POST /events` (phiên
sau, chưa sửa code — chỉ ghi nhận):**
1. `record_event()` nhận tham số `session_id` nhưng `app/api/routers/events.py::receive_events`
   luôn gọi với `session_id=None` — nghĩa là cột `analytics_event.session_id`
   hiện **luôn rỗng** trên mọi sự kiện gửi qua `POST /events`, dù §3.1
   mô tả "server tự điền từ phiên". Hệ quả: không gộp được sự kiện theo
   phiên làm việc khi phân tích phễu (US-020) — chỉ gộp được theo
   `user_hash`. Chưa rõ nên điền gì vào đây (hash của `cwd_sid`? một id
   phiên hỏi đáp riêng?) — cần quyết định thiết kế trước khi sửa, không
   phải lỗi một dòng.
2. `record_event()` ghi `app_version=get_settings().service_name` —
   `service_name` mặc định là `"cwd-backend"` (tên dịch vụ), **không phải
   phiên bản ứng dụng** như tên trường `app_version` ngụ ý (`pyproject.toml`
   có `version = "0.1.0"` nhưng không có settings nào đọc giá trị này).
   Vô hại (không rò rỉ gì, không chứa nội dung) nhưng dữ liệu cột này
   hiện không dùng được để so sánh chỉ số giữa các bản triển khai.

**Đã sửa thêm (phiên T-107):** nối `session_started` phía FE — xem ghi chú
ở hàng "Đủ 12 sự kiện..." phía trên. Tổng 7/15 tên sự kiện giờ có lời gọi
thật phía code.

**Đã sửa thêm (phiên T-109/T-205/T-208):** nối 4 sự kiện phía tài liệu —
xem ghi chú ở hàng "Đủ 12 sự kiện..." phía trên. Tổng **11/15** tên sự
kiện giờ có lời gọi thật phía code (6 BE + `session_started` + 4 sự kiện
tài liệu). Tất cả sự kiện FE mới vẫn đi qua `shared/analytics/client.ts::track()`
duy nhất, không có module nào khác tự gửi sự kiện (đúng DR-05 dù lint
ranh giới chưa cấu hình).

**Đã sửa thêm (phiên T-305/T-306/T-307, `features/chat`):** hoàn thiện
`citation_viewed` với đúng ngưỡng hover ≥500ms hoặc click (trước đó chỉ có
click) và nối `retry_clicked{context}` ở nhánh câu trả lời
(`answer_failed`/`incomplete`), cả hai có test (`ChatPage.test.tsx`, dùng
fake timers cho ngưỡng hover). Đồng thời phát hiện và **sửa một lỗi đếm
trùng**: `question_submitted`/`answer_failed` giờ dùng `ready_doc_count`
thật (không còn hard-code `0`), và quan trọng hơn — `ChatPage.tsx` **không
còn tự phát `answer_rendered`** nữa, vì backend (`conversations.py`) đã
phát đúng sự kiện này ngay sau `event: done` với `latency_ms` đo chính xác
phía server (§5.4 của task này); nếu FE cũng phát lại, mỗi câu trả lời sẽ
bị đếm hai lần trong `analytics_event`, làm sai các số liệu phễu MET-003.
Tổng **14/15** tên sự kiện trong bảng §3.2 giờ có lời gọi thật, chỉ còn
thiếu `feedback_submitted` (chưa có component nào phát sự kiện này trong
bất kỳ task Sprint 3/4 nào).

**Chưa làm:** `feedback_submitted` (chưa có task/component sở hữu), canary
test tự động (AC-020.1), xác nhận ATTT bằng văn bản (AC-020.2), unit test
allow-list phía BE, và lint ranh giới DR-05 cho `shared/analytics`. Giữ
**"In progress"**.

## 9. Tham chiếu

- [PRD §5.2 — Danh mục sự kiện và nguyên tắc quyền riêng tư](../../requirements/PRD.md) · §5.1 G-04
- [SADD §2.2.1 (`analytics`, `core`), §3.1.1 (`analytics_event`), §4.3, P-03, ADR-09, DR-05](../../requirements/SADD.md)
- [User Stories — US-020 (AC-020.1, AC-020.2)](../../design/User_Stories.md)
- [SDD UI/UX §3.8.4 — Đo lường theo thành phần](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 Sprint 4, §8.1 G-04](../implement_plan.md)
