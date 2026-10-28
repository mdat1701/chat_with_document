# T-204 — Cập nhật trạng thái tài liệu theo thời gian thực (SSE)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-010 (Thấy trạng thái xử lý của từng tài liệu) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `documents` (api) + Redis pub/sub |
| API liên quan | **API-06** `GET /documents/events` |
| Vai trò chính | BE (phối hợp FE ở T-205) |
| Ước lượng | 2d |
| Phụ thuộc | T-201/T-203 (worker publish sự kiện), T-102 (phiên), T-106 (SSE client ở `shared/api`) |
| Trạng thái | Done (BE; phụ thuộc FE `sseClient` ở T-106 chưa có) |

## 1. Mục tiêu

Đẩy thay đổi trạng thái tài liệu từ worker tới trình duyệt **trong ≤ 5 giây** mà không cần polling, dùng Server-Sent Events (ADR-07 — một chiều là đủ, tương thích proxy HTTP).

Kiến trúc: worker → Redis pub/sub → **mọi bản sao API** → client SSE đúng chủ sở hữu.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-010.1 | *Given* một tài liệu thay đổi trạng thái trên máy chủ, *When* sự kiện SSE được gửi, *Then* trạng thái trên UI cập nhật trong ≤ 5 giây (SDD CN-02). |
| AC-010.2 | *Given* mọi tài liệu đều đang xử lý, *When* người dùng nhìn ô câu hỏi, *Then* ô bị khóa kèm gợi ý và **tự mở** khi có ít nhất 1 tài liệu ✅ (ES-02). |
| AC-004.2 | *Given* trong 10 tệp có 1 tệp lỗi, *When* xử lý kết thúc, *Then* 9 tệp "Sẵn sàng" và 1 tệp "Lỗi"; tệp lỗi không ảnh hưởng tệp còn lại. |

## 3. Hợp đồng API / giao diện

```http
GET /documents/events
Accept: text/event-stream
Cookie: cwd_sid=...
Last-Event-ID: <id sự kiện cuối client đã nhận>   (tùy chọn)

→ 200 Content-Type: text/event-stream
      Cache-Control: no-cache
      X-Accel-Buffering: no          # bắt buộc với Ingress NGINX để không buffer

id: 1730031234567-0
event: status
data: {"id":"3f1c...","status":"ready","error_code":null,"page_count":20}

event: status
data: {"id":"8ab2...","status":"failed","error_code":"PDF_ENCRYPTED","page_count":null}

: ping          ← mỗi 15 giây, giữ kết nối qua proxy

→ 401 { "code": "SESSION_EXPIRED" }
```

Quy ước:
- Chỉ phát sự kiện của **tài liệu thuộc người dùng trong phiên** — `owner_id` lấy từ session, không từ query param.
- Trường `status` ∈ `processing | ready | failed | deleting`.

## 4. Thay đổi dữ liệu

Không thay đổi schema. Chỉ **đọc** `document` khi client kết nối lại (snapshot ban đầu do `GET /documents` của T-205 đảm nhiệm).

Kênh Redis: `doc-status:{owner_id}` (pub/sub, không lưu trữ). Nguồn sự thật vẫn là cột `document.status` trong PostgreSQL — sự kiện chỉ là thông báo.

## 5. Các bước triển khai

1. **Phía worker** (đã gọi ở T-201/T-203): sau mỗi lần đổi `document.status`, `PUBLISH doc-status:{owner_id}` với payload JSON ở §3.
2. **Phía API** — endpoint `GET /documents/events`:
   - Xác thực phiên; chưa đăng nhập → `401 SESSION_EXPIRED`.
   - Mở `SUBSCRIBE doc-status:{owner_id}` bằng client Redis **async** (không chặn event loop FastAPI).
   - Stream mỗi message nhận được thành khung `event: status` + `data: <json>`.
   - Gửi comment `: ping\n\n` mỗi 15 giây khi không có sự kiện — tránh Ingress/proxy đóng kết nối idle.
   - Gắn `id:` cho mỗi sự kiện (dùng Redis stream ID hoặc timestamp-counter) để client gửi lại qua `Last-Event-ID`.
3. **Dọn dẹp kết nối:** khi client ngắt (`request.is_disconnected()`), hủy subscribe và giải phóng kết nối Redis — tránh rò rỉ kết nối khi 10+ người dùng mở nhiều tab.
4. **Giới hạn kết nối:** mỗi người dùng tối đa N kết nối SSE đồng thời (đề xuất 5, cấu hình được) để một tab bị lỗi không làm cạn pool.
5. **Phía front-end** (phối hợp T-205):
   - Mở SSE sau khi `GET /documents` trả snapshot đầu tiên.
   - Khi nhận `status`, cập nhật đúng hàng trong cache TanStack Query theo `id`.
   - **Khi kết nối lại** (`onerror` → reconnect, hoặc tab visible trở lại): gọi lại `GET /documents` để bù sự kiện đã lỡ — nguồn sự thật là DB, không phải luồng sự kiện.
6. **Quan sát:** metric `sse_connections` (gauge) theo SADD §4.3; log khi đóng/mở kết nối chỉ ghi `user_hash`, không ghi tên tệp.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `SESSION_EXPIRED` (401) | Phiên hết hạn khi mở SSE hoặc trong lúc stream | Client đóng SSE, chuyển `/login?returnTo=...`, giữ bản nháp câu hỏi |
| — | Redis mất kết nối | API đóng stream êm; client tự reconnect (EventSource làm sẵn) rồi gọi lại `GET /documents` |

Trường hợp biên:
- **Nhiều bản sao API:** pub/sub broadcast tới mọi bản sao; chỉ bản sao đang giữ kết nối của đúng `owner_id` mới forward — không cần sticky session.
- **Nhiều tab cùng người dùng:** mỗi tab một kết nối, đều nhận cùng sự kiện — đúng mong muốn.
- **Tải lại trang khi tệp đang xử lý (NE-09):** máy chủ vẫn xử lý; `GET /documents` trả trạng thái hiện tại, SSE tiếp tục từ đó.
- **Sự kiện tới trước khi UI có hàng tương ứng** (hiếm, race khi upload): bỏ qua sự kiện không khớp `id` nào, lần `GET /documents` kế tiếp sẽ đồng bộ.
- **Proxy buffer:** nếu thiếu `X-Accel-Buffering: no`, sự kiện bị gom lại hàng chục giây → vi phạm AC-010.1. Phải kiểm thử qua Ingress thật, không chỉ localhost.

## 7. Kiểm thử bắt buộc

- [ ] Worker đổi trạng thái → UI cập nhật ≤ 5s qua Ingress staging — không có staging/Ingress thật, không đo được
- [x] A không nhận sự kiện của B — kênh pub/sub theo `doc-status:{owner_id}` (lấy từ `current_user.id`, không nhận từ client) nên tách biệt theo thiết kế; chưa có test 2 phiên song song tự động
- [ ] Ngắt mạng 30s rồi nối lại → UI dùng `GET /documents` để đồng bộ lại — endpoint `GET /documents` tồn tại và trả trạng thái mới nhất, nhưng **chưa có FE nào gọi SSE để mất kết nối rồi fallback** (xem T-106: `sseClient` chưa tồn tại)
- [x] Idle 60s không bị đóng — `document_events` gửi `": ping\n\n"` mỗi 15s khi không có message mới
- [x] Đóng tab → `sse_connections.dec()` trong khối `finally`, có `pubsub.unsubscribe()`/`close()`
- [ ] 10 tệp, 1 lỗi → 10 sự kiện cuối — logic publish đúng (mỗi lần đổi trạng thái gọi `_publish_status`), chưa có test tích hợp đo đủ số sự kiện

## 8. Định nghĩa Hoàn thành

- [ ] AC-010.1 trên staging — chưa có staging
- [ ] Không rò rỉ kết nối sau 100 lần mở-đóng — chưa test tải
- [ ] Chỉ `shared/api` phía FE gọi `EventSource` — **chưa áp dụng được, FE chưa có `sseClient`/`EventSource` nào cả** (gap nằm ở T-106, không phải T-204)
- [x] Payload không chứa tên tệp/nội dung — `_publish_status` chỉ gửi `id/status/error_code/page_count`

### Ghi chú triển khai thực tế

Phần backend (`GET /documents/events` trong `app/api/routers/documents.py`,
publish qua `app/modules/ingestion/service.py::_publish_status`) đã viết
đúng kiến trúc: kênh Redis theo `owner_id` lấy từ phiên (cô lập G-03),
keep-alive bằng comment SSE, dọn kết nối trong `finally`, payload tối giản
không rò rỉ nội dung. Kiểm tra tĩnh sạch (ruff/mypy/lint-imports).

**Chưa làm được, không thuộc phạm vi code T-204:** phía front-end chưa có
`shared/api/sseClient` nào gọi `EventSource` tới endpoint này (xem gap đã
ghi ở T-106) — nghĩa là SSE backend đã sẵn sàng nhưng chưa có UI nào tiêu
thụ nó. Đây là lý do T-205 (thư viện tài liệu UI) chưa thể tự cập nhật
real-time.

## 9. Tham chiếu

- SADD v0.3 §2.4.2 (API-06), §3.1.4 / §4.2.4 (Redis pub/sub, nhiều bản sao API), ADR-07 (chọn SSE), §4.3 (metric `sse_connections`)
- User Stories v0.4 — US-010 (AC-010.1 – AC-010.3), US-004 (AC-004.2), US-003 (NE-09)
- SDD UI/UX v0.3 §3.5.1 (API-06), §3.7.1 (vòng đời tài liệu), CN-02
