# T-206 — Xóa tài liệu khỏi tập truy vấn

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-008 (Xóa một tài liệu) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `documents` (api) |
| API liên quan | **API-07** `DELETE /documents/{id}` |
| Vai trò chính | BE (UI xác nhận ở T-208) |
| Ước lượng | 2d |
| Phụ thuộc | T-104 (RLS/`owner_id`), T-203 (`chunk` đã tồn tại) |
| Trạng thái | To do |

## 1. Mục tiêu

Cho phép người dùng xóa tài liệu khỏi tập truy vấn một cách **dứt khoát và có thể kiểm chứng**: khi API trả `204`, tài liệu đã thực sự ra khỏi phạm vi trả lời — không còn được truy xuất hay trích dẫn (BR-005, hỗ trợ Pilot Gate G-05).

Vì **không có hoàn tác** (IX-04), UI **không dùng optimistic update** — chỉ xóa khỏi danh sách sau khi nhận `204` thật.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-008.1 | *Given* một tài liệu ở trạng thái bất kỳ, *When* người dùng nhấn "Xóa", *Then* hệ thống hiển thị hộp xác nhận ghi tên tệp. |
| AC-008.2 | *Given* người dùng đã xác nhận xóa, *When* thao tác hoàn tất, *Then* tài liệu biến mất khỏi danh sách, và các câu hỏi sau đó không còn trích dẫn tài liệu này. |
| AC-008.3 | *Given* người dùng nhấn "Hủy", *When* hộp đóng lại, *Then* tài liệu vẫn còn nguyên. |
| AC-002.3 | *Given* A biết mã định danh tài liệu của B, *When* A cố truy cập trực tiếp, *Then* hệ thống từ chối truy cập (**404**, không tiết lộ tồn tại). |

## 3. Hợp đồng API / giao diện

```http
DELETE /documents/{id}
Cookie: cwd_sid=...
X-CSRF-Token: <token từ GET /me>

→ 204 No Content        # chỉ trả SAU KHI chunk đã bị xóa và tài liệu ra khỏi phạm vi truy vấn
→ 401 { "code": "SESSION_EXPIRED" }
→ 403                    # thiếu/sai CSRF token
→ 404 { "code": "DOC_NOT_FOUND" }   # không tồn tại HOẶC thuộc người khác (không phân biệt)
```

**Quyết định thiết kế quan trọng:** tài liệu của người khác trả **404 `DOC_NOT_FOUND`**, *không* trả 403 — để không tiết lộ rằng tài liệu đó tồn tại (SADD §3.1.3, AC-002.3).

## 4. Thay đổi dữ liệu

| Bảng | Thao tác |
|---|---|
| `document` | `UPDATE … SET status='deleting'` → sau đó `DELETE` hàng |
| `chunk` | `DELETE FROM chunk WHERE document_id = :id` (xóa luôn vector và `tsv` vì cùng hàng) |
| Object storage | Xóa `owner/{owner_id}/{document_id}.pdf` **sau khi** commit |
| `audit_log` | Insert `action='document_deleted'`, `target_id=<document_id>`, **không** chứa tên tệp |

Bảng `answer` **không** bị xóa (chỉ chứa metadata, không nội dung) — giữ để tính chỉ số; không còn trỏ tới tài liệu nữa.

## 5. Các bước triển khai

Thứ tự dưới đây là bắt buộc (SADD §3.2.3) để `204` thực sự có nghĩa "đã ra khỏi phạm vi truy vấn":

1. Xác thực phiên + CSRF.
2. `SET LOCAL app.user_id` (T-104) rồi `SELECT … FROM document WHERE id = :id FOR UPDATE`.
   - Không có hàng (do không tồn tại **hoặc** RLS chặn vì thuộc người khác) → `404 DOC_NOT_FOUND`.
   - Đã ở `status='deleting'` → coi như thành công, trả `204` (idempotent).
3. `UPDATE document SET status='deleting'` và **commit ngay bước này** (hoặc dùng cùng transaction nhưng đảm bảo `retrieval` đọc được trạng thái mới) — kể từ đây, module `retrieval` (Sprint 3) **phải** loại tài liệu khỏi mọi truy vấn vector/FTS.
4. `DELETE FROM chunk WHERE document_id = :id` (có thể theo lô nếu tài liệu 300 trang/~600 đoạn).
5. `DELETE FROM document WHERE id = :id`.
6. Commit → trả **`204`**.
7. **Sau** response: xóa object trong storage (bất đồng bộ qua job `maintenance` hoặc gọi trực tiếp nhưng bọc try/except) — nếu lỗi, `blob.reconcile_orphans` (T-207) sẽ dọn sau ≤ 24 giờ.
8. Ghi `audit_log`; phát sự kiện analytics `document_deleted{trigger:'user'}` (T-404 chuẩn hóa allow-list).
9. Publish sự kiện SSE `status='deleting'` (hoặc để FE tự làm mới) để các tab khác của cùng người dùng đồng bộ.
10. **Tái sử dụng use case này cho retention** (T-207) — không viết hai luồng xóa khác nhau.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `DOC_NOT_FOUND` (404) | Tài liệu không tồn tại, đã bị xóa, hoặc thuộc người dùng khác | UI: "Không tìm thấy tài liệu. Tài liệu có thể đã bị xóa." + làm mới danh sách |
| `SESSION_EXPIRED` (401) | Phiên hết hạn | Chuyển `/login?returnTo=/` |
| — (403) | Thiếu `X-CSRF-Token` | Lỗi kỹ thuật, không hiển thị cho người dùng cuối (bug phía FE) |

Trường hợp biên:
- **Xóa tài liệu đang `processing`:** cho phép; worker phát hiện `status='deleting'` ở bước kế tiếp và thoát êm (T-201/T-203 đã xử lý).
- **Xóa trong lúc câu trả lời đang stream (NE-08):** bước kiểm tra trích dẫn ở `qa` (T-303) phải tra lại tài liệu và **loại bỏ trích dẫn trỏ tới tài liệu không còn tồn tại**.
- **Xóa tài liệu cuối cùng (ES-05):** UI về trạng thái trống nhưng **giữ nguyên hội thoại cũ** trên màn hình, chỉ khóa ô câu hỏi — xem [`SCR-02_18_last-document-deleted.png`](../../design/html_design/SCR-02_18_last-document-deleted.png).
- **Gọi DELETE hai lần liên tiếp:** lần hai trả `404` hoặc `204` (idempotent) — **không** 500.
- **Xóa thất bại ở bước object storage:** vẫn trả `204` (DB đã sạch); object mồ côi do job dọn.

## 7. Kiểm thử bắt buộc

- [ ] Xóa xong, hỏi lại câu mà đáp án chỉ có trong tài liệu đã xóa → nhận `not_found`, **không** trích dẫn tài liệu đó (AC-008.2; xác nhận đầy đủ sau Sprint 3).
- [ ] Sau `204`: `SELECT count(*) FROM chunk WHERE document_id=...` = 0 và hàng `document` không còn.
- [ ] Người dùng A gọi `DELETE` trên `document_id` của B → **404**, dữ liệu của B nguyên vẹn (AC-002.3, G-03).
- [ ] Gọi `DELETE` hai lần → không lỗi 500.
- [ ] Xóa tài liệu đang xử lý → worker thoát êm, không ghi chunk mồ côi.
- [ ] Giả lập lỗi xóa object → API vẫn trả `204`, object được dọn bởi `blob.reconcile_orphans`.
- [ ] Kiểm tra `audit_log` có bản ghi, **không** chứa tên tệp.

## 8. Định nghĩa Hoàn thành

- [ ] AC-008.1 – AC-008.3 đạt (UI xác nhận do T-208 hoàn thiện).
- [ ] `204` chỉ được trả sau khi chunk đã bị xóa — có integration test chứng minh thứ tự này.
- [ ] Use case xóa dùng chung được cho job retention (T-207) — không trùng lặp code.
- [ ] Hỗ trợ Pilot Gate G-05: có bằng chứng tài liệu đã xóa không còn truy xuất được.

## 9. Tham chiếu

- SADD v0.3 §2.4.2 (API-07), §3.2.3 (luồng xóa chi tiết), §3.1.3 (404 thay vì 403), §2.2.4 (`blob.reconcile_orphans`)
- User Stories v0.4 — US-008 (AC-008.1 – AC-008.3, ES-05, NE-08), US-002 (AC-002.3)
- SDD UI/UX v0.3 §3.4.3 (`DOC_NOT_FOUND`), §3.8.2 (xác nhận thao tác phá hủy, IX-04)
- PRD v0.2 §5.1 — Pilot Gate G-05
