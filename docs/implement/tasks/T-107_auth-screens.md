# T-107 — Màn hình đăng nhập và chưa được cấp quyền

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-001 (Đăng nhập bằng tài khoản được cấp) |
| Epic | EP-01 — Truy cập và phân quyền |
| Module (SDD §3.1) | `features/auth` |
| API liên quan | API-01 `GET /me`, `/auth/login`, `/auth/logout` |
| Vai trò chính | FE |
| Ước lượng | 2d |
| Phụ thuộc | T-101 (luồng OIDC), T-102 (API-01), T-106 (nền tảng FE) |
| Trạng thái | To do |

## 1. Mục tiêu

Hiện thực 3 trạng thái giao diện của luồng truy cập: **đăng nhập (SCR-01)**, **đăng nhập lại sau khi phiên hết hạn (SCR-01 biến thể)** và **chưa được cấp quyền (SCR-03)**; kèm route guard bảo vệ toàn bộ ứng dụng và cơ chế **giữ bản nháp câu hỏi** khi phiên hết hạn.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-001.1 | Tài khoản được cấp quyền đăng nhập hợp lệ → vào màn hình chính, thấy tập tài liệu của mình |
| AC-001.2 | Không có trong danh sách cấp quyền → hiển thị "Bạn chưa được cấp quyền sử dụng. Liên hệ quản trị viên." và không tiết lộ tài liệu nào |
| AC-001.3 | Phiên hết hạn → chuyển về trang đăng nhập, **giữ lại nội dung câu hỏi đang soạn** |
| AC-001.4 | Chưa đăng nhập mà vào thẳng một đường dẫn nội bộ → chuyển về trang đăng nhập |

## 3. Giao diện — component và ảnh thiết kế

| Component | Props / trạng thái chính | Ảnh thiết kế |
|---|---|---|
| `LoginScreen` | `variant: 'default' \| 'session_expired'`, `returnTo` | [`SCR-01_login.png`](../../design/html_design/SCR-01_login.png), [`SCR-01_login-session-expired.png`](../../design/html_design/SCR-01_login-session-expired.png) |
| `NoAccessScreen` | — (nội dung cố định) + nút Đăng xuất | [`SCR-03_no-access.png`](../../design/html_design/SCR-03_no-access.png) |
| `RequireAuth` (route guard) | `children`; dùng `useMe()` | — |
| `NotFoundScreen` | nút "Về trang hỏi đáp" | [`SCR-07_page-not-found.png`](../../design/html_design/SCR-07_page-not-found.png) |

**Hành vi nút đăng nhập:** điều hướng **toàn trang** (`window.location.assign`) tới `/auth/login?return_to=<đường dẫn hiện tại>` — không dùng `fetch`, vì luồng OIDC cần redirect trình duyệt thật.

```ts
// Trạng thái phiên dùng chung
type SessionState =
  | { status: 'loading' }
  | { status: 'authenticated'; user: MeVM }
  | { status: 'unauthenticated' }      // 401 → /login
  | { status: 'forbidden' };           // 403 → /no-access
```

## 4. Thay đổi dữ liệu

| Dữ liệu | Nơi lưu | Khi nào |
|---|---|---|
| `cwd_draft_question` | `sessionStorage` | Ghi khi nhận 401 lúc đang có nội dung trong composer; **xóa ngay** sau khi khôi phục thành công hoặc khi người dùng gửi câu hỏi / đăng xuất (SDD §3.4.4 — ngoại lệ có kiểm soát, chờ D-04) |
| Cache TanStack Query | RAM | Xóa toàn bộ khi đăng xuất hoặc khi nhận 401 |

## 5. Các bước triển khai

1. **`useMe()`**: hook gọi `GET /me` (TanStack Query, `retry: false`), ánh xạ 200 → `authenticated`, 401 → `unauthenticated`, 403 → `forbidden`.
2. **Route guard `RequireAuth`** bọc route `/`:
   - `loading` → hiện skeleton toàn trang (không nháy trắng).
   - `unauthenticated` → `navigate('/login?returnTo=' + encodeURIComponent(pathname))` (AC-001.4).
   - `forbidden` → `navigate('/no-access')` (AC-001.2).
3. **`LoginScreen` (SCR-01)**: logo, tiêu đề sản phẩm, nút chính "Đăng nhập bằng tài khoản công ty", dòng phụ giải thích chỉ người được cấp quyền mới dùng được. Nút có `data-testid="login-sso"`.
4. **Biến thể `session_expired`**: khi URL có `?returnTo=` và trước đó đã có phiên (hoặc cờ trong `sessionStorage`), hiện thêm banner thông tin: "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại." — đúng thông báo `SESSION_EXPIRED` của SDD §3.4.3, kèm trấn an "Câu hỏi bạn đang soạn đã được giữ lại." nếu có bản nháp.
5. **Giữ bản nháp (AC-001.3)**:
   - Trong interceptor 401 của `shared/api` (T-106), trước khi điều hướng: đọc nội dung composer từ Zustand store, nếu khác rỗng thì ghi vào `sessionStorage['cwd_draft_question']`.
   - Sau khi đăng nhập lại và quay về `/`, `ChatPanel` (Sprint 3) đọc khóa này để khôi phục rồi **xóa khỏi storage**. Ở Sprint 1 chưa có composer: cài sẵn hàm `saveDraft()` / `restoreDraft()` trong `features/auth` và viết unit test cho chúng.
   - Mọi truy cập `sessionStorage` bọc `try/catch` (chế độ ẩn danh có thể ném lỗi).
6. **`NoAccessScreen` (SCR-03)**: biểu tượng, thông báo `NOT_AUTHORIZED` nguyên văn từ `messages.vi.ts`, nút "Đăng xuất" gọi `POST /auth/logout` rồi chuyển `/login`. **Không** hiển thị email, mã lỗi kỹ thuật, hay bất kỳ thông tin hệ thống nào khác.
7. **`NotFoundScreen` (SCR-07)**: route `*`. Lưu ý thứ tự: người **chưa đăng nhập** vào URL sai phải thấy `/login` trước, không phải trang 404 (AC-001.4) → đặt `RequireAuth` bao ngoài route 404 của khu vực đã đăng nhập.
8. **Đăng xuất**: xóa cache Query, xóa `sessionStorage` liên quan, gọi `POST /auth/logout`, chuyển `/login`.
9. **Khả năng truy cập**: tiêu đề `h1` trên mỗi màn hình, focus tự động vào nút chính khi tải, tương phản đạt WCAG AA (dùng token màu sẵn có).
10. **Đo lường**: phát `session_started{is_first_session}` một lần sau khi `GET /me` trả 200 lần đầu trong phiên trình duyệt (PRD §5.2) — thực hiện ở `features/auth`, không ở back-end.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI |
|---|---|---|
| `SESSION_EXPIRED` | Bất kỳ API nào trả 401 | Lưu bản nháp → `/login?returnTo=…` + banner phiên hết hạn |
| `NOT_AUTHORIZED` | `GET /me` trả 403 | Chuyển SCR-03, nút Đăng xuất là hành động duy nhất |

**Trường hợp biên:**
- Người dùng bấm Hủy ở màn hình IdP → quay lại `/login` với thông báo trung tính, không hiện lỗi đỏ.
- Mở nhiều tab: tab A hết phiên, tab B đăng nhập lại → tab A khi thao tác tiếp sẽ dùng cookie mới và hoạt động bình thường (không cần đồng bộ thủ công).
- `returnTo` nhận từ URL phải được validate phía client (chỉ chấp nhận đường dẫn bắt đầu bằng `/`), tránh bị lợi dụng dù back-end đã chặn (T-101).
- Chưa đăng nhập mà vào `/no-access` trực tiếp → chuyển về `/login` (không cho phép xem màn hình này khi không có phiên).

## 7. Kiểm thử bắt buộc

- [ ] Vào `/` khi chưa đăng nhập → chuyển `/login?returnTo=%2F` (AC-001.4)
- [ ] Đăng nhập thành công → quay về đúng `returnTo`, hiển thị màn hình chính (AC-001.1)
- [ ] `GET /me` trả 403 → hiện SCR-03 với đúng thông báo, **không** thấy danh sách tài liệu nào (AC-001.2)
- [ ] Giả lập 401 khi composer đang có chữ → sau khi đăng nhập lại, nội dung được khôi phục nguyên vẹn và `sessionStorage` đã được xóa (AC-001.3)
- [ ] Chế độ ẩn danh chặn `sessionStorage` → ứng dụng vẫn đăng nhập/điều hướng bình thường, chỉ mất tính năng giữ bản nháp
- [ ] Đăng xuất → cache Query trống, không còn dữ liệu người dùng nào trong Web Storage
- [ ] axe-core trên SCR-01, SCR-03, SCR-07: không có lỗi nghiêm trọng; điều hướng được hoàn toàn bằng bàn phím
- [ ] Giao diện khớp ảnh thiết kế ở 1280px và 1024px

## 8. Định nghĩa Hoàn thành

- [ ] 4 AC của US-001 đạt ở phía giao diện, có test E2E cho ít nhất AC-001.2 và AC-001.4
- [ ] Toàn bộ chuỗi lấy từ `messages.vi.ts`, không hard-code
- [ ] SCR-03 không tiết lộ bất kỳ thông tin hệ thống nào ngoài thông báo chuẩn
- [ ] Sự kiện `session_started` phát đúng một lần mỗi phiên

## 9. Tham chiếu

[`../../design/User_Stories.md`](../../design/User_Stories.md) US-001 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.2.1 (SCR-01/03/07), §3.4.3, §3.4.4, §3.5.3 · [`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2, §4.1.1 · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.2 (`session_started`) · Ảnh: [`SCR-01_login.png`](../../design/html_design/SCR-01_login.png), [`SCR-01_login-session-expired.png`](../../design/html_design/SCR-01_login-session-expired.png), [`SCR-03_no-access.png`](../../design/html_design/SCR-03_no-access.png), [`SCR-07_page-not-found.png`](../../design/html_design/SCR-07_page-not-found.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
