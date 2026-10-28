# T-102 — Phiên, CSRF và `GET /me`

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-001 (Đăng nhập bằng tài khoản được cấp) |
| Epic | EP-01 — Truy cập và phân quyền |
| Module (SADD §2.2.1) | `identity`, `core` |
| API liên quan | API-01 `GET /me` |
| Vai trò chính | BE |
| Ước lượng | 1d |
| Phụ thuộc | T-101 (session đã được tạo) |
| Trạng thái | Done |

## 1. Mục tiêu

Cung cấp điểm vào duy nhất để front-end biết "tôi là ai, tôi có quyền gì" và lấy `csrf_token`; đồng thời cài middleware kiểm tra phiên + CSRF áp dụng cho **mọi** request ghi dữ liệu của toàn hệ thống (áp dụng từ T-108 trở đi).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-001.1 | *Given* tài khoản được cấp quyền, *When* đăng nhập hợp lệ, *Then* vào màn hình chính và hiển thị tập tài liệu của người dùng (UI dựa vào `GET /me` để biết đã đăng nhập) |
| AC-001.3 | *Given* phiên đã hết hạn, *When* thực hiện thao tác bất kỳ, *Then* chuyển về trang đăng nhập và giữ nội dung câu hỏi đang soạn |
| AC-001.4 | *Given* chưa đăng nhập, *When* truy cập đường dẫn bên trong ứng dụng, *Then* chuyển về trang đăng nhập |

## 3. Hợp đồng API

```http
GET /me
Cookie: cwd_sid=<sid>
→ 200 {
    "id": "7f1c…",
    "display_name": "Lê Minh Anh",
    "email": "minhanh.le@example.com",
    "roles": ["user"],
    "csrf_token": "b3f9…"
  }
→ 401 { "code": "SESSION_EXPIRED" }    // không có cookie, hoặc session không còn trong Redis
→ 403 { "code": "NOT_AUTHORIZED" }     // session còn nhưng app_user.active vừa bị thu hồi
```

**Quy ước CSRF áp dụng cho mọi method ghi (`POST`, `PUT`, `PATCH`, `DELETE`):**

```http
POST /documents
Cookie: cwd_sid=<sid>
X-CSRF-Token: <csrf_token lấy từ GET /me>
→ 403 { "code": "CSRF_INVALID" }   // thiếu header hoặc không khớp giá trị trong session
```

`GET` / `HEAD` không yêu cầu CSRF (chỉ đọc, an toàn).

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `session:{sid}` (Redis) | Đọc mỗi request; cập nhật `last_seen_at` để TTL 2 giờ trượt; `csrf_token` sinh một lần khi tạo session (T-101) và giữ nguyên suốt phiên |
| `app_user` | Đọc `active`, `display_name`, `email`; join `user_role` lấy `roles[]` |

## 5. Các bước triển khai

1. Viết FastAPI dependency `get_current_session()`:
   - Đọc cookie `cwd_sid` → không có thì raise 401 `SESSION_EXPIRED`.
   - `GET session:{sid}` từ Redis → không có (đã hết TTL hoặc bị thu hồi bởi T-103) thì 401 `SESSION_EXPIRED`.
   - Kiểm tra mốc tuyệt đối: `now - created_at > 12h` → xóa key, 401.
   - Cập nhật `last_seen_at` và gia hạn TTL 2 giờ (`EXPIRE session:{sid} 7200`).
2. Viết dependency `require_active_user()` dùng tiếp kết quả trên: tra `app_user.active`; `false` → 403 `NOT_AUTHORIZED` (bao trường hợp quyền bị thu hồi giữa phiên mà session chưa kịp xóa).
3. Viết middleware CSRF: với method ghi, so sánh header `X-CSRF-Token` với `session.csrf_token` bằng so sánh hằng thời gian (`secrets.compare_digest`) → lệch thì 403 `CSRF_INVALID`.
4. Cài `GET /me` dùng hai dependency trên, trả payload như hợp đồng ở §3. **Không** trả thông tin nội bộ (sid, oidc_subject).
5. Đầu mỗi transaction DB của request đã xác thực, chạy `SET LOCAL app.user_id = '<user_id>'` để policy RLS ở T-104 hoạt động — đặt trong cùng dependency để developer không thể quên.
6. Chuẩn hóa body lỗi toàn hệ thống về `{ "code": "<ErrorCode>", "params": {…} }` (quy ước SADD §2.4.2) — **không** trả nguyên văn thông báo máy chủ cho client.
7. Thêm metric Prometheus: `auth_me_total{outcome}`, `csrf_rejected_total`.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI/API |
|---|---|---|
| `SESSION_EXPIRED` | Không có cookie, session hết TTL, hoặc vượt mốc 12 giờ tuyệt đối | 401; UI lưu bản nháp vào `sessionStorage` rồi chuyển `/login?returnTo=…` (AC-001.3) |
| `NOT_AUTHORIZED` | Session còn nhưng `app_user.active = false` | 403; UI chuyển SCR-03 |
| `CSRF_INVALID` *(nội bộ)* | Request ghi thiếu / sai `X-CSRF-Token` | 403; UI coi là lỗi hệ thống, yêu cầu tải lại trang |

**Trường hợp biên:**
- Quyền bị thu hồi bằng CLI (T-103) trong lúc người dùng đang thao tác → T-103 xóa toàn bộ session nên request kế tiếp trả 401; nếu vì lý do nào đó session còn, `require_active_user()` chặn bằng 403 (hai lớp).
- Nhiều tab mở cùng lúc: mọi tab dùng chung một `csrf_token` của cùng session — đúng theo thiết kế, không cần token theo tab.
- Client gọi `GET /me` song song nhiều lần → không được sinh lại `csrf_token` (phải idempotent).

## 7. Kiểm thử bắt buộc

- [ ] `GET /me` có cookie hợp lệ → 200, payload đúng schema, `roles` lấy từ `user_role`
- [ ] `GET /me` không cookie → 401 `SESSION_EXPIRED`
- [ ] Xóa `session:{sid}` khỏi Redis → `GET /me` trả 401 ngay lần gọi kế tiếp
- [ ] Set `app_user.active=false` nhưng giữ session → `GET /me` trả 403 `NOT_AUTHORIZED`
- [ ] `POST` tới endpoint ghi bất kỳ **không** kèm `X-CSRF-Token` → 403 `CSRF_INVALID`
- [ ] `POST` kèm token sai → 403; kèm token đúng → đi tiếp bình thường
- [ ] Gọi `GET /me` 2 lần liên tiếp → `csrf_token` giống nhau (không xoay vòng)
- [ ] Sau 2 giờ không hoạt động → session hết hạn; hoạt động liên tục 11 giờ 50 phút → vẫn sống; sang 12 giờ 1 phút → hết hạn

## 8. Định nghĩa Hoàn thành

- [ ] Mọi endpoint ghi trong codebase đều đi qua middleware CSRF (kiểm tra bằng test quét route)
- [ ] `SET LOCAL app.user_id` được đặt tự động, không phụ thuộc developer nhớ gọi
- [ ] Body lỗi thống nhất `{code, params}` cho toàn bộ API
- [ ] Log không chứa `sid`, `csrf_token`, email (chỉ `user_hash`)

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (API-01), §3.1.3 (`SET LOCAL app.user_id`), §4.1.1 · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-001 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.4.3 (danh mục mã lỗi), §3.5.1 (API-01) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
