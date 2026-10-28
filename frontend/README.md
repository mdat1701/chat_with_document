# Frontend — Chat với tài liệu

SPA React 18 + TypeScript + Vite, kiến trúc **feature-sliced** theo
[SDD UI/UX §3.1 – §3.3](../docs/design/SDD_UI_UX_Blueprint.md). Tài liệu
này mô tả cấu trúc thư mục, ranh giới module bắt buộc, và cách thêm một
feature mới đúng kiến trúc (T-106 §8 DoD).

## Cấu trúc thư mục

```
src/
  app/        # router, provider toàn cục (AppConfig, Toast), error boundary, layout (AppHeader, UserMenu)
  features/   # auth | documents | chat — logic + UI riêng của từng tính năng
  shared/
    tokens/     # CSS variables (màu, chữ, khoảng cách, bo góc, shadow) — nguồn duy nhất của design token
    ui/         # Component hiển thị thuần (Button, Dialog, Drawer, Toast, Tooltip, Skeleton, Banner, EmptyState...)
    api/        # httpClient (fetch + CSRF + ánh xạ lỗi) và sseClient — nơi DUY NHẤT được gọi fetch/EventSource
    analytics/  # Client gửi sự kiện analytics — ngoại lệ thứ hai được phép gọi fetch (sendBeacon)
    i18n/       # messages.vi.ts — toàn bộ chuỗi hiển thị (UX-07, giao diện luôn tiếng Việt)
    validation/ # validateFiles() và các hàm kiểm tra phía client dùng chung
    config/     # useAppConfig() — nạp GET /config một lần, cung cấp qua Context
    testing/    # Helper test dùng chung (ví dụ expectNoA11yViolations() cho axe-core)
```

Mỗi thư mục con có `README.md` riêng mô tả chi tiết trách nhiệm của nó.

## Ranh giới module bắt buộc (SDD §3.3, DR-01 – DR-06)

Các luật này được **ESLint thực thi thật** (`eslint.config.js`,
`eslint-plugin-boundaries`) — vi phạm sẽ làm `npm run lint` thất bại,
không chỉ là quy ước bằng lời:

- `shared/*` **không được** import `features/*` (phụ thuộc chỉ một
  chiều: `features` → `shared`, không bao giờ ngược lại).
- Chỉ `shared/api` (và `shared/analytics`, cho hàng đợi sự kiện
  best-effort) được gọi `fetch`/`EventSource` trực tiếp. Mọi lời gọi
  mạng khác — kể cả trong `features/*` — phải đi qua hàm trong
  `shared/api/client.ts`.
- Component trong `shared/ui` **không** gọi API, không import
  `shared/api`/`shared/analytics`/`features/*` — chỉ nhận dữ liệu qua
  props và hiển thị.
- Mọi chuỗi hiển thị nằm trong `shared/i18n/messages.vi.ts`, không
  hard-code trong JSX.
- Mọi giới hạn cấu hình (kích thước tệp, số tài liệu tối đa, độ dài câu
  hỏi...) đọc qua `useAppConfig()`, không hard-code trong component.
- Mọi màu sắc/khoảng cách lấy từ CSS variable trong
  `shared/tokens/global.css`, không dùng mã màu cố định (hex literal)
  trong component.

## Cách thêm một feature mới

1. Tạo thư mục `features/<ten-feature>/` với file `README.md` ngắn mô
   tả trách nhiệm của feature.
2. Lắp UI bằng component có sẵn trong `shared/ui` trước khi tự viết
   component mới — chỉ thêm vào `shared/ui` khi thật sự dùng chung ≥ 2
   feature.
3. Mọi lời gọi API mới thêm vào `shared/api/client.ts` (hàm riêng cho
   từng endpoint), feature chỉ import hàm đó — không tự gọi `fetch`.
4. Thêm chuỗi hiển thị mới vào `shared/i18n/messages.vi.ts`, không viết
   thẳng trong JSX.
5. Nếu feature cần giới hạn cấu hình, đọc qua `useAppConfig()` — không
   hard-code số.
6. Viết test cạnh file nguồn (`*.test.ts`/`*.test.tsx`, Vitest +
   Testing Library); nếu thêm component hiển thị mới vào `shared/ui`,
   bắt buộc có test axe-core (`expectNoA11yViolations()` từ
   `shared/testing/axe.ts`).
7. Chạy `npm run lint && npx tsc -b --noEmit && npm test -- --run &&
   npm run build` trước khi coi là xong — cả 4 lệnh này là bằng chứng
   tối thiểu cho mọi thay đổi frontend trong dự án này (xem cách các
   task T-106 trở đi tự xác minh trong `docs/implement/tasks/`).

## Lệnh thường dùng

| Lệnh | Mục đích |
|---|---|
| `npm run dev` | Chạy dev server (Vite) |
| `npm run build` | `tsc -b` + build production |
| `npm run lint` | ESLint, bao gồm luật ranh giới module |
| `npm run typecheck` | `tsc -b --noEmit` |
| `npm test` | Chạy toàn bộ test (Vitest) |
| `npm run test:a11y` | Chỉ chạy test axe-core trong `shared/ui` |
| `npm run format:check` | Kiểm tra Prettier (hiện còn nợ kỹ thuật trên một số file cũ, xem T-106) |

## Tài liệu liên quan

- [SDD UI/UX Blueprint](../docs/design/SDD_UI_UX_Blueprint.md) — nguồn
  thiết kế gốc cho mọi quyết định kiến trúc ở trên.
- [docs/implement/tasks/](../docs/implement/tasks/) — từng task T-1xx
  trở đi có "Ghi chú triển khai thực tế" ghi rõ đã làm gì, xác minh thế
  nào, còn thiếu gì — tài liệu đáng tin nhất về trạng thái thật của FE.
