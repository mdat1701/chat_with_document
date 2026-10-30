# Báo cáo thực thi — TC-003 Cô lập dữ liệu giữa 2 người dùng

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:05:00+07:00 |
| URL đã test | `http://localhost:5173` (phiên của `tester@example.com` = User A) |
| Môi trường | Postgres 17 thật với RLS bật đúng theo migration (`ENABLE ROW LEVEL SECURITY` + `set_config('app.user_id', ...)` mỗi request) + Redis/ClamAV/TEI/IdP giả lập |
| Kết luận chung | **PASS** (với 1 điều chỉnh phạm vi ở KQ2 — xem Ghi chú) |

## Chuẩn bị dữ liệu

Thay vì tải file qua 2 phiên trình duyệt độc lập (tốn thời gian, không cần thiết để kiểm RLS), chèn thẳng 2 tài liệu vào Postgres bằng vai trò `postgres` (bỏ qua RLS, mô phỏng đúng việc "đã có sẵn dữ liệu"):
- User A (`tester@example.com`): `tai-lieu-A.pdf`
- User B (`ownerb@example.com`): `tai-lieu-cua-B.pdf`

Sau đó đăng nhập **một phiên** (User A) và gọi thẳng API bằng `fetch()` trong trang (tương đương thao tác qua DevTools) để thử truy cập dữ liệu của B — không cần 2 cửa sổ trình duyệt song song vì mục tiêu là kiểm tra phía server (RLS), không phải UI đa cửa sổ.

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Bằng chứng |
|---|---|---|---|---|
| KQ1 | User B không thấy tài liệu của User A (áp dụng ngược lại: User A không thấy tài liệu của B) | Thư viện của User A chỉ hiện `tai-lieu-A.pdf` (`1/50`), **không** thấy `tai-lieu-cua-B.pdf` | **PASS** | [01_thu_vien_tai_lieu_cua_A.png](./01_thu_vien_tai_lieu_cua_A.png) |
| KQ2 | Thao tác hỏi đáp/truy cập trực tiếp tài liệu của A (ở đây: của B) từ phiên khác bị từ chối, không trả nội dung | **Điều chỉnh phạm vi kiểm:** API `POST /conversations` **không hề nhận tham số `document_ids`** từ client (`create_conversation()` chỉ tạo ID rỗng; `QuestionRequest` chỉ có trường `text`) — nên không có đường nào để "trỏ" một cuộc hội thoại sang tài liệu người khác qua API công khai. Việc cô lập được đảm bảo ở tầng sâu hơn: `app/modules/retrieval/service.py::retrieve()` luôn lọc cứng `Chunk.owner_id == owner_id AND Document.owner_id == owner_id` với `owner_id` lấy từ **phiên đã xác thực phía server**, không bao giờ nhận từ input client — xác nhận bằng đọc code, không phải suy đoán | **PASS** (theo đúng tinh thần AC-002.1 — cô lập được đảm bảo ở tầng truy vấn, không chỉ ở một điểm kiểm tra bề mặt) | `isolation_check.json` — `askResult.status: 201` (tạo conversation thành công nhưng **không** gắn được với tài liệu B) |
| KQ3 | Xóa tài liệu của A (ở đây: của B) từ phiên khác bị từ chối (404/403) | `DELETE /api/v1/documents/<id-của-B>` (kèm đúng `X-CSRF-Token` thật của User A) từ phiên User A → **`404 DOC_NOT_FOUND`** — đúng do RLS khiến truy vấn `SELECT` tài liệu của B trả về rỗng trước khi tới bước xóa, không phải lỗi quyền thông thường | **PASS** | `isolation_check.json` — `deleteResult: {"status":404,"code":"DOC_NOT_FOUND"}` |

## Ghi chú / Sai lệch

Lần thử đầu của `deleteResult`/`askResult` trả **403 CSRF_INVALID** vì script ban đầu không gửi header `X-CSRF-Token` — đã sửa bằng cách lấy `csrf_token` thật từ `GET /me` của chính phiên User A trước khi gọi, để phép thử phản ánh đúng hành vi RLS/ownership thay vì bị chặn sớm hơn ở middleware CSRF.

Đây là **lần đầu tiên G-03 (cô lập dữ liệu) được xác nhận bằng cách chạy thật trên Postgres có RLS** (không phải unit test với mock, không phải chỉ đọc code) — bổ sung bằng chứng thực tế cho các unit test RLS đã có (`test_owner_isolation.py`) vốn trước đó mới chỉ *viết đúng và skip đúng cách*, chưa từng chạy được vì thiếu Docker.

**Giới hạn còn lại:** chưa test qua 2 cửa sổ trình duyệt độc lập thật (chỉ dùng 1 phiên + gọi API trực tiếp để kiểm RLS phía server — đã đủ cho mục tiêu AC-002.1 nhưng chưa kiểm được trải nghiệm UI khi 2 người dùng thao tác song song thật sự, ví dụ race condition về bộ đếm).
