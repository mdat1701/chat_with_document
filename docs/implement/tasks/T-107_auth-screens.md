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
| Trạng thái | In progress (3 màn hình + route guard + AC-001.3 (giữ bản nháp) + i18n + `session_started` đã nối trong phiên này; còn thiếu axe-core/so khớp ảnh thiết kế/E2E) |

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

- [x] Vào `/` khi chưa đăng nhập → chuyển `/login?returnTo=%2F` (AC-001.4) — route guard trong `App.tsx` dùng `useAuth()`, xác nhận bằng đọc code (link `/auth/login?return_to=...` được dựng động từ `window.location.pathname`)
- [ ] Đăng nhập thành công → quay về đúng `returnTo`, hiển thị màn hình chính (AC-001.1) — phần redirect sau login nằm ở backend OIDC callback (T-101), chưa có test FE xác nhận round-trip
- [x] `GET /me` trả 403/401 → hiện SCR-03/`/login`, không thấy danh sách tài liệu nào (AC-001.2) — `useAuth.load()` set `user: null` khi `apiFetch` ném lỗi, route guard chuyển hướng
- [x] Giả lập 401 khi composer đang có chữ → sau khi đăng nhập lại, nội dung được khôi phục nguyên vẹn (AC-001.3) — `setUnauthorizedHandler()` trong `shared/api/client.ts` gọi `captureDraftOnUnauthorized()` (`features/auth/draft.ts`) trên mọi 401 (`apiFetch` và `streamQuestion`); `ChatPage` đăng ký nội dung composer hiện tại qua `registerComposerSource()` và khôi phục bằng `restoreDraft()` lúc mount. Xác nhận bằng unit test (`draft.test.ts`, 9 test) — chưa có E2E trình duyệt thật cho round-trip UI đầy đủ
- [x] Chế độ ẩn danh chặn `sessionStorage` → `saveDraft`/`restoreDraft`/`clearDraft` bọc `try/catch`, không ném lỗi khi storage bị chặn — test giả lập bằng cách mock `sessionStorage.prototype` ném `DOMException`
- [ ] Đăng xuất → cache Query trống — chưa có TanStack Query nào được dùng thật (xem ghi chú T-106)
- [ ] axe-core trên SCR-01, SCR-03, SCR-07 — axe-core chưa được cài (xem T-106)
- [ ] Giao diện khớp ảnh thiết kế ở 1280px và 1024px — chưa đối chiếu bằng mắt/test ảnh

## 8. Định nghĩa Hoàn thành

- [x] 4 AC của US-001 đạt ở phía giao diện — AC-001.3 (giữ bản nháp khi phiên hết hạn) nay có `features/auth/draft.ts` + interceptor 401 toàn cục trong `shared/api/client.ts`
- [x] Toàn bộ chuỗi lấy từ `messages.vi.ts`, không hard-code — `AuthScreens.tsx` nay import `messages`/`authMessages` từ `shared/i18n/messages.vi.ts`, không còn chuỗi hard-code trong JSX
- [x] SCR-03 không tiết lộ bất kỳ thông tin hệ thống nào ngoài thông báo chuẩn — xác nhận bằng đọc `NoAccessScreen`
- [x] Sự kiện `session_started` phát đúng một lần mỗi phiên — `features/auth/auth.ts` gọi `track("session_started", { is_first_session })` ngay sau `GET /me` thành công, khử trùng lặp bằng cờ `cwd_session_started` trong `sessionStorage` (bọc try/catch)

### Ghi chú triển khai thực tế

**Đã có và chạy được (phiên trước):** `LoginScreen`, `NoAccessScreen`
(component thật, không phải placeholder), route guard trong `App.tsx` dựa
trên `useAuth()` (Zustand store gọi thật `GET /me` qua `apiFetch`), đường
dẫn `returnTo` được dựng động theo `window.location.pathname`.

**Đã sửa trong phiên này (3 khoảng trống còn lại của T-107):**

1. **AC-001.3 — giữ bản nháp câu hỏi khi phiên hết hạn.** Thêm
   `features/auth/draft.ts` (`saveDraft`/`restoreDraft`/`clearDraft`, khóa
   `cwd_draft_question`, mọi truy cập `sessionStorage` bọc `try/catch` —
   chế độ ẩn danh không làm crash). `shared/api/client.ts` thêm
   `setUnauthorizedHandler()` — một điểm đăng ký handler chung thay vì
   `shared/api` import ngược `features/auth` (vi phạm DR-02); `apiFetch` và
   `streamQuestion` đều gọi handler này trên mọi phản hồi 401.
   `features/auth/auth.ts` đăng ký handler đó lúc khởi động module: lưu
   nháp (qua `captureDraftOnUnauthorized()`) rồi đặt `user: null` để route
   guard tự chuyển `/login`. Vì composer thật (`features/chat/ChatPage.tsx`)
   dùng `useState` cục bộ chứ chưa có store dùng chung, `ChatPage` tự đăng
   ký "nguồn đọc nội dung hiện tại" qua `registerComposerSource()` (tương tự
   cách `setCsrfToken` tách rời `shared/api` khỏi state cụ thể) — tránh
   `shared/api`/`features/auth` phụ thuộc ngược vào `features/chat`.
   `ChatPage` khôi phục nháp lúc mount (`restoreDraft()`), xóa ngay sau khi
   đọc và xóa lại sau khi gửi câu hỏi thành công. `LoginScreen` hiện thêm
   banner `SESSION_EXPIRED` (+ câu trấn an "đã được giữ lại" nếu còn nháp)
   khi trình duyệt từng có phiên hợp lệ trước đó trong tab
   (`hasPriorSessionInBrowser()`, dựa trên cờ `cwd_session_started`).
   9 unit test mới trong `features/auth/draft.test.ts`, gồm cả trường hợp
   `sessionStorage` ném lỗi (mock `DOMException` trên prototype).
2. **i18n.** `AuthScreens.tsx` không còn chuỗi hard-code: thêm
   `authMessages` vào `shared/i18n/messages.vi.ts` (tách khỏi `messages`
   vốn chỉ dành cho mã lỗi SDD §3.4.3, để không làm phình `ErrorCode`), và
   `LoginScreen`/`NoAccessScreen` import từ đó. Đồng thời thay `<a>`/
   `<button>` thô bằng `Button` và banner thô bằng `Banner` của
   `shared/ui` (T-106) — giảm khoảng cách design-system mà không đổi hành
   vi: nút đăng nhập vẫn điều hướng toàn trang bằng
   `window.location.assign` (không qua `fetch`, giữ đúng ghi chú §3 vì
   luồng OIDC cần redirect trình duyệt thật), chỉ chuyển từ thẻ `<a>` sang
   `onClick` trên `Button`.
3. **`session_started`.** `features/auth/auth.ts::useAuth.load()` gọi
   `track("session_started", { is_first_session })` ngay sau khi `GET /me`
   trả 200 lần đầu, khử trùng lặp bằng cờ `cwd_session_started` trong
   `sessionStorage` (không phát lại khi `load()` bị gọi lại, ví dụ
   StrictMode/remount). **`is_first_session`:** codebase hiện chưa có tín
   hiệu rõ ràng phân biệt "vừa hoàn tất đăng nhập OIDC" với "tải lại trang
   đã có cookie sẵn" ở phía FE, vì redirect sau khi đăng nhập do backend
   OIDC callback xử lý (T-101) chứ không đi qua một route FE riêng. Chọn
   dùng tín hiệu sẵn có gần nhất — `document.referrer` chứa `/auth/login`
   — coi đó là phiên vừa đăng nhập (`is_first_session: true`); mọi lần tải
   trang khác (đã có cookie, không tới từ bước đăng nhập) là
   `is_first_session: false`. Đây là xấp xỉ hợp lý trong phạm vi FE hiện
   tại, không hoàn hảo (ví dụ mất referrer khi trình duyệt chặn Referrer
   Policy nghiêm ngặt) — nếu cần chính xác tuyệt đối, nên đổi sang một cờ
   do backend OIDC callback set (ngoài phạm vi T-107, chạm vào T-101/BE).

**Còn thiếu (không đổi so với trước, ngoài phạm vi phiên này):** axe-core,
so khớp ảnh thiết kế ở 1280px/1024px, E2E cho AC-001.1/1.2/1.4 — không có
trình duyệt thật để chạy Playwright/axe trong môi trường này (xem ghi chú
T-504). Round-trip AC-001.3 mới được xác nhận bằng unit test, chưa bằng
E2E trình duyệt thật.

Giữ trạng thái **"In progress"**: các khoảng trống AC-001.3/i18n/
`session_started` đã đóng, nhưng DoD về axe-core/so khớp ảnh thiết kế/E2E
vẫn chưa đạt.

## 9. Tham chiếu

[`../../design/User_Stories.md`](../../design/User_Stories.md) US-001 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.2.1 (SCR-01/03/07), §3.4.3, §3.4.4, §3.5.3 · [`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2, §4.1.1 · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.2 (`session_started`) · Ảnh: [`SCR-01_login.png`](../../design/html_design/SCR-01_login.png), [`SCR-01_login-session-expired.png`](../../design/html_design/SCR-01_login-session-expired.png), [`SCR-03_no-access.png`](../../design/html_design/SCR-03_no-access.png), [`SCR-07_page-not-found.png`](../../design/html_design/SCR-07_page-not-found.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
