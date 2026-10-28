# T-108 — API tải tài liệu lên (`POST /documents`)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-003 (tải 1 PDF), US-004 (nhiều PDF), US-006 (giới hạn tệp), US-007 (hạn mức tài liệu) |
| Epic | EP-02 — Quản lý tài liệu |
| Module (SADD §2.2.1) | `documents` |
| API liên quan | API-04/05 `POST /documents?on_duplicate=…` |
| Vai trò chính | BE |
| Ước lượng | 3d |
| Phụ thuộc | T-005 (schema `document`), T-102 (phiên + CSRF), T-104 (RLS), T-105 (cấu hình + rate limit), T-006 (hàng đợi Celery) |
| Trạng thái | In progress (code đầy đủ; 5 test tự động mới qua TestClient; AC-007.2 song song thật vẫn cần Postgres) |

## 1. Mục tiêu

Nhận tệp PDF tải lên, kiểm tra **mọi giới hạn ở phía máy chủ** (không tin kiểm tra của trình duyệt), ghi tệp vào object storage, tạo bản ghi `document` ở trạng thái `processing` và đẩy job ingestion. Điểm khó nhất là đảm bảo **không bao giờ vượt hạn mức DF-02 khi nhiều tệp tải lên song song** (AC-007.2).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-003.1 | Tải PDF có lớp văn bản ≤ 20 MB, ≤ 300 trang khi đang có < 50 tài liệu → xuất hiện trong danh sách với trạng thái "Đang xử lý" rồi "Sẵn sàng" |
| AC-004.1 | Chọn 10 tệp hợp lệ cùng lúc → cả 10 xuất hiện, mỗi tệp có trạng thái riêng |
| AC-004.2 | Trong 10 tệp có 1 tệp lỗi → 9 "Sẵn sàng", 1 "Lỗi"; tệp lỗi không ảnh hưởng tệp còn lại |
| AC-006.1 | Tệp đúng 20 MB (DF-01) → được chấp nhận |
| AC-006.2 | Tệp > 20 MB → từ chối (phía máy chủ trả 413 nếu client bỏ qua kiểm tra) |
| AC-007.1 | Đã đủ 50 tài liệu → từ chối với `QUOTA_EXCEEDED` |
| AC-007.2 | Có 48 tài liệu, gửi 5 tệp **cùng lúc** → đúng 2 tệp được nhận, 3 tệp bị từ chối |

## 3. Hợp đồng API

```http
POST /documents?on_duplicate=reject|replace|keep_both       # mặc định: reject
Cookie: cwd_sid=<sid>
X-CSRF-Token: <token>
Content-Type: multipart/form-data            # đúng MỘT trường "file"
Content-Length: <bắt buộc>

→ 201 {
    "id": "d41f…", "name": "HopDong_DoiTacA.pdf",
    "size_bytes": 3145728, "page_count": null,
    "status": "processing", "error_code": null,
    "uploaded_at": "2026-11-05T07:12:03Z",
    "expires_at":  "2027-02-03T07:12:03Z"
  }
→ 409 { "code": "DUPLICATE_NAME", "params": { "name": "HopDong_DoiTacA.pdf" } }
→ 413 { "code": "FILE_TOO_LARGE",  "params": { "max_mb": 20 } }
→ 415 { "code": "FILE_NOT_PDF" }
→ 422 { "code": "QUOTA_EXCEEDED",  "params": { "max": 50 } }
→ 429 { "code": "RATE_LIMITED",    "params": { "retry_after_seconds": 120 } }
→ 401 { "code": "SESSION_EXPIRED" } · 403 { "code": "CSRF_INVALID" }
```

```http
POST /documents/{id}/retry          # chỉ cho tài liệu failed với UPLOAD_NETWORK | INGESTION_FAILED
→ 202 Accepted
→ 409 { "code": "RETRY_NOT_ALLOWED" }
```

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `document` | INSERT `(id, owner_id, name, size_bytes, page_count=null, status='processing', blob_key, sha256, uploaded_at=now(), expires_at=now()+retention_days)` |
| `document` | Ràng buộc `UNIQUE (owner_id, lower(name))` phục vụ phát hiện trùng tên (ER-08) |
| `app_user` | `SELECT … FOR UPDATE` trên hàng của chủ sở hữu để khóa phần đếm hạn mức (không sửa dữ liệu) |
| Object storage | PUT object tại khóa `owner/{owner_id}/{document_id}.pdf`, SSE-KMS, bucket chặn truy cập công khai |
| Hàng đợi `ingestion` | Đẩy job `ingestion.process(document_id)` **sau khi** transaction commit |

## 5. Các bước triển khai — **thứ tự bắt buộc**

> Thứ tự này quyết định tính đúng của AC-006.2 và AC-007.2. Không được đảo.

1. **Ingress chặn sớm**: cấu hình `client_max_body_size 21m` ở Ingress NGINX — body lớn hơn bị chặn trước khi tới ứng dụng (tiết kiệm băng thông và CPU).
2. **Rate limit** (T-105): kiểm tra `rl:upload:{user_id}` (60 tệp/giờ) → vượt thì **429 `RATE_LIMITED`** kèm `Retry-After`, chưa đọc body.
3. **Kiểm tra `Content-Length`** ≤ `max_file_size_bytes` (DF-01): vượt → **413 `FILE_TOO_LARGE`**, **không đọc body**. Thiếu header `Content-Length` → 411/400.
4. **Kiểm tra magic bytes**: đọc 5 byte đầu của stream, so với `%PDF-`; sai → **415 `FILE_NOT_PDF`**, hủy, không ghi gì. (Bắt được tệp đổi đuôi `.pdf`.)
5. **Mở transaction** và thực hiện trong đúng thứ tự:
   a. `SELECT … FROM app_user WHERE id = :owner FOR UPDATE` — khóa hàng người dùng. Đây là điểm serialize các request song song.
   b. `SELECT count(*) FROM document WHERE owner_id = :owner AND status <> 'deleting'`; nếu `count >= max_documents` → rollback, **422 `QUOTA_EXCEEDED`**.
   c. Kiểm tra trùng tên theo `lower(name)`:
      - `on_duplicate=reject` (mặc định): trùng → rollback, **409 `DUPLICATE_NAME`**.
      - `replace`: đặt bản ghi cũ `status='deleting'` (luồng xóa thực thi ở T-206 dọn tiếp), rồi tiếp tục.
      - `keep_both`: đổi tên bản mới thành `name (2).pdf`; nếu `(2)` cũng trùng thì tăng dần `(3)`, `(4)`…
   d. Sinh `document_id` (UUID v4) và `blob_key = owner/{owner_id}/{document_id}.pdf`.
6. **Ghi tệp vào object storage theo stream**, vừa ghi vừa đếm byte thực tế và tính `sha256`. Nếu byte thực tế vượt DF-01 (client khai `Content-Length` gian dối) → hủy upload, xóa object dở, rollback, **413**.
7. **INSERT `document`** với `status='processing'`, `size_bytes` = số byte thực đếm được, `expires_at = uploaded_at + retention_days`.
8. **Commit transaction** → trả **201** với payload như §3.
9. **Sau commit**, đẩy job `ingestion.process(document_id)` vào hàng đợi `ingestion` (Celery). Thứ tự này tránh trường hợp worker nhận job trước khi hàng dữ liệu nhìn thấy được.
10. `POST /documents/{id}/retry`: chỉ chấp nhận khi `status='failed'` và `error_code ∈ {UPLOAD_NETWORK, INGESTION_FAILED}`; đẩy lại job, trả 202; các mã lỗi khác → 409 `RETRY_NOT_ALLOWED`.
11. **Dọn dẹp tải lên gián đoạn**: nếu kết nối đứt giữa chừng, **không** tạo bản ghi `document`; object dở dang sẽ được job `blob.reconcile_orphans` (T-207) xóa sau 24 giờ.
12. Thêm metric: `upload_total{outcome}`, `upload_bytes_total`, span OTel `documents.upload`. Log **không** ghi tên tệp (P-03) — chỉ `document_id` và `user_hash`.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI/API |
|---|---|---|
| `FILE_TOO_LARGE` | `Content-Length` hoặc byte thực tế > DF-01 | 413; UI: "Tệp vượt quá 20 MB. Hãy nén hoặc tách tệp rồi tải lại." |
| `FILE_NOT_PDF` | 5 byte đầu ≠ `%PDF-` | 415; UI: "Chỉ hỗ trợ tệp PDF." |
| `QUOTA_EXCEEDED` | Đã đạt DF-02 tài liệu | 422; UI: "Đã đạt tối đa 50 tài liệu. Xóa bớt tài liệu để tải thêm." |
| `DUPLICATE_NAME` | Trùng `lower(name)` và `on_duplicate=reject` | 409; UI mở `DuplicateFileDialog` (T-109) |
| `RATE_LIMITED` `[D-05]` | > 60 tệp/giờ | 429 + `Retry-After` |
| `UPLOAD_NETWORK` | Kết nối đứt khi đang truyền | Không tạo bản ghi; UI hiển thị dòng lỗi kèm **Thử lại** (trạng thái phía client) |

**Trường hợp biên:**
- Tệp **đúng** 20 MB (20 971 520 byte) phải **được nhận** — kiểm tra là `>` chứ không phải `>=` (AC-006.1).
- 5 request song song khi còn 2 chỗ: nhờ `FOR UPDATE` ở bước 5a, đúng 2 request nhận 201, 3 request nhận 422 — **không** có trường hợp 51 tài liệu.
- Tệp 0 byte → 415 (không phải PDF hợp lệ).
- Tên tệp chứa ký tự đặc biệt / đường dẫn (`../`) → chỉ lấy basename, chuẩn hóa Unicode NFC trước khi lưu; `blob_key` dùng UUID nên không phụ thuộc tên tệp.
- `page_count` **chưa biết** ở bước này (chỉ biết sau khi worker mở PDF ở T-201) → trả `null`, không đoán.

## 7. Kiểm thử bắt buộc

- [x] Tệp PDF hợp lệ → 201, `status='processing'`, có job trong hàng đợi `ingestion` (AC-003.1) — **test mới** `test_valid_pdf_upload_returns_201_and_enqueues_ingestion` (`tests/unit/test_documents_router.py`), qua `TestClient` thật + `AsyncSession`/Redis/queue giả lập
- [x] Tệp đúng 20 MB → 201 (AC-006.1); tệp 20 MB + 1 byte → 413 (AC-006.2) — kiểm tra `content_length` trước khi đọc; **test mới** `test_file_too_large_by_content_length_header_returns_413` xác nhận nhánh 413 qua header `Content-Length`
- [x] Tệp `.pdf` nhưng nội dung là PNG → `FILE_NOT_PDF` (415) — **test mới** `test_non_pdf_magic_bytes_returns_415`
- [x] Client khai `Content-Length` nhỏ hơn thực tế rồi gửi tệp lớn → bị chặn khi stream vượt `max_file_size_bytes`, rollback + xoá blob dở dang (xác nhận bằng đọc code; chưa test riêng nhánh "gian dối Content-Length" cụ thể)
- [ ] **Test song song thật** (asyncio/threading) cho AC-007.2 — **vẫn chưa viết**; đây là giới hạn thật của mock `AsyncSession` (không mô phỏng được ngữ nghĩa khóa `SELECT ... FOR UPDATE` của Postgres) — cần test tích hợp Testcontainers tương tự `tests/integration/conftest.py` (T-504) chạy nhiều coroutine `asyncio.gather` thật
- [x] Đã đủ 50 tài liệu → 422 `QUOTA_EXCEEDED` (AC-007.1) — **test mới** `test_quota_exceeded_returns_422`
- [x] `on_duplicate=reject/keep_both/replace` — cả 3 nhánh có trong `_unique_name()`; **test mới** `test_duplicate_name_reject_mode_returns_409` xác nhận nhánh `reject` (mặc định); `replace`/`keep_both` vẫn chỉ xác nhận bằng đọc code
- [x] Thiếu `X-CSRF-Token` → 403 (middleware `csrf_protection` trong `app/api/main.py`, áp dụng mọi `POST /api/v1/*`); phiên hết hạn → 401 (`get_current_user`)
- [x] Rate limit 60 tệp/giờ dùng `check_rate_limit` của T-105
- [ ] Ngắt kết nối giữa chừng → dọn object mồ côi — logic rollback tức thời có (`except: path.unlink(...)`), cơ chế `reconcile_orphan_blobs` (T-206) dọn định kỳ cũng tồn tại, nhưng **chưa có test tích hợp mô phỏng ngắt kết nối giữa chừng**
- [x] Log không chứa tên tệp — xác nhận bằng đọc code (không log `file.filename`/`name` ở mức info)

## 8. Định nghĩa Hoàn thành

- [ ] 7 AC ở §2 đạt về mặt code; 6/7 giờ có test tự động (chỉ AC-007.2 **chưa có test song song** chạy trong CI) — chưa đạt đủ điều kiện DoD vì thiếu đúng ca khó nhất
- [x] Mọi giới hạn đọc từ `get_settings()` (T-105), không hard-code — xác nhận bằng đọc code
- [x] Không có đường dẫn code nào ghi `document.owner_id` từ client — `owner_id` luôn lấy từ `current_user.id` (phiên)
- [x] Khóa object đúng tiền tố `owner/{owner_id}/{document_id}.pdf`, không trả URL trực tiếp — xác nhận bằng đọc code
- [ ] Metric/span OTel trên staging — chưa có staging thật để xác nhận

### Ghi chú triển khai thực tế

Toàn bộ router `app/api/routers/documents.py::upload_document` đã được kiểm
tra tĩnh sạch (`ruff check .`, `mypy app`, `lint-imports` — xem xác nhận
toàn backend ở README) và đọc thủ công khớp với mô tả §3/§5 của task này.

**Đã thêm (phiên này):** `tests/unit/test_documents_router.py` (5 test) —
đúng như đề xuất ở lần rà soát trước, dùng `TestClient` thật +
`dependency_overrides` cho `get_current_user`/`get_db_session`/`get_queue`,
`fakeredis` cho rate limit, và một `_SequentialSession` giả lập trả lần
lượt kết quả cho từng lệnh `AsyncSession.execute()` theo đúng thứ tự
`upload_document` gọi (owner FOR UPDATE → đếm hạn mức → kiểm tra trùng
tên). Phủ 5/7 ca ở §7: upload hợp lệ → 201 + enqueue, 415 sai magic byte,
422 hết hạn mức, 409 trùng tên (`on_duplicate=reject`), 413 theo header
`Content-Length`. Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports`
(3 hợp đồng vẫn giữ) và `pytest` (131 passed).

**Vẫn chưa làm (giới hạn thật của kỹ thuật mock, không phải thiếu thời
gian):** AC-007.2 (hạn mức dưới tải song song) cần ngữ nghĩa khóa
`SELECT ... FOR UPDATE` của Postgres thật — một `AsyncSession` giả lập
không thể mô phỏng việc 5 transaction đồng thời bị serialize bởi khóa
hàng. Cần test tích hợp Testcontainers (cùng hạ tầng với
`tests/integration/conftest.py`, T-504) chạy `asyncio.gather` với 5
request thật. Cũng chưa test riêng ca "ngắt kết nối giữa chừng" và nhánh
`replace`/`keep_both` của `on_duplicate`.

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (API-04/05, "Hành vi máy chủ của `POST /documents`"), §2.2.2 (pipeline ingestion), §3.1.1 – §3.1.2 (schema `document`, ràng buộc unique) · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-003, US-004, US-006, US-007 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.4.3, §3.5.1 · [`../../requirements/PRD.md`](../../requirements/PRD.md) §0.3 (DF-01 – DF-03) · Ảnh: [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png), [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
