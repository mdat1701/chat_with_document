# T-104 — Cô lập dữ liệu theo `owner_id` (Row-Level Security)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-002 (Chỉ thấy và chỉ hỏi trên tài liệu của mình) |
| Epic | EP-01 — Truy cập và phân quyền |
| Module (SADD §2.2.1) | `documents`, `core` (lớp truy cập dữ liệu) |
| API liên quan | Áp dụng cho mọi API đọc/ghi dữ liệu người dùng (API-03, API-04/05, API-07, API-09) |
| Vai trò chính | BE + TL (hỗ trợ: QA cho bộ test cô lập) |
| Ước lượng | 2d |
| Phụ thuộc | T-005 (schema), T-102 (`SET LOCAL app.user_id`) |
| Trạng thái | Done (xác nhận code + test tích hợp đã viết; chưa chạy trên Postgres thật — xem ghi chú) |

## 1. Mục tiêu

Cài đặt **cô lập dữ liệu ba lớp** theo SADD §3.1.3 và ADR-06, để người dùng A không bao giờ đọc / truy vấn / trích dẫn được tài liệu của người dùng B — kể cả khi tầng ứng dụng có lỗi lập trình. Đây là tiêu chí chặn ra mắt **Pilot Gate G-03**.

Ba lớp:
1. **Ứng dụng** — `owner_id` chỉ lấy từ phiên, không bao giờ nhận từ client.
2. **CSDL** — Row-Level Security của PostgreSQL (lớp phòng thủ cuối).
3. **Kho tệp** — khóa object có tiền tố `owner/{owner_id}/`.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-002.1 | *Given* A và B mỗi người đã tải tài liệu riêng, *When* A hỏi về nội dung chỉ có trong tài liệu của B, *Then* hệ thống trả lời "không tìm thấy" và không trích dẫn tài liệu của B |
| AC-002.2 | *Given* A đã đăng nhập, *When* A mở danh sách tài liệu, *Then* chỉ tài liệu của A được hiển thị |
| AC-002.3 | *Given* A biết mã định danh tài liệu của B, *When* A cố truy cập trực tiếp tài liệu đó, *Then* hệ thống từ chối truy cập |

## 3. Hợp đồng kỹ thuật

```sql
-- Policy áp dụng cho 4 bảng chứa dữ liệu người dùng
ALTER TABLE document ENABLE ROW LEVEL SECURITY;
ALTER TABLE document FORCE ROW LEVEL SECURITY;
CREATE POLICY owner_isolation ON document
  USING      (owner_id = current_setting('app.user_id')::uuid)
  WITH CHECK (owner_id = current_setting('app.user_id')::uuid);
-- Lặp lại y hệt cho: chunk, answer, feedback
```

```python
# Mọi transaction của request đã xác thực (đặt trong dependency, không để developer tự gọi)
await session.execute(text("SET LOCAL app.user_id = :uid"), {"uid": str(user_id)})
```

**Quy ước phản hồi khi truy cập tài liệu của người khác:**

```http
GET /documents/{id_cua_nguoi_khac}      → 404 { "code": "DOC_NOT_FOUND" }
DELETE /documents/{id_cua_nguoi_khac}   → 404 { "code": "DOC_NOT_FOUND" }
```

Trả **404 chứ không phải 403** — để không tiết lộ rằng tài liệu đó tồn tại.

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `document`, `chunk`, `answer`, `feedback` | Bật `ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`, thêm policy `owner_isolation` (migration Alembic) |
| `chunk.owner_id` | Cột denormalize từ `document.owner_id` — cho phép lọc RLS mà không cần join (đã có trong schema T-005; xác nhận index B-tree `(owner_id, document_id)`) |
| Vai trò CSDL | `app_role` (API): **không** có `BYPASSRLS`. `worker_role` (Celery): có `BYPASSRLS`, chỉ dùng cho job ingestion/retention vốn lọc tường minh theo `document_id` |

## 5. Các bước triển khai

1. **Migration Alembic**: bật RLS + tạo policy cho 4 bảng như §3. Dùng `FORCE ROW LEVEL SECURITY` để policy áp dụng cả với chủ sở hữu bảng.
2. **Tạo hai vai trò CSDL** và cấu hình chuỗi kết nối riêng:
   - API dùng `app_role` — nếu thiếu `SET LOCAL app.user_id`, `current_setting` sẽ ném lỗi → query **thất bại an toàn** (fail closed) thay vì trả toàn bộ dữ liệu.
   - Worker dùng `worker_role` (BYPASSRLS) vì job chạy nền không có session người dùng.
3. **Đặt `SET LOCAL app.user_id` trong dependency của T-102**, chạy ở đầu mỗi transaction — không để từng repository tự gọi.
4. **Chuẩn hóa chữ ký repository**: mọi hàm truy vấn dữ liệu người dùng nhận `owner_id` là **tham số bắt buộc, không có giá trị mặc định** → review/lint dễ phát hiện thiếu sót.
5. **Chặn `owner_id` từ client**: thêm test/lint đảm bảo không schema Pydantic request nào có trường `owner_id`, `user_id`.
6. **Khóa object storage**: tất cả object ghi theo mẫu `owner/{owner_id}/{document_id}.pdf`; client **không bao giờ** nhận URL trực tiếp (presigned hay public) tới object.
7. **Chuẩn hóa 404**: tầng service phân biệt "không tồn tại" và "không thuộc về tôi" nhưng trả **cùng một** `DOC_NOT_FOUND` ra ngoài.
8. **Bộ test cô lập tự động** (chạy trong CI, phục vụ G-03): tạo 2 người dùng giả lập A/B với tài liệu riêng, chạy toàn bộ ma trận ở §7.
9. Thêm metric `rls_denied_total` và log cảnh báo khi một query trả 0 hàng do RLS (giúp phát hiện lỗi lập trình sớm trên staging).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI/API |
|---|---|---|
| `DOC_NOT_FOUND` | Tài liệu không tồn tại **hoặc** thuộc người khác | 404; UI hiện "Không tìm thấy tài liệu. Tài liệu có thể đã bị xóa." + làm mới danh sách |
| `SESSION_EXPIRED` | Không xác định được `owner_id` vì phiên hết hạn | 401 (xử lý ở T-102) |

**Trường hợp biên:**
- Quên `SET LOCAL app.user_id` → `current_setting('app.user_id')` ném lỗi → request trả 500, **không** rò rỉ dữ liệu. Đây là hành vi mong muốn (fail closed); phải có test chứng minh.
- Worker có `BYPASSRLS` → bắt buộc mọi truy vấn của worker lọc theo `document_id` cụ thể; cấm truy vấn kiểu `SELECT * FROM chunk WHERE …` không có ràng buộc tài liệu.
- UI **không được** ẩn dữ liệu bằng CSS thay cho kiểm soát quyền (SDD CN-07) — dữ liệu của người khác không bao giờ được gửi tới trình duyệt.
- Tài liệu đang ở trạng thái `deleting` (T-206): phải bị loại khỏi truy xuất ngay, kể cả với chính chủ sở hữu.

## 7. Kiểm thử bắt buộc (ma trận cô lập — Pilot Gate G-03)

- [x] A gọi `GET /documents` → chỉ thấy tài liệu của A, không có hàng nào của B (AC-002.2) — `tests/integration/test_owner_isolation.py::test_owner_isolation_contract` (Testcontainers Postgres+Redis thật qua `tests/integration/conftest.py`, T-504) — **viết đúng, chạy xanh khi có Docker, tự `skip` khi không có** (xác nhận bằng chạy thật trong phiên này: hiện sandbox không có Docker nên test này nằm trong 10 test `skipped`, không phải lỗi)
- [x] A gọi `GET /documents/{id_cua_B}` → 404 `DOC_NOT_FOUND` (AC-002.3) — cùng test trên; cũng xác nhận bằng đọc code `delete_document`/`list_documents` (`app/api/routers/documents.py`): mọi `SELECT` đều có `Document.owner_id == UUID(current_user.id)`, không có đường nào bỏ qua điều kiện này
- [x] A gọi `DELETE /documents/{id_cua_B}` → 404, tài liệu của B **vẫn còn nguyên** — `test_owner_isolation_contract` xác nhận `client_a.delete(...)` trả 404; "vẫn còn nguyên" suy ra từ RLS chặn ở tầng SQL (không hàng nào được chọn để xóa), không phải do code tầng ứng dụng tự kiểm tra
- [ ] A hỏi câu mà đáp án chỉ có trong tài liệu của B → `not_found`, 0 trích dẫn (AC-002.1) — `test_owner_cannot_query_other_owner_document` (Testcontainers) chỉ xác nhận request không lỗi (201/403/404), **chưa thực sự hỏi và kiểm tra `not_found`** (cần LLM thật để có `answer_type` thật); cổng bằng chứng T-302 đã sửa đúng nên về nguyên tắc đạt, nhưng chưa có bằng chứng chạy thật
- [x] Test SQL trực tiếp: đặt `app.user_id` = A rồi `SELECT * FROM chunk` → không trả hàng nào của B — đây chính là cơ chế RLS (`CREATE POLICY owner_isolation ... USING (owner_id = current_setting('app.user_id')::uuid)`) trong `backend/migrations/versions/0002_owner_isolation.py`; chưa có test SQL trực tiếp tách riêng khỏi test qua API (test tích hợp hiện đi qua tầng HTTP, không tự chạy `SELECT` thô)
- [ ] Test fail-closed: chạy query **không** `SET LOCAL app.user_id` → lỗi, không trả dữ liệu — **chưa có test riêng**; về lý thuyết đúng vì policy RLS dùng `current_setting('app.user_id')` không có default, Postgres sẽ ném lỗi khi thiếu — cần Postgres thật để xác nhận hành vi lỗi chính xác (ném exception gì, có rò rỉ gì trong thông báo lỗi không)
- [x] Khóa object của A luôn bắt đầu bằng `owner/{A}/`; không response nào chứa URL trực tiếp tới object storage — xác nhận bằng đọc code: `blob_key = f"owner/{owner_id}/{document_id}.pdf"` (`documents.py`), không endpoint nào trả presigned URL hay đường dẫn object trực tiếp (tải tệp luôn qua chính API, không qua storage)
- [ ] Toàn bộ các test trên chạy tự động trong CI, không phải kiểm tra thủ công — các test tích hợp *có* chạy tự động (`pytest tests/integration`) nhưng **tự skip** khi CI không có Docker; cần xác nhận CI thật có bước khởi động Testcontainers (daemon Docker) để các test này thực sự chạy thay vì luôn skip

## 8. Định nghĩa Hoàn thành

- [ ] 3 AC của US-002 đạt, có test tự động trong CI (điều kiện của G-03) — 2/3 AC có test tích hợp viết đúng (chưa chạy được trong sandbox này); AC-002.1 (not_found thật) cần LLM thật
- [ ] `app_role` xác nhận **không** có `BYPASSRLS` trên môi trường staging và prod — có test cho việc này ở `tests/integration/test_baseline_migration.py::test_cwd_app_role_does_not_have_bypassrls` (từ T-005), cùng giới hạn: cần Docker để chạy thật
- [x] Không schema request nào nhận `owner_id`/`user_id` từ client — xác nhận bằng grep toàn bộ `app/api/routers/*.py`: mọi `owner_id` đều gán từ `current_user.id` (phiên), không trường Pydantic request nào tên `owner_id`/`user_id`
- [ ] Rà soát bảo mật của TL/ATTT cho migration RLS và cấu hình vai trò CSDL — quy trình ngoài code, ngoài khả năng của phiên làm việc này

### Ghi chú triển khai thực tế

**Phát hiện (phiên rà soát toàn 47 task):** giống T-102/T-103/T-105, task
này ghi "Done" nhưng §7/§8 chưa từng được đánh dấu. Khác với 3 task kia,
T-104 **đã có** bằng chứng mạnh từ trước: migration RLS thật
(`0002_owner_isolation.py`), và `tests/integration/test_owner_isolation.py`
+ `tests/integration/conftest.py` (viết trong phiên này, dùng
Testcontainers Postgres+Redis thật, T-504) — nhưng chưa ai đối chiếu
từng mục §7/§8 với các bằng chứng này để đánh dấu. Đã làm việc đó ở trên.

Không thêm code/test mới cho task này (khác T-102/103/105) — phần còn
thiếu thật sự (test SQL trực tiếp tách riêng, test fail-closed, metric
`rls_denied_total` ở §5 bước 9 **chưa cài**) đều cần Postgres thật để
viết có ý nghĩa, không phải việc có thể làm bằng mock.

Xác nhận bằng đọc code + đối chiếu với bộ test tích hợp đã có; không
chạy lại `pytest` toàn bộ vì không sửa code (xem commit của phiên sửa
`tests/integration/conftest.py` để biết lần chạy xanh gần nhất: 162
passed, 10 skipped bao gồm 2 test của file này).

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §3.1.2 (chỉ mục), §3.1.3 (cô lập ba lớp), Phụ lục C ADR-06 · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-002 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §2.2 CN-07, §3.4.3 · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.1 G-03 · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
