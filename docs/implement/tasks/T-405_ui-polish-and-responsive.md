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
| Trạng thái | To do (chưa bắt đầu — phụ thuộc `shared/ui` của T-106) |

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

- [ ] **ER-09:** nhập 2.001 ký tự → bộ đếm đỏ, nút Gửi khóa; xóa còn 1.999 → mở lại
- [ ] **NE-03:** ngắt mạng (DevTools offline) khi đang soạn dở → banner hiện, nút Gửi khóa, nội dung **không mất**; bật lại mạng → gửi được ngay
- [ ] **AC-009.3:** ở 900px, nhấn "Tài liệu" → ngăn trượt mở; `Esc` và nhấn scrim đều đóng được
- [ ] **IR-01:** trong lúc streaming, DOM **không** chứa `CitationList`; sau `done` thì xuất hiện
- [ ] Toàn bộ 7 trạng thái `Composer` ở §3 có ca kiểm thử riêng, đúng thứ tự ưu tiên
- [ ] axe-core chạy trên SCR-01, SCR-02, SCR-03, SCR-07 → 0 lỗi mức `serious`/`critical`
- [ ] Zoom 200% ở 1280px và chiều rộng 360px → không có thanh cuộn ngang
- [ ] Điều hướng toàn bộ luồng chính **chỉ bằng bàn phím** (Tab/Enter/Esc) không bị kẹt focus
- [ ] Đối chiếu ảnh: [`SCR-02_22_offline-banner.png`](../../design/html_design/SCR-02_22_offline-banner.png), [`SCR-02_25_question-too-long.png`](../../design/html_design/SCR-02_25_question-too-long.png), [`SCR-02_26_tablet-drawer.png`](../../design/html_design/SCR-02_26_tablet-drawer.png), [`SCR-02_23_user-menu.png`](../../design/html_design/SCR-02_23_user-menu.png), [`SCR-02_24_streaming.png`](../../design/html_design/SCR-02_24_streaming.png)

## 8. Định nghĩa Hoàn thành

- [ ] 5 ảnh thiết kế ở trên khớp với bản chạy thật tại 1280px (và 900px cho ngăn trượt)
- [ ] axe-core sạch lỗi nghiêm trọng, chạy tự động trong CI
- [ ] Mọi phần tử tương tác có `data-testid` và dùng được bằng bàn phím
- [ ] Không còn mã màu cố định trong component (lint kiểm tra token)
- [ ] Menu người dùng **không** còn mục post-MVP (Báo cáo tuần / Chấm điểm / Quản lý quyền)
- [ ] Chạy đúng trên Chrome, Edge, Firefox (2 phiên bản mới nhất)

### Ghi chú triển khai thực tế

Không tìm thấy bằng chứng triển khai nào trong `App.tsx`/`ChatPage.tsx`/
`UploadDropzone.tsx` cho: bộ đếm ký tự ER-09, khóa composer khi mất mạng
(`ChatPage` không đọc `navigator.onLine` — chỉ `UploadDropzone` có), ngăn
trượt responsive 900px, ẩn `CitationList` khi streaming (thực ra đã đúng
nhờ thứ tự SSE, xem T-306), axe-core, menu người dùng. Task này phụ thuộc
trực tiếp vào `shared/ui` (T-106) chưa tồn tại nên giữ nguyên "To do".

## 9. Tham chiếu

- [SDD UI/UX §2.4 – §2.5 (chất lượng UX), §3.5.2 (phím tắt), §3.7.3 (trạng thái Composer), §3.8.1 (token)](../../design/SDD_UI_UX_Blueprint.md)
- [PRD §4.2 — ER-09, NE-03, ES-01 – ES-05](../../requirements/PRD.md)
- [User Stories — US-009 (AC-009.3), US-011](../../design/User_Stories.md)
- Ảnh thiết kế: thư mục [`html_design/`](../../design/html_design/)
- [implement_plan.md §5 Sprint 4](../implement_plan.md)
