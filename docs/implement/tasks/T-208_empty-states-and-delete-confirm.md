# T-208 — Trạng thái trống (ES-01 – ES-05), hộp xác nhận xóa & toast

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-003 (ES-01), US-008 (xác nhận xóa, ES-05), US-010 (ES-02/ES-03) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | Front-end `features/documents` + `shared/ui` |
| API liên quan | API-03, API-07 (tiêu thụ; không tạo API mới) |
| Vai trò chính | FE |
| Ước lượng | 2d |
| Phụ thuộc | T-205 (danh sách tài liệu), T-206 (API xóa), T-106 (`shared/ui`: Dialog, Toast, EmptyState) |
| Trạng thái | To do (chỉ có `window.confirm()` tạm thời, chưa có component/trạng thái trống thật) |

## 1. Mục tiêu

Làm cho màn hình **luôn nói rõ người dùng cần làm gì tiếp theo** ở mọi trạng thái rỗng, và đảm bảo thao tác xóa — vốn **không có hoàn tác** — luôn có bước xác nhận rõ ràng (IX-04).

Đây là task hoàn thiện trải nghiệm của EP-02 trước khi chuyển sang luồng hỏi đáp ở Sprint 3.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-008.1 | *Given* một tài liệu ở trạng thái bất kỳ, *When* người dùng nhấn "Xóa", *Then* hệ thống hiển thị hộp xác nhận ghi tên tệp. |
| AC-008.3 | *Given* người dùng nhấn "Hủy" trong hộp xác nhận, *When* hộp đóng lại, *Then* tài liệu vẫn còn nguyên. |
| AC-010.2 | *Given* mọi tài liệu đều đang xử lý, *Then* ô câu hỏi bị khóa kèm gợi ý "Tài liệu đang được xử lý, vui lòng chờ…" và tự mở khi có ít nhất 1 tài liệu ✅ (ES-02). |
| AC-011.3 | *Given* người dùng chưa có tài liệu nào "Sẵn sàng", *When* mở màn hình hỏi đáp, *Then* ô câu hỏi bị vô hiệu hóa kèm gợi ý "Tải tài liệu lên để bắt đầu hỏi". |

## 3. Hợp đồng API / giao diện

**5 trạng thái trống bắt buộc (PRD §4.2):**

| Mã | Điều kiện | Nội dung hiển thị | Ô câu hỏi |
|---|---|---|---|
| ES-01 | `documents.length === 0` | Hướng dẫn 3 bước: ① Tải PDF lên ② Chờ trạng thái ✅ ③ Đặt câu hỏi; nút "Tải tài liệu lên" nổi bật | Khóa — "Tải tài liệu lên để bắt đầu hỏi" |
| ES-02 | Có tài liệu, **tất cả** `processing`/`uploading` | Gợi ý chờ xử lý | Khóa — "Tài liệu đang được xử lý, vui lòng chờ…" |
| ES-03 | Có tài liệu, **tất cả** `failed` | Banner: "Không có tài liệu nào sẵn sàng. Kiểm tra lỗi ở danh sách bên trái." | Khóa — "Không có tài liệu nào sẵn sàng" |
| ES-04 | Có ≥ 1 `ready`, chưa có câu hỏi nào | "Bạn có thể hỏi, ví dụ: …" — **câu mẫu tĩnh** (gợi ý thông minh là P-05, post-MVP) | Mở |
| ES-05 | Vừa xóa tài liệu cuối cùng | Quay về nội dung ES-01, **nhưng giữ nguyên hội thoại cũ** đang hiển thị | Khóa |

**Component (SDD §3.2.3):**

```tsx
<EmptyState variant="ES-01" | "ES-02" | "ES-03" | "ES-04" | "ES-05" />
<DeleteConfirmDialog documentName={name} onConfirm={...} onCancel={...} />
<ToastRegion />   // góc dưới phải, tự ẩn sau 4 giây
```

**Ảnh thiết kế tham chiếu:**
[`SCR-02_01_empty-first-login.png`](../../design/html_design/SCR-02_01_empty-first-login.png) (ES-01) ·
[`SCR-02_04_processing-only.png`](../../design/html_design/SCR-02_04_processing-only.png) (ES-02) ·
[`SCR-02_06_all-failed-banner.png`](../../design/html_design/SCR-02_06_all-failed-banner.png) (ES-03) ·
[`SCR-02_12_ready-suggestions.png`](../../design/html_design/SCR-02_12_ready-suggestions.png) (ES-04) ·
[`SCR-02_18_last-document-deleted.png`](../../design/html_design/SCR-02_18_last-document-deleted.png) (ES-05) ·
[`SCR-02_09_delete-confirm.png`](../../design/html_design/SCR-02_09_delete-confirm.png) (hộp xác nhận)

## 4. Thay đổi dữ liệu

Không đổi schema. Trạng thái trống là **hàm thuần** của dữ liệu đã có:

```ts
function resolveEmptyState(docs: DocumentVM[], messages: MessageVM[]): EmptyStateVariant | null {
  const ready = docs.filter(d => d.status === 'ready');
  if (docs.length === 0) return messages.length > 0 ? 'ES-05' : 'ES-01';
  if (ready.length === 0 && docs.every(d => d.status === 'failed')) return 'ES-03';
  if (ready.length === 0) return 'ES-02';
  if (messages.length === 0) return 'ES-04';
  return null;
}
```

> Dùng **một hàm dẫn xuất duy nhất**, không rải cờ boolean khắp component — tránh lệch trạng thái (CN-10, dễ kiểm thử).

## 5. Các bước triển khai

1. Cài `resolveEmptyState` như hàm thuần trong `features/documents` (hoặc `features/chat` tùy nơi đặt), có unit test riêng cho cả 5 nhánh.
2. `EmptyState` nhận `variant`, render nội dung + chuỗi từ `messages.vi.ts`; mỗi variant phát `empty_state_viewed{state_code}` **một lần mỗi phiên** (dùng `Set` lưu trong store, không `localStorage`).
3. **ES-01:** hướng dẫn 3 bước, nút CTA "Tải tài liệu lên" kích hoạt cùng handler với `UploadDropzone`.
4. **ES-02/ES-03:** khóa composer kèm `disabledReason`; `Composer` hiển thị tooltip giải thích lý do khi hover/focus nút Gửi bị vô hiệu (§2.5 SDD — nút disabled luôn có tooltip).
5. **ES-04:** hiển thị 3 câu hỏi mẫu **tĩnh** (lấy từ `messages.vi.ts`, ví dụ theo persona PER-01 trong PRD); nhấn vào câu mẫu thì điền vào ô câu hỏi (chưa gửi). Ghi chú rõ trong code: gợi ý sinh từ nội dung tài liệu là **P-05, post-MVP**, không làm ở đây.
6. **ES-05:** khi `documents.length === 0` nhưng `messages.length > 0` → hiển thị nội dung ES-01 trong cột trái, **giữ nguyên** `MessageList` bên phải, khóa composer. Đối chiếu với ảnh `SCR-02_18_last-document-deleted.png`.
7. **`DeleteConfirmDialog`** (dùng Radix Dialog để có sẵn focus trap + ARIA):
   - Tiêu đề + nội dung ghi rõ **tên tệp**.
   - **Focus mặc định đặt ở nút "Hủy"** (IX-04 — không đặt vào nút phá hủy).
   - `Esc` đóng hộp thoại; nhấn ra ngoài cũng đóng; cả hai tương đương "Hủy" (AC-008.3).
   - Nút "Xóa" ở trạng thái loading trong lúc chờ `DELETE`; **không** đóng danh sách trước khi có `204` (không optimistic UI).
8. **Toast sau khi xóa thành công:** `ToastRegion` góc dưới phải, nội dung `Đã xóa "<tên tệp>".`, **tự ẩn sau 4 giây**. Toast chỉ dùng cho **xác nhận thao tác**, không dùng cho lỗi cần xử lý (§2.5 SDD).
9. Sau `204`: cập nhật cache danh sách + `DocumentCounter`, rồi chạy lại `resolveEmptyState` (có thể chuyển sang ES-01/ES-05).
10. Thêm `data-testid`: `empty-state`, `delete-confirm`, `delete-cancel`, `delete-submit`, `toast`.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `DOC_NOT_FOUND` (404) | Xác nhận xóa tài liệu đã bị xóa ở tab khác | Đóng hộp thoại, hiện thông báo "Không tìm thấy tài liệu…", làm mới danh sách (không hiện toast thành công) |
| `SESSION_EXPIRED` (401) | Phiên hết hạn khi bấm Xóa | Chuyển `/login?returnTo=/`, giữ bản nháp câu hỏi |
| Lỗi mạng | `DELETE` thất bại | Giữ hộp thoại mở, hiện lỗi tại chỗ kèm nút thử lại — **không** xóa khỏi danh sách |

Trường hợp biên:
- **Nhấn Xóa liên tiếp nhiều lần** → nút chuyển disabled sau lần nhấn đầu, tránh gửi hai request.
- **Tên tệp rất dài trong hộp thoại** → cắt bằng ellipsis giữa chuỗi, giữ phần đuôi `.pdf` để nhận diện.
- **Xóa tài liệu khi đang chờ câu trả lời** → cho phép; cảnh báo nhẹ rằng câu trả lời đang chạy có thể không còn trích dẫn tài liệu này (NE-08).
- **Chuyển ES-02 → ES-04 tự động:** khi SSE báo tài liệu đầu tiên `ready`, composer phải **tự mở** mà không cần tải lại trang (AC-010.2).

## 7. Kiểm thử bắt buộc

- [ ] Dựng đủ 5 kịch bản ES-01 → ES-05 trong E2E bằng dữ liệu giả lập; chụp ảnh so sánh với file tương ứng trong `html_design/`.
- [ ] ES-02 → ES-04: giả lập SSE báo `ready` → composer tự mở trong ≤ 5 giây, không cần reload (AC-010.2).
- [ ] Hộp xác nhận: focus mặc định ở "Hủy"; `Tab` di chuyển hợp lý; `Esc` đóng (AC-008.1, AC-008.3).
- [ ] Nhấn "Hủy" → không có request `DELETE` nào được gửi (kiểm tra qua network mock).
- [ ] Toast tự ẩn sau 4 giây và được trình đọc màn hình thông báo (`role="status"`).
- [ ] `empty_state_viewed` chỉ phát **một lần** cho mỗi variant trong một phiên.
- [ ] axe-core: 0 lỗi nghiêm trọng trên Dialog và EmptyState.
- [ ] ES-05: sau khi xóa tài liệu cuối, hội thoại cũ **vẫn hiển thị**, ô câu hỏi khóa.

## 8. Định nghĩa Hoàn thành

- [ ] 5 trạng thái trống khớp ảnh thiết kế — chưa xây `resolveEmptyState`, `DocumentLibrary.tsx` chỉ có 1 nhánh rỗng chung chung ("Chưa có tài liệu…")
- [ ] `resolveEmptyState` unit test — hàm chưa tồn tại
- [ ] Chuỗi lấy từ `messages.vi.ts` — chưa, hard-code
- [x] Không dùng optimistic UI cho xóa — `remove()` trong `DocumentLibrary.tsx` gọi `await apiFetch(DELETE)` rồi mới `load()` lại, không tự xóa dòng trước khi có `204`
- [ ] `data-testid`/WCAG AA — có testid cơ bản (`doc-item`, `doc-delete`, `empty-state`) nhưng không có `ConfirmDialog`/toast nên không đạt đủ yêu cầu bàn phím/ARIA của hộp thoại thật

### Ghi chú triển khai thực tế

Task này **về cơ bản chưa bắt đầu**: không có `ConfirmDialog`, không có
`Toast`/`ToastRegion` (phụ thuộc `shared/ui` — xem T-106), không có hàm
`resolveEmptyState` cho 5 biến thể ES-01→05, không có sự kiện
`empty_state_viewed`. Phần duy nhất tồn tại là `window.confirm()` gốc
trình duyệt trong `DocumentLibrary.tsx` làm tạm cho bước xác nhận xóa — đáp
ứng tinh thần "không optimistic update" nhưng không đạt yêu cầu UI/AX của
task (focus mặc định ở Hủy, `Esc` đóng, `data-testid="confirm-delete"`
dùng trong kịch bản E2E mẫu của T-504). Giữ **"To do"**.

## 9. Tham chiếu

- PRD v0.2 §4.2 (ES-01 – ES-05, định nghĩa gốc), §5.2 (`empty_state_viewed`)
- SDD UI/UX v0.3 §3.2.3 (`EmptyState`, `DeleteConfirmDialog`, `ToastRegion`), §3.7.3 (trạng thái Composer), §2.5 (quy tắc toast, tooltip nút disabled), §3.8.2 (xác nhận thao tác phá hủy)
- User Stories v0.4 — US-003, US-008 (ES-05, NE-08), US-010, US-011 (AC-011.3)
- Ảnh: `docs/design/html_design/SCR-02_01`, `_04`, `_06`, `_09`, `_12`, `_18`
