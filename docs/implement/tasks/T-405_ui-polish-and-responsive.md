# T-405 — Hoàn thiện giao diện, trạng thái biên và đáp ứng kích thước màn hình

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 4 |
| Story | Hỗ trợ US-003, US-009, US-011 (không sở hữu story riêng) |
| Epic | EP-02, EP-03 |
| Module (SADD §2.2.1) | `shared/ui`, `features/documents`, `features/chat` |
| API liên quan | Không gọi API mới |
| Vai trò chính | FE (chính) + QA |
| Ước lượng | 3 ngày công |
| Phụ thuộc | T-205 (thư viện tài liệu), T-305 (`Composer`), T-306 (`AnswerMessage`) |
| Trạng thái | In progress (xem "Ghi chú triển khai thực tế" — còn thiếu kiểm thử đa trình duyệt thật, đối chiếu ảnh thiết kế bằng mắt, và phím tắt `Ctrl+Shift+O`/mũi tên) |

## 1. Mục tiêu

Khép lại các trạng thái giao diện còn thiếu sau Sprint 3 và đưa SPA đạt chuẩn khả năng truy cập/đáp ứng của SDD §2.4 – §2.5: con trỏ streaming, bộ đếm ký tự, banner ngoại tuyến, ngăn trượt tài liệu dưới 1024px, menu người dùng, vùng chạm và zoom.

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Nội dung |
|---|---|
| AC-009.3 | Màn hình rộng < 1024px → nhấn nút "Tài liệu" thì thư viện mở dạng **ngăn trượt** (UX-01) |
| ER-09 | Câu hỏi > `max_question_length` (DF-07 = 2.000) → bộ đếm ký tự **chuyển đỏ**, nút Gửi bị khóa |
| NE-03 | Mất mạng → banner "Bạn đang ngoại tuyến"; vùng tải lên và nút Gửi bị khóa; **bản nháp câu hỏi được giữ** |
| IR-01 | Khi câu trả lời đang `streaming` → **ẩn** thẻ nguồn; chỉ hiện khi `complete` |
| IX-07 / WCAG 2.1 AA | Mọi trạng thái có icon **và** chữ; axe-core không còn lỗi nghiêm trọng |
| SDD §2.5 | Vùng chạm ≥ 44×44px khi < 1024px (≥ 32×32px trên desktop); zoom 200% không vỡ bố cục |

## 3. Hợp đồng API / giao diện

Không có API mới. Bảng trạng thái `Composer` phải cài đúng **theo thứ tự ưu tiên** (SDD §3.7.3):

| Thứ tự | Điều kiện | Trạng thái | Tooltip / gợi ý |
|---|---|---|---|
| 1 | Đang ngoại tuyến | Khóa toàn bộ | "Bạn đang ngoại tuyến" |
| 2 | Không có tài liệu nào | Khóa | "Tải tài liệu lên để bắt đầu hỏi" (ES-01) |
| 3 | Mọi tài liệu đang xử lý | Khóa | "Tài liệu đang được xử lý, vui lòng chờ…" (ES-02) |
| 4 | Mọi tài liệu đều lỗi | Khóa | "Không có tài liệu nào sẵn sàng" (ES-03) |
| 5 | Đang chờ câu trả lời trước | Khóa **nút Gửi**, vẫn gõ được | "Đang trả lời câu hỏi trước…" |
| 6 | Ô trống hoặc > DF-07 ký tự | Khóa nút Gửi | Bộ đếm chuyển đỏ khi vượt giới hạn |
| 7 | Còn lại | Sẵn sàng | — |

Điểm ngắt màn hình (SDD §3.8.1): `sm` 360 · `md` 768 · `lg` 1024 · `xl` 1280.

## 4. Thay đổi dữ liệu

Không có thay đổi CSDL. Chỉ dùng `localStorage` cho **tùy chọn giao diện không chứa nội dung** (ví dụ ngăn tài liệu đang mở hay đóng) theo SDD §3.4.4; bản nháp câu hỏi dùng `sessionStorage` (đã làm ở T-107, phụ thuộc D-04).

## 5. Các bước triển khai

1. **Con trỏ streaming:** trong `AnswerMessage`, khi `phase = 'streaming'` hiển thị con trỏ nhấp nháy ở cuối nội dung; **ẩn** `CitationList` cho tới khi `phase = 'complete'` (IR-01). Dùng `prefers-reduced-motion` để tắt nhấp nháy khi người dùng yêu cầu giảm chuyển động.
2. **Bộ đếm ký tự:** `CharCounter` hiển thị `{len}/2.000` lấy ngưỡng từ `GET /config` (không hard-code); khi `len > max` thì đổi sang `--color-danger`, thêm `aria-invalid` cho textarea và khóa nút Gửi (ER-09).
3. **`OfflineBanner`:** lắng nghe sự kiện `online`/`offline` của `navigator`; khi offline → hiện banner cố định, khóa `UploadDropzone` và nút Gửi, **giữ nguyên** nội dung đang soạn; khi online trở lại thì tự ẩn và mở khóa, không mất bản nháp (NE-03).
4. **Ngăn trượt tài liệu (< 1024px):** `DocumentPanel` chuyển sang `position: absolute` + `transform: translateX(-100%)`, mở bằng nút "Tài liệu" ở header; thêm lớp phủ (scrim) nhấn để đóng; `Esc` đóng ngăn; **bẫy focus** trong ngăn khi đang mở (Radix primitives).
5. **Menu người dùng:** hoàn thiện `AppHeader` menu — chỉ gồm thông tin tài khoản, **Trợ giúp**, **Đăng xuất** (SDD v0.3 — không còn mục Báo cáo tuần/Chấm điểm/Quản lý quyền). Điều hướng bàn phím bằng mũi tên, `Esc` đóng.
6. **Phím tắt (SDD §3.5.2):** `Enter` gửi, `Shift+Enter` xuống dòng, `/` đưa con trỏ vào ô câu hỏi khi focus không nằm trong ô nhập, `Ctrl+Shift+O` tạo cuộc trò chuyện mới, `Esc` đóng hộp thoại, `↑`/`↓` duyệt danh sách tài liệu.
7. **Vùng chạm & zoom:** đặt kích thước tối thiểu 44×44px cho mọi nút khi `< 1024px` (32×32px desktop); kiểm tra bố cục ở zoom 200% và ở chiều rộng 360px → **không có thanh cuộn ngang**.
8. **Khả năng truy cập:** `aria-live="polite"` cho `MessageList` thông báo "Đã có câu trả lời"; mọi nút bị vô hiệu có tooltip giải thích lý do; chạy axe-core trong CI và xử lý hết lỗi mức nghiêm trọng.
9. **Rà soát token:** bảo đảm không component nào dùng mã màu cố định — toàn bộ lấy từ design token (SDD §3.8.1), kiểm tra bằng lint.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Mất mạng **giữa lúc** đang stream câu trả lời | Hiển thị `ANSWER_INTERRUPTED` + nút Thử lại, **ẩn thẻ nguồn** (IR-01); banner ngoại tuyến hiện song song |
| Người dùng dán 5.000 ký tự | Bộ đếm đỏ ngay, nút Gửi khóa; **không** tự cắt bớt nội dung của người dùng |
| Mở ngăn tài liệu rồi xoay ngang máy tính bảng lên ≥ 1024px | Ngăn trượt tự chuyển về bố cục 2 cột, không kẹt trạng thái "đang mở" |
| `navigator.onLine` báo online nhưng API vẫn lỗi | Banner ngoại tuyến **không** hiện; dùng thông báo lỗi theo `ErrorCode` tại chỗ (CN-05) |
| `localStorage` bị chặn (chế độ riêng tư) | Bọc try/catch; giao diện vẫn chạy với giá trị mặc định (SDD §3.4.4) |
| Người dùng bật `prefers-reduced-motion` | Tắt nhấp nháy con trỏ và hiệu ứng trượt ngăn |

## 7. Kiểm thử bắt buộc

- [x] **ER-09:** nhập 2.001 ký tự → bộ đếm đỏ, nút Gửi khóa; xóa còn 1.999 → mở lại (đã có từ T-305, kiểm bằng `ChatPage.test.tsx`; phiên này thêm `aria-invalid` cho textarea)
- [x] **NE-03:** ngắt mạng khi đang soạn dở → banner hiện (`OfflineBanner`, sticky, `role="status"`), nút Gửi khóa (`disabledReason="offline"`), `UploadDropzone` khóa; nội dung **không mất** (state React của `ChatPageInner` không unmount khi offline — đã kiểm bằng đọc code, chưa có test tự động riêng cho kịch bản DevTools offline thật)
- [x] **AC-009.3:** dưới 1024px, nhấn "Tài liệu" → `Drawer` (Radix Dialog neo trái) mở; `Esc` và nhấn scrim đều đóng được (hành vi chuẩn của Radix, có smoke test `Drawer.test.tsx`); **chưa** kiểm bằng trình duyệt thật ở đúng 900px (chỉ kiểm bằng đọc CSS/logic `useIsDesktop`)
- [x] **IR-01:** trong lúc streaming, DOM **không** chứa `CitationList`; sau `done` thì xuất hiện (đã đúng từ T-306 nhờ thứ tự SSE, xác nhận lại trong phiên này)
- [x] Toàn bộ 7 trạng thái `Composer` ở §3 đối chiếu lại với bảng ưu tiên — khớp hoàn toàn (tooltip Việt hoá đúng từng dòng), có ca kiểm thử trong `ChatPage.test.tsx`
- [x] axe-core chạy trên các component mới (`OfflineBanner`, `Drawer`) + toàn bộ `shared/ui` hiện có → 0 lỗi mức `serious`/`critical` trong các test đã chạy; **chưa** chạy axe-core trên toàn trang SCR-01/02/03/07 thực sự (không có browser thật trong sandbox này, chỉ chạy `jest-axe` trên cây DOM từng component)
- [ ] Zoom 200% ở 1280px và chiều rộng 360px — **không thể xác minh bằng trình duyệt thật** trong sandbox này; chỉ xác minh được qua đọc CSS: không có `width` cố định lớn hơn viewport trong `chat.css`/`documents.css`/`ui.css`, `body { min-width: 320px }`, không phát hiện phần tử có khả năng gây tràn ngang ở 360px
- [ ] Điều hướng toàn bộ luồng chính chỉ bằng bàn phím — xác minh được cho `Dialog`/`Drawer`/`Tooltip`/`UserMenu` (đều dùng Radix UI, có bẫy focus + `Esc` sẵn có); **chưa** chạy kiểm thử thủ công Tab-qua-toàn-trang bằng trình duyệt thật
- [ ] Đối chiếu ảnh: [`SCR-02_22_offline-banner.png`](../../design/html_design/SCR-02_22_offline-banner.png), [`SCR-02_25_question-too-long.png`](../../design/html_design/SCR-02_25_question-too-long.png), [`SCR-02_26_tablet-drawer.png`](../../design/html_design/SCR-02_26_tablet-drawer.png), [`SCR-02_23_user-menu.png`](../../design/html_design/SCR-02_23_user-menu.png), [`SCR-02_24_streaming.png`](../../design/html_design/SCR-02_24_streaming.png) — **chưa đối chiếu bằng mắt** (không có trình duyệt/renderer ảnh trong sandbox này)

## 8. Định nghĩa Hoàn thành

- [ ] 5 ảnh thiết kế ở trên khớp với bản chạy thật tại 1280px (và 900px cho ngăn trượt) — **chưa làm được**, cần máy có trình duyệt
- [x] axe-core sạch lỗi nghiêm trọng cho các component mới/đã sửa (chạy trong `npm test`, không phải CI riêng — CI hiện tại đã gọi `npm test` nên coi như "chạy trong CI" theo nghĩa rộng, nhưng **chưa** có bước axe quét toàn trang)
- [x] Mọi phần tử tương tác mới (`OfflineBanner`, nút "Tài liệu", `Drawer`, `UserMenu` và các mục trong đó) có `data-testid` và dùng được bằng bàn phím (Radix UI lo phần focus/Esc)
- [x] Không còn mã màu cố định (hex) trong `features/*` và `shared/ui` — đã rà soát bằng `grep -rn "#[0-9a-fA-F]{3,6}"` loại trừ `global.css`, không còn kết quả; token `--color-skeleton-highlight` và `--color-overlay` được thêm vào `global.css` để thay cho các hex còn sót trong `ui.css`
- [x] Menu người dùng (`UserMenu`) chỉ gồm email tài khoản (nhãn), "Trợ giúp", "Đăng xuất" — không có mục post-MVP
- [ ] Chạy đúng trên Chrome, Edge, Firefox (2 phiên bản mới nhất) — **không thể kiểm chứng**, sandbox này không có trình duyệt thật để chạy cross-browser

### Ghi chú triển khai thực tế

Đọc lại code trước khi làm cho thấy phần lớn §5 bước 1–2 (con trỏ streaming,
ẩn `CitationList` khi `streaming`, bộ đếm ký tự, 7 trạng thái `Composer` theo
đúng thứ tự ưu tiên SDD §3.7.3 với tooltip Việt hoá khớp từng dòng) **đã được
làm đúng** trong các phiên T-305/T-306 trước đó — không phải "chưa bắt đầu"
như ghi chú cũ của task này nói. Phiên này bổ sung phần còn thiếu thật sự:

- `shared/ui/OfflineBanner.tsx` — banner `position: sticky` (không dùng
  `fixed` tuyệt đối để tránh che nội dung phía dưới mà không có đệm bù),
  `role="status"`, thay cho `<div className="offline-banner">` ad-hoc cũ
  trong `App.tsx`.
- `shared/ui/Drawer.tsx` — bọc `@radix-ui/react-dialog` neo trái (bẫy focus,
  `Esc`, scrim-close có sẵn từ Radix), dùng cho thư viện tài liệu dưới
  1024px (AC-009.3).
- `app/useIsDesktop.ts` — hook `matchMedia('(min-width: 1024px)')` quyết
  định bố cục 2 cột (`app-layout--two-col`) hay ngăn trượt; khi xoay ngang
  qua lại ngưỡng 1024px, nhánh ngăn trượt bị gỡ hẳn khỏi cây React (không
  chỉ ẩn CSS) nên không có chuyện kẹt trạng thái "đang mở" nêu ở §6.
- `app/UserMenu.tsx` — dùng `@radix-ui/react-dropdown-menu` (đã có sẵn
  trong `package.json`, không thêm phụ thuộc mới); 3 mục: email (nhãn,
  `DropdownMenu.Label`), "Trợ giúp" (hiện tạm mở `mailto:` placeholder vì
  chưa có trang trợ giúp thật — cần thay bằng đường dẫn thật khi có), "Đăng
  xuất" (gọi `logout()` sẵn có trong `shared/api/client.ts`, giữ nguyên quy
  ước xóa draft trước khi điều hướng).
- `shared/tokens/global.css` — thêm token `--color-skeleton-highlight`,
  `--color-overlay`, và 4 biến `--breakpoint-*` (tài liệu hoá điểm ngắt SDD
  §3.8.1); thay toàn bộ hex-literal còn sót trong `.card`/`.button`/
  `.document-row`/skeleton shimmer bằng `var(--...)`. `grep` xác nhận
  `features/*` và `shared/ui` (ngoài `global.css`) không còn hex-literal.
- `Composer.tsx` — thêm `aria-invalid` vào textarea khi vượt quá
  `max_question_length` (trước đó chỉ đổi màu bộ đếm, chưa gắn ARIA).
- Test mới: `OfflineBanner.test.tsx`, `Drawer.test.tsx` (mỗi file có 1 ca
  axe-core qua `expectNoA11yViolations`, theo đúng khuôn mẫu các test
  `shared/ui` khác).

**Chưa làm / không thể làm trong phiên này (nêu rõ để không báo cáo khống):**

1. **Phím tắt** `Ctrl+Shift+O` (cuộc trò chuyện mới) và điều hướng mũi tên
   trong danh sách tài liệu — **chưa cài đặt**, đúng như mục "ưu tiên thấp"
   trong chỉ dẫn của task. `/` để focus ô câu hỏi, `Enter`/`Shift+Enter`,
   `Esc` đóng hộp thoại (qua Radix) đã có sẵn.
2. **Kiểm thử đa trình duyệt** (Chrome/Edge/Firefox) và **đối chiếu 5 ảnh
   thiết kế bằng mắt** — không thể thực hiện trong sandbox này (không có
   trình duyệt thật/headless browser để chụp màn hình so sánh). Đây là lý
   do chính khiến Định nghĩa Hoàn thành (§8) chưa đạt 100%.
3. **Zoom 200%** và axe-core quét toàn trang (SCR-01/02/03/07) — chỉ kiểm
   chứng được gián tiếp qua đọc CSS và chạy axe-core ở mức component
   (`jest-axe`/`vitest`), không phải trên trang đã render đầy đủ trong
   trình duyệt.
4. `DocumentLibrary`'s `hasMessages` vẫn hard-code `false` (ghi chú cũ từ
   T-205) — ngoài phạm vi T-405, không đụng tới.
5. Không chạy backend thật để kiểm `NE-03` kịch bản "API vẫn lỗi dù
   `navigator.onLine` báo online" — logic hiện tại (banner chỉ dựa vào sự
   kiện `online`/`offline`, lỗi API dùng `ErrorCode` riêng ở `AnswerMessage`)
   đã đúng theo thiết kế nhưng chưa có test tích hợp riêng cho trường hợp
   biên này.

Do còn các khoảng trống trên (đặc biệt là không thể kiểm thử trình duyệt
thật), trạng thái giữ ở **"In progress"**, không đánh dấu "Done".

## 9. Tham chiếu

- [SDD UI/UX §2.4 – §2.5 (chất lượng UX), §3.5.2 (phím tắt), §3.7.3 (trạng thái Composer), §3.8.1 (token)](../../design/SDD_UI_UX_Blueprint.md)
- [PRD §4.2 — ER-09, NE-03, ES-01 – ES-05](../../requirements/PRD.md)
- [User Stories — US-009 (AC-009.3), US-011](../../design/User_Stories.md)
- Ảnh thiết kế: thư mục [`html_design/`](../../design/html_design/)
- [implement_plan.md §5 Sprint 4](../implement_plan.md)
