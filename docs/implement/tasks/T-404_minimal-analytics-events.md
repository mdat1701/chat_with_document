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
| Trạng thái | To do |

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

- [ ] **AC-020.1 / canary test:** chuỗi canary không xuất hiện trong `analytics_event`, log (Loki) hay metric sau khi chạy trọn luồng
- [ ] Unit test allow-list: gửi `props` có khóa `question` → khóa bị loại, sự kiện vẫn ghi, có cảnh báo ở dev
- [ ] Không có sự kiện nào chứa `document_name`/`file_name` (test duyệt toàn bộ lược đồ đã khai báo)
- [ ] `user_hash` khác nhau giữa 2 người dùng và **không** đảo ngược được về `user_id` (kiểm tra bằng mắt + không lưu secret trong repo)
- [ ] Đủ 12 sự kiện của §3.2 được phát đúng thời điểm (test tích hợp theo phễu: `session_started` → `empty_state_viewed` → `document_upload_started` → `document_processing_succeeded` → `question_submitted` → `answer_rendered`)
- [ ] Ghi `analytics_event` lỗi (mock DB down) → luồng hỏi đáp vẫn trả lời bình thường
- [ ] Lint/kiểm tra ranh giới: không module nào ngoài `shared/analytics` gửi sự kiện (DR-05)

## 8. Định nghĩa Hoàn thành

- [ ] AC-020.1 có ca kiểm thử tự động chạy trong CI (canary test), không phải kiểm tra thủ công
- [ ] AC-020.2 có biên bản/email xác nhận của ATTT đính kèm hồ sơ Pilot Gate G-04
- [ ] `POST /events` được bổ sung vào SADD §2.4.2 (hoặc ghi rõ là endpoint nội bộ ngoài danh mục API-xx)
- [ ] Bảng `analytics_event` phân vùng theo tháng + job tạo phân vùng đã đăng ký
- [ ] **Không** có `mv_weekly_usage`, **không** đăng ký `analytics.rollup_daily` (xác nhận bằng rà soát code — giữ đúng ADR-09)
- [ ] Tài liệu một trang về danh mục sự kiện + allow-list đã bàn giao cho ATTT và PM

## 9. Tham chiếu

- [PRD §5.2 — Danh mục sự kiện và nguyên tắc quyền riêng tư](../../requirements/PRD.md) · §5.1 G-04
- [SADD §2.2.1 (`analytics`, `core`), §3.1.1 (`analytics_event`), §4.3, P-03, ADR-09, DR-05](../../requirements/SADD.md)
- [User Stories — US-020 (AC-020.1, AC-020.2)](../../design/User_Stories.md)
- [SDD UI/UX §3.8.4 — Đo lường theo thành phần](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 Sprint 4, §8.1 G-04](../implement_plan.md)
