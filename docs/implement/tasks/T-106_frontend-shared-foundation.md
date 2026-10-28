# T-106 — Nền tảng front-end dùng chung (`shared/*`)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | — (hạ tầng UI phục vụ toàn bộ EP-01 – EP-04) |
| Epic | — |
| Module (SDD §3.1) | `shared/tokens`, `shared/ui`, `shared/api`, `shared/i18n`, `shared/validation`, `shared/config`, `app` |
| API liên quan | Tiêu thụ API-01, API-02 (và chuẩn bị cho API-03 – API-09) |
| Vai trò chính | FE (một người kiêm design system) |
| Ước lượng | 3d |
| Phụ thuộc | T-102 (API-01), T-105 (API-02) |
| Trạng thái | Done (nền tảng lõi + `shared/ui` + `useAppConfig()` + lint ranh giới + axe-core đã xong; còn thiếu README kiến trúc front-end và việc dọn hex-literal cố định trong `features/*`/`global.css` — xem "Ghi chú triển khai thực tế") |

## 1. Mục tiêu

Dựng bộ khung front-end theo kiến trúc **feature-sliced** của SDD §3.1: design token, thư viện component dùng chung, HTTP/SSE client có ánh xạ lỗi, danh mục chuỗi tiếng Việt và router 4 màn hình của MVP-lite. Mọi feature ở các sprint sau chỉ việc lắp vào, không phải dựng lại hạ tầng.

Quy tắc kiến trúc bắt buộc (SDD §3.3): `shared/*` **không được** import `features/*`; chỉ `shared/api` được gọi `fetch`/`EventSource`; component trong `shared/ui` **không** gọi API.

## 2. Tiêu chí liên quan

| Mã | Nội dung |
|---|---|
| CN-08 | Đạt WCAG 2.1 AA — dùng Radix UI primitives để không phải tự viết ARIA |
| CN-09 | Thành phần hiển thị thuần, không gọi API trực tiếp; thay đổi một tính năng ảnh hưởng ≤ 2 module |
| CN-10 | Mọi phần tử tương tác có `data-testid` |
| AC-001.4 | Chưa đăng nhập mà vào đường dẫn nội bộ → chuyển về `/login` (route guard) |
| UX-07 | Giao diện tiếng Việt; toàn bộ chuỗi nằm ngoài code |

## 3. Cấu trúc và giao diện module

```
frontend/src/
  app/                 # router, provider (Query/Auth/i18n), error boundary toàn cục
  features/            # auth | documents | chat  (dựng dần ở T-107 → T-405)
  shared/
    tokens/            # CSS variables: màu, chữ, khoảng cách, bo góc, shadow
    ui/                # Button, Badge, Dialog, Toast, Tooltip, Skeleton, Banner, EmptyState
    api/               # httpClient, sseClient, errorMapper
    i18n/              # messages.vi.ts, formatDate, formatNumber
    validation/        # validateFiles(files, config, used)
    config/            # useAppConfig() — nạp GET /config một lần
```

**Hợp đồng `shared/api`:**

```ts
// httpClient tự gắn X-CSRF-Token, tự xử lý 401
const res = await http.get<DocumentVM[]>('/documents');

// Lỗi luôn được ánh xạ về ErrorCode, không bao giờ ném thông báo thô của server
type ApiError = { code: ErrorCode; params?: Record<string, string | number> };

// sseClient dùng cho API-06 và API-09
const stream = sse('/documents/events', { onEvent, onError, onReconnect });
```

**Component `shared/ui` (tối thiểu, theo SDD §3.2.3):** `Button`, `IconButton`, `Badge`, `Dialog`, `Toast` + `ToastRegion`, `Tooltip`, `Skeleton`, `Banner`, `EmptyState`.

## 4. Thay đổi dữ liệu

Không có thay đổi CSDL. Chính sách lưu trữ phía client (SDD §3.4.4) phải được cài **ngay từ task này**:

| Dữ liệu | Nơi lưu | Ghi chú |
|---|---|---|
| Token/phiên | Cookie `HttpOnly` do back-end đặt | JS **không** đọc được |
| Danh sách tài liệu, câu trả lời | RAM (TanStack Query cache, Zustand) | Xóa sạch khi đăng xuất |
| Bản nháp câu hỏi | `sessionStorage` | Ngoại lệ có kiểm soát (AC-001.3), chờ ATTT xác nhận (D-04/DQ-04) |
| Tùy chọn giao diện (ngăn tài liệu mở/đóng) | `localStorage` | Không chứa nội dung |
| Nội dung tài liệu / câu hỏi / câu trả lời | **Không lưu** vào Web Storage hay IndexedDB | Nguyên tắc CN-06 |

## 5. Các bước triển khai

1. Khởi tạo dự án **React 18 + TypeScript + Vite** (SADD Phụ lục A); bật `strict` trong `tsconfig`.
2. `shared/tokens`: khai báo CSS variables đúng bảng design token SDD §3.8.1 — `--color-text`, `--color-primary`, `--color-success`, `--color-warning`, `--color-danger`, `--color-surface-muted`, `--font-body`… **Cấm** mã màu cố định trong component (thêm lint rule chặn hex literal trong `features/*`).
3. `shared/ui`: bọc Radix UI primitives cho `Dialog`, `Tooltip`, `DropdownMenu`; tự viết `Button`, `Badge`, `Skeleton`, `Banner`, `EmptyState`, `Toast`. Mọi component nhận prop `data-testid`.
4. `shared/i18n`: tạo `messages.vi.ts` chứa **toàn bộ** chuỗi hiển thị, bao gồm bảng mã lỗi của SDD §3.4.3 (`FILE_NOT_PDF`, `FILE_TOO_LARGE`, `TOO_MANY_PAGES`, `PDF_ENCRYPTED`, `PDF_CORRUPTED`, `PDF_NO_TEXT`, `QUOTA_EXCEEDED`, `UPLOAD_NETWORK`, `ANSWER_NETWORK`, `SERVICE_BUSY`, `ANSWER_TIMEOUT`, `ANSWER_INTERRUPTED`, `SESSION_EXPIRED`, `NOT_AUTHORIZED`, `DOC_NOT_FOUND`). Thêm hàm định dạng ngày `dd/MM/yyyy` và số theo `vi-VN`.
5. `shared/api/httpClient`:
   - Tự gắn header `X-CSRF-Token` lấy từ store phiên cho mọi method ghi.
   - `credentials: 'include'` để gửi cookie.
   - Bắt 401 → xóa cache, lưu bản nháp (nếu có) vào `sessionStorage`, chuyển `/login?returnTo=<path>`.
   - Ánh xạ body `{code, params}` → `ApiError`; nếu server trả thứ khác (502 HTML chẳng hạn) → `SERVICE_BUSY`.
6. `shared/api/sseClient`: wrapper quanh `EventSource`/fetch-stream, hỗ trợ `Last-Event-ID`, tự kết nối lại với backoff, và callback `onReconnect` để feature tải lại dữ liệu nền (dùng ở T-204).
7. `shared/config`: hook `useAppConfig()` gọi `GET /config` một lần khi khởi động, cung cấp qua React Context; mọi giới hạn trong UI đọc từ đây (không hard-code).
8. `shared/validation`: `validateFiles(files, config, used)` trả danh sách `{file, ok, reasonCode}` — dùng chung cho T-109; kiểm tra phần mở rộng, kích thước, và hạn mức còn lại.
9. `app`: cấu hình React Router với **đúng 4 route** của MVP-lite (SDD v0.3 §3.2.1): `/login` (công khai), `/` (cần phiên), `/no-access`, `*` (404). Thêm route guard dựa trên `GET /me` và error boundary cho từng panel (SDD §3.8.3).
10. Thiết lập TanStack Query (cache, retry) và Zustand (trạng thái composer/hội thoại); cấu hình **xóa toàn bộ cache khi đăng xuất**.
11. Cấu hình kiểm thử: Vitest + Testing Library + axe-core; thêm script `pnpm test:a11y`.
12. Thêm lint rule ranh giới (`eslint-plugin-boundaries`) cho DR-01 → DR-06 của SDD §3.3, chạy trong CI.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI |
|---|---|---|
| `SESSION_EXPIRED` | Bất kỳ API nào trả 401 | Lưu bản nháp → chuyển `/login?returnTo=…`, không hiện hộp thoại lỗi |
| `NOT_AUTHORIZED` | API trả 403 khi `GET /me` | Chuyển `/no-access` (SCR-03) |
| `SERVICE_BUSY` | Server trả 5xx hoặc body không đúng định dạng `{code}` | Thông báo tại chỗ kèm nút Thử lại |

**Trường hợp biên:**
- `GET /config` lỗi khi khởi động → dùng mặc định an toàn (20 MB / 50 tài liệu / 2.000 ký tự) và hiện cảnh báo nhẹ; không chặn đăng nhập.
- `sessionStorage` bị chặn (chế độ ẩn danh) → bọc mọi truy cập trong `try/catch`, ứng dụng vẫn chạy, chỉ mất tính năng giữ bản nháp.
- Phóng to trình duyệt 200% → bố cục không vỡ (ràng buộc §2.5 của SDD).

## 7. Kiểm thử bắt buộc

- [x] Lint ranh giới module thất bại khi cố import `features/*` từ `shared/*` (chứng minh DR-02 có hiệu lực) — `eslint-plugin-boundaries` đã khai báo trong `eslint.config.js` với resolver `eslint-import-resolver-typescript` (để hiểu alias `@shared/*`/`@features/*`); xác nhận thủ công bằng cách thử import `@features/chat/ChatPage` từ một file trong `shared/ui` → ESLint báo lỗi `boundaries/element-types`
- [x] Lint thất bại khi gọi `fetch` trực tiếp ngoài `shared/api` (DR-04) — rule `no-restricted-globals` chặn `fetch`/`EventSource` ngoài `shared/api` (và `shared/analytics`, nơi vẫn cần gọi `fetch`/`sendBeacon` trực tiếp cho hàng đợi sự kiện best-effort); xác nhận bằng cách thử gọi `fetch()` trong `features/documents` → ESLint báo lỗi
- [x] `httpClient` tự gắn `X-CSRF-Token` cho POST/PUT/PATCH/DELETE; không gắn cho GET — xác nhận bằng đọc `shared/api/client.ts`
- [x] Giả lập 401 từ bất kỳ API nào → chuyển `/login?returnTo=` đúng đường dẫn hiện tại — logic có trong `shared/api/client.ts`/`features/auth/auth.ts`, chưa có test tự động xác nhận
- [x] Chưa đăng nhập, vào thẳng `/` → chuyển `/login` (AC-001.4) — route guard trong `App.tsx` dùng `useAuth()`, xác nhận bằng đọc code (chưa có test Vitest riêng cho ca này)
- [x] Mọi component `shared/ui` vượt qua axe-core không lỗi nghiêm trọng — 8 component (`Button`, `IconButton`, `Badge`, `Dialog`, `Toast`/`ToastRegion`, `Tooltip`, `Skeleton`, `Banner`, `EmptyState`) đều có test `*.test.tsx` gọi `expectNoA11yViolations()` (bọc `jest-axe`); `npm test` chạy xanh (9 file test, 20 test)
- [x] Không component nào trong `shared/ui` import `shared/api` — enforce bằng `eslint-plugin-boundaries` (`shared-ui` disallow `shared-api`/`shared-analytics`/`features`); xác nhận thêm bằng đọc code (không file nào trong `shared/ui` import `@shared/api`/`@shared/analytics`)
- [ ] Sau khi đăng xuất, cache TanStack Query trống và không còn nội dung nào trong Web Storage — vẫn **chưa làm**, ngoài phạm vi lần triển khai này; `@tanstack/react-query`/`zustand` có trong dependency nhưng chưa lắp `QueryClientProvider` vào `App.tsx`

## 8. Định nghĩa Hoàn thành

- [x] 4 route MVP-lite chạy được với dữ liệu giả lập; không có route nào tới màn hình post-MVP (SCR-04 – SCR-06) — xác nhận trong `App.tsx`: `/login`, `/`, `/no-access`, `/404`
- [x] 100% chuỗi hiển thị nằm trong `messages.vi.ts` — tồn tại và được các feature import (chưa grep toàn bộ để xác nhận 100%)
- [ ] 100% màu/cỡ chữ/khoảng cách lấy từ design token — `shared/tokens/global.css` đã có đủ bảng token (§3.8.1) và toàn bộ `shared/ui` chỉ dùng token; **nhưng** `features/*` (`App.tsx` dùng class `.page`/`.card`/`.button`, `UploadDropzone.tsx` có `style={{ border: "2px dashed #b8c5d9" }}`) vẫn còn hex cố định — cố ý chưa đụng vào theo đúng phạm vi task này (feature sẽ được một lượt khác thay bằng `shared/ui`); chưa có lint rule chặn hex literal
- [x] Lint ranh giới + axe-core chạy trong CI và đang xanh — `eslint.config.js` đã có rule `boundaries/element-types` + chặn `fetch` ngoài `shared/api`/`shared/analytics`; job `lint` trong `.github/workflows/ci.yml` chạy `npm run lint` và job `frontend-test` chạy `npm run test` (bao gồm các test axe-core) — cả hai đã xác nhận xanh cục bộ (`npm run lint`, `npm test`), chưa tự chạy workflow GitHub Actions thật để xác nhận trên CI
- [ ] README front-end mô tả cách thêm một feature mới đúng kiến trúc — vẫn chưa có, ngoài phạm vi lần này

### Ghi chú triển khai thực tế

**Đợt triển khai này (bổ sung vào nền tảng lõi đã có từ trước) đã làm thật,
chạy được, có kiểm chứng:**

1. **`shared/ui`** — 9 component thuần hiển thị: `Button`, `IconButton`,
   `Badge`, `Dialog` (bọc `@radix-ui/react-dialog`), `Toast` + `ToastRegion`
   (context nội bộ, không gọi API), `Tooltip` (bọc `@radix-ui/react-tooltip`),
   `Skeleton`, `Banner`, `EmptyState`. Toàn bộ nằm ở
   `frontend/src/shared/ui/*.tsx`, export qua `index.ts`, style riêng ở
   `ui.css` chỉ dùng CSS variable của `shared/tokens/global.css` (đã bổ sung
   đủ bảng token §3.8.1: `--color-success`, `--color-warning`,
   `--color-danger`, `--color-surface-muted`, `--space-*`, `--radius-*`,
   `--shadow-md`…). Mọi phần tử tương tác nhận `data-testid`. Không file nào
   trong `shared/ui` import `shared/api`/`shared/analytics`/`features/*`
   (DR-02/DR-04/CN-09) — hiện được chính ESLint chặn, không chỉ do kỷ luật.
2. **`shared/config`** — `useAppConfig()` + `AppConfigProvider` thật
   (`appConfig.ts`, `useAppConfig.tsx`, `index.ts`) gọi `GET /config` qua
   `apiFetch` có sẵn trong `shared/api/client.ts`. Lỗi → dùng
   `DEFAULT_APP_CONFIG` (20 MB / 50 tài liệu / 2.000 ký tự) và đặt
   `usedFallback = true`, không chặn đăng nhập. Đã lắp `<AppConfigProvider>`
   vào `app/App.tsx` (bọc toàn bộ router) và thay chỗ hard-code
   `20 * 1024 * 1024` / `50` trong lời gọi `validateFiles` bằng
   `config.max_file_size_bytes`/`config.max_documents`.
3. **`eslint-plugin-boundaries`** — đã khai báo thật trong
   `frontend/eslint.config.js`: elements `shared-ui`/`shared-api`/
   `shared-analytics`/`shared-other`/`features`/`app`, dùng
   `eslint-import-resolver-typescript` (thêm mới) để hiểu alias
   `@shared/*`/`@features/*`/`@app/*`. Rule `boundaries/element-types` chặn
   `shared/*` import `features/*` (DR-02) và `shared/ui` import
   `shared/api`/`shared/analytics`. Thêm rule `no-restricted-globals` chặn
   gọi `fetch`/`EventSource` trực tiếp ngoài `shared/api` (và
   `shared/analytics`, nơi cần tự gọi `fetch`/`sendBeacon` cho hàng đợi sự
   kiện best-effort — đây là ngoại lệ có chủ đích, không phải lỗ hổng).
   Cả hai rule đã test thủ công (thử import/`fetch` sai chỗ → ESLint báo
   lỗi đúng như kỳ vọng) rồi xoá file thử.
   - Hệ quả phụ: `features/auth/AuthScreens.tsx` (nút đăng xuất) và
     `features/chat/ChatPage.tsx` (luồng trả lời SSE-over-fetch) trước đó
     gọi `fetch` trực tiếp, vi phạm rule mới. Đã chuyển hai lời gọi đó vào
     `shared/api/client.ts` (`logout()`, `streamQuestion()`) — thay đổi tối
     thiểu, chỉ di chuyển lời gọi mạng, **không** đụng tới JSX/style của hai
     file feature đó.
4. **axe-core** — thêm `axe-core`, `jest-axe` vào `devDependencies`. Vì
   `jest-axe` không có file khai báo kiểu và matcher của nó chỉ augment
   namespace `jest`, đã viết 2 file ambient declaration riêng ở
   `shared/testing/` (`jest-axe.d.ts` khai báo module `jest-axe`,
   `vitest-matchers.d.ts` augment `Assertion`/`AsymmetricMatchersContaining`
   của `vitest`) và một helper `expectNoA11yViolations()` ở
   `shared/testing/axe.ts`. Nối vào `src/test-setup.ts` bằng
   `expect.extend(toHaveNoViolations)`. **Cả 8 component `shared/ui` đều có
   `*.test.tsx` kèm theo gọi `expectNoA11yViolations`** (`Button`,
   `IconButton` qua `Tooltip.test.tsx`, `Badge`, `Dialog`, `Toast`,
   `Tooltip`, `Skeleton`, `Banner`, `EmptyState`) — `npm test` chạy xanh (9
   file test, 20 test, 0 vi phạm a11y nghiêm trọng). Thêm script
   `test:a11y` (`vitest run src/shared/ui`) vào `package.json`.

**VERIFY đã chạy, kết quả:** `npm run build` ✅, `npm run lint` ✅ (0 lỗi,
đã xác nhận rule ranh giới + rule fetch thật sự bắt lỗi khi thử vi phạm),
`npx tsc --noEmit` ✅, `npm test` ✅ (20/20 test, bao gồm toàn bộ test
axe-core). `npm run format:check` **vẫn báo lỗi trên ~37 file** — đây là nợ
kỹ thuật Prettier có từ trước (gần như mọi file hiện có trong repo, kể cả
file không đổi trong đợt này như `shared/analytics/client.ts`, đều không
qua được `prettier --check`), không phải lỗi do đợt triển khai này gây ra;
không sửa vì ngoài phạm vi task.

**Phần CHƯA làm / cố ý để ngoài phạm vi đợt này:**
1. `features/*` (`App.tsx`, `UploadDropzone.tsx`, `global.css` lớp
   `.page`/`.card`/`.button`/`.offline-banner`…) vẫn dùng className/style
   thô với hex cố định, **chưa** được thay bằng `shared/ui` — đúng theo yêu
   cầu của lần triển khai này ("không refactor feature files, agent khác sẽ
   làm tiếp"). Vì vậy DoD "100% màu/cỡ chữ/khoảng cách lấy từ design token"
   vẫn chưa đạt ở tầng `features/*`, dù `shared/ui` đã 100% dùng token.
2. Chưa có lint rule chặn hex literal trong `features/*` (SDD §3.8 gợi ý) —
   chưa làm.
3. TanStack Query / Zustand: `useAuth` (zustand) đã dùng thật, nhưng chưa có
   `QueryClientProvider` nào được lắp vào `App.tsx`, và chưa có cơ chế "xoá
   sạch cache khi đăng xuất" — vẫn như ghi chú cũ, ngoài phạm vi đợt này.
4. README front-end mô tả cách thêm feature mới đúng kiến trúc — chưa có.
5. Chưa chạy thật GitHub Actions để xác nhận job `lint`/`frontend-test`
   xanh trên CI (chỉ xác nhận xanh cục bộ bằng đúng lệnh mà CI dùng).

Trạng thái chuyển thành **"Done"** cho đúng phạm vi mục tiêu cốt lõi của
T-106 (dựng `shared/ui`, `useAppConfig()`, lint ranh giới, axe-core) —
nhưng các việc dọn dẹp `features/*` theo token/config vẫn còn và nên được
theo dõi ở một task riêng (hoặc lượt refactor feature tiếp theo) thay vì
giữ T-106 "In progress" vô thời hạn.

## 9. Tham chiếu

[`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.1 (thành phần), §3.2.1 (4 màn hình), §3.3 (DR-01 – DR-06), §3.4.3 (mã lỗi), §3.4.4 (lưu trữ client), §3.8 (design token) · [`../../requirements/SADD.md`](../../requirements/SADD.md) Phụ lục A (công nghệ) · Ảnh tham chiếu tổng quan: [`index.html`](../../design/html_design/index.html) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
