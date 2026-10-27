# T-101 — Đăng nhập OIDC theo mẫu BFF

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-001 (Đăng nhập bằng tài khoản được cấp) |
| Epic | EP-01 — Truy cập và phân quyền |
| Module (SADD §2.2.1) | `identity` |
| API liên quan | `/auth/login`, `/auth/callback`, `/auth/logout` (SADD §2.4.2) |
| Vai trò chính | BE (hỗ trợ: TL, ATTT) |
| Ước lượng | 3d |
| Phụ thuộc | T-005 (schema `app_user`), T-008 (khung FastAPI), **D-03** (chốt IdP) |
| Trạng thái | To do |

## 1. Mục tiêu

Dựng luồng đăng nhập OIDC theo mẫu **BFF (Backend-for-Frontend)** — back-end giữ token, trình duyệt chỉ nhận cookie phiên `HttpOnly` (ADR-08). Đăng nhập OIDC thành công **chưa đủ**: tài khoản phải có `app_user.active = true` mới được vào ứng dụng; nếu không, chuyển tới `/no-access` (AC-001.2).

Nguyên tắc bảo mật bắt buộc: không có access token / refresh token nào đi qua JavaScript hoặc Web Storage (SDD §3.4.4, ranh giới tin cậy TB-1).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-001.1 | *Given* tài khoản nằm trong danh sách được cấp quyền, *When* đăng nhập với thông tin hợp lệ, *Then* hệ thống chuyển tới màn hình chính và hiển thị tập tài liệu của người dùng |
| AC-001.2 | *Given* người dùng không có trong danh sách được cấp quyền, *When* cố đăng nhập, *Then* hệ thống từ chối, hiển thị "Bạn chưa được cấp quyền sử dụng. Liên hệ quản trị viên." và không tiết lộ bất kỳ tài liệu nào |
| AC-001.3 | *Given* phiên đã hết hạn, *When* người dùng thực hiện thao tác bất kỳ, *Then* hệ thống chuyển về trang đăng nhập và giữ lại nội dung câu hỏi đang soạn (phần UI ở T-107) |
| AC-001.4 | *Given* người dùng chưa đăng nhập, *When* truy cập trực tiếp một đường dẫn bên trong ứng dụng, *Then* hệ thống chuyển về trang đăng nhập |

## 3. Hợp đồng API

```http
GET /auth/login?return_to=/
→ 302 Location: https://<idp>/authorize
       ?response_type=code&client_id=...&redirect_uri=...
       &scope=openid%20profile%20email&state=<random>&nonce=<random>
       &code_challenge=<S256>&code_challenge_method=S256
   Set-Cookie: cwd_oidc_tx=<signed state|nonce|verifier|return_to>; HttpOnly; Secure; SameSite=Lax; Max-Age=300
→ 400 { "code": "INVALID_RETURN_TO" }        // return_to không phải đường dẫn nội bộ
```

```http
GET /auth/callback?code=<code>&state=<state>
→ 302 Location: <return_to>                   // hợp lệ + app_user.active = true
   Set-Cookie: cwd_sid=<sid>; HttpOnly; Secure; SameSite=Lax; Path=/
   Set-Cookie: cwd_oidc_tx=; Max-Age=0        // xóa cookie giao dịch
→ 302 Location: /no-access                    // xác thực OK nhưng chưa được cấp quyền
→ 400 { "code": "OIDC_STATE_MISMATCH" }       // state/nonce không khớp hoặc hết hạn
```

```http
POST /auth/logout
Headers: X-CSRF-Token: <token>
→ 204 No Content
   Set-Cookie: cwd_sid=; Max-Age=0
```

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `app_user` (PostgreSQL) | Đọc theo `oidc_subject`; lần đăng nhập đầu của tài khoản đã được cấp quyền bằng email (T-103) thì **điền** `oidc_subject` và `display_name` |
| `session:{sid}` (Redis) | Tạo mới: `{user_id, csrf_token, roles[], created_at, last_seen_at}`; TTL 2 giờ (trượt theo `last_seen_at`), **tuyệt đối tối đa 12 giờ** tính từ `created_at` |
| `sessions_by_user:{user_id}` (Redis SET) | Thêm `sid` — để T-103 thu hồi quyền xóa được toàn bộ phiên của một người dùng |
| `audit_log` | Ghi `login_success` / `login_denied` / `logout` (không chứa nội dung tài liệu) |

## 5. Các bước triển khai

1. Đăng ký OIDC client với IdP đã chốt ở **D-03** (SSO nội bộ hoặc Keycloak tự lưu trữ). Lưu `client_id` / `client_secret` qua secret manager (External Secrets / Vault) — **không** hard-code, không đưa vào image.
2. Cài adapter OIDC trong `adapters/` (ví dụ `authlib`), module miền `identity` chỉ gọi qua port — đổi IdP không sửa code miền (nguyên tắc P-01).
3. `GET /auth/login`:
   - Validate `return_to` bằng regex `^/(?!/)` (bắt buộc là đường dẫn nội bộ, chặn `//evil.com` và URL tuyệt đối) → sai thì 400.
   - Sinh `state`, `nonce` (32 byte ngẫu nhiên) và PKCE `code_verifier` → `code_challenge` (S256).
   - Lưu bộ bốn `{state, nonce, code_verifier, return_to}` vào cookie giao dịch `cwd_oidc_tx` **có ký HMAC**, TTL 300 giây.
   - Redirect 302 tới endpoint `authorize` của IdP.
4. `GET /auth/callback`:
   - Đọc và verify chữ ký cookie `cwd_oidc_tx`; so khớp `state` → lệch hoặc hết hạn thì 400 `OIDC_STATE_MISMATCH`.
   - Đổi `code` lấy token qua **back-channel** (server → IdP, không qua trình duyệt), gửi kèm `code_verifier`.
   - Verify chữ ký ID token (JWKS, cache khóa công khai), kiểm tra `iss`, `aud`, `exp`, `nonce`.
5. Kiểm tra cấp quyền: tra `app_user` theo `oidc_subject`; nếu không thấy, tra theo `email` (tài khoản đã cấp quyền trước bằng CLI nhưng chưa từng đăng nhập) và điền `oidc_subject`.
   - Không tìm thấy bản ghi **hoặc** `active = false` → **không tạo session**, xóa cookie giao dịch, 302 `/no-access`, ghi `audit_log` `login_denied`.
6. Tạo session: `sid` ngẫu nhiên 32 byte, ghi `session:{sid}` + thêm vào `sessions_by_user:{user_id}`, đặt cookie `cwd_sid` (`HttpOnly; Secure; SameSite=Lax; Path=/`), redirect về `return_to`.
7. `POST /auth/logout`: xóa `session:{sid}`, gỡ `sid` khỏi `sessions_by_user:{user_id}`, xóa cookie, 204.
8. **Không** phát sự kiện `session_started` ở đây — sự kiện này do front-end phát sau khi `GET /me` (T-102) trả 200 lần đầu trong phiên trình duyệt.
9. Thêm span OTel `auth.login`, `auth.callback` (thuộc tính: `outcome`, không ghi email/sub vào log — chỉ `user_hash`).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI/API |
|---|---|---|
| `NOT_AUTHORIZED` | Xác thực OIDC thành công nhưng `app_user` không tồn tại hoặc `active=false` | 302 `/no-access`; UI hiện SCR-03 (T-107), không tiết lộ thông tin hệ thống |
| `SESSION_EXPIRED` | Cookie `cwd_sid` không còn session tương ứng trong Redis | Mọi API trả 401; UI chuyển `/login?returnTo=…` (T-102, T-107) |
| `INVALID_RETURN_TO` *(nội bộ)* | `return_to` là URL tuyệt đối hoặc `//host` | 400, không redirect — chống open-redirect |
| `OIDC_STATE_MISMATCH` *(nội bộ)* | `state` lệch, cookie giao dịch hết hạn hoặc bị giả mạo | 400, yêu cầu đăng nhập lại từ đầu |

**Trường hợp biên:**
- IdP trả `error=access_denied` (người dùng bấm Hủy trên màn hình IdP) → redirect `/login` kèm thông báo trung tính, không coi là lỗi hệ thống.
- Người dùng mở 2 tab cùng đăng nhập → mỗi tab có cookie giao dịch riêng; cả hai hoàn tất đều hợp lệ (session thứ hai ghi đè cookie `cwd_sid`).
- Phiên vượt 12 giờ tuyệt đối dù vẫn hoạt động → vẫn bị hết hạn (yêu cầu bảo mật), UI xử lý theo AC-001.3.

## 7. Kiểm thử bắt buộc

- [ ] Tài khoản `active=true` → sau đăng nhập vào thẳng `/`, `GET /me` trả 200 (AC-001.1)
- [ ] Tài khoản không có trong `app_user` → 302 `/no-access`, **không** có `Set-Cookie: cwd_sid` trong response (AC-001.2)
- [ ] Tài khoản `active=false` → kết quả giống trên (AC-001.2)
- [ ] `GET /auth/login?return_to=https://evil.com` và `?return_to=//evil.com` → 400, không redirect ra ngoài
- [ ] `state` bị sửa trong URL callback → 400 `OIDC_STATE_MISMATCH`, không tạo session
- [ ] Xóa key `session:{sid}` trong Redis → request tiếp theo trả 401 `SESSION_EXPIRED` (AC-001.3)
- [ ] Session tạo cách đây 12 giờ 1 phút nhưng vừa hoạt động → vẫn hết hạn
- [ ] `POST /auth/logout` → 204, key Redis bị xóa, `sid` rời khỏi `sessions_by_user:{user_id}`
- [ ] Log/trace của toàn bộ luồng không chứa email, `sub`, hay token (chỉ `user_hash`) — nguyên tắc P-03

## 8. Định nghĩa Hoàn thành

- [ ] 4 AC của US-001 liên quan tới back-end đạt, có test tự động trong CI
- [ ] Không có token OIDC nào đọc được bằng JavaScript (kiểm tra thủ công bằng DevTools: chỉ thấy cookie `HttpOnly`)
- [ ] Secret nạp từ secret manager, không nằm trong repo hay image
- [ ] `audit_log` ghi đủ `login_success` / `login_denied` / `logout`
- [ ] Code review bởi TL + rà soát nhanh của ATTT về luồng token

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (endpoint), §4.1.1 (xác thực), Phụ lục C ADR-08 · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-001 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.4.3, §3.4.4 · Ảnh: [`SCR-01_login.png`](../../design/html_design/SCR-01_login.png), [`SCR-03_no-access.png`](../../design/html_design/SCR-03_no-access.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
