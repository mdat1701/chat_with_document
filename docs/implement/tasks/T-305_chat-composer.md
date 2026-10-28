# T-305 — Ô nhập câu hỏi và chỉ báo đang trả lời

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | US-011 |
| Epic | EP-03 |
| Module (SADD §2.2.1) | `features/chat` (front-end, SDD §3.2.3) |
| API liên quan | API-02 (`/config`), API-08, API-09 |
| Vai trò chính | FE |
| Ước lượng | 3d |
| Phụ thuộc | T-106 (nền tảng FE), T-304 (API SSE), T-205 (biết số tài liệu ready) |
| Trạng thái | In progress (7 trạng thái, phím tắt, bộ đếm ký tự, giữ nháp khi lỗi/hết phiên đã nối; còn thiếu axe-core và so khớp ảnh thiết kế) |

## 1. Mục tiêu

Dựng `Composer` (ô nhập câu hỏi) và `TypingIndicator` — điểm tương tác chính của người dùng với sản phẩm. Yêu cầu khắt khe nhất là **phản hồi hình ảnh ≤ 300 ms** sau khi gửi (IX-03) và **không bao giờ làm mất câu hỏi đang soạn** khi gặp lỗi mạng hoặc phiên hết hạn (CN-05).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-011.3 | Chưa có tài liệu "Sẵn sàng" → ô câu hỏi bị vô hiệu kèm gợi ý "Tải tài liệu lên để bắt đầu hỏi" |
| AC-011.4 | Ô trống hoặc chỉ khoảng trắng → nhấn Gửi không gửi gì |
| IX-02 | `Enter` gửi · `Shift+Enter` xuống dòng · `/` đưa con trỏ vào ô câu hỏi |
| IX-03 | Chỉ báo "Đang tìm trong N tài liệu…" xuất hiện ≤ 300 ms sau khi gửi |
| ER-09 | Câu hỏi > 2.000 ký tự (DF-07) → bộ đếm chuyển đỏ, nút Gửi bị khóa |
| UX-05 | Dòng cố định dưới ô nhập: "Câu trả lời do AI tạo — hãy kiểm tra nguồn trước khi sử dụng" |

## 3. Hợp đồng API / giao diện

Trạng thái `Composer` theo thứ tự ưu tiên (SDD §3.7.3 — **đúng thứ tự này**, điều kiện trên thắng điều kiện dưới):

| # | Điều kiện | Trạng thái | Tooltip / gợi ý |
|---|---|---|---|
| 1 | Đang ngoại tuyến | Khóa toàn bộ | "Bạn đang ngoại tuyến" |
| 2 | Không có tài liệu nào | Khóa toàn bộ | "Tải tài liệu lên để bắt đầu hỏi" (ES-01) |
| 3 | Mọi tài liệu đang xử lý | Khóa toàn bộ | "Tài liệu đang được xử lý, vui lòng chờ…" (ES-02) |
| 4 | Mọi tài liệu đều lỗi | Khóa toàn bộ | "Không có tài liệu nào sẵn sàng" (ES-03) |
| 5 | Đang chờ câu trả lời trước | Khóa **nút Gửi**, vẫn gõ được | "Đang trả lời câu hỏi trước…" |
| 6 | Ô trống hoặc > DF-07 ký tự | Khóa **nút Gửi** | Bộ đếm chuyển đỏ khi vượt |
| 7 | Còn lại | Sẵn sàng | — |

Props chính:

```ts
interface ComposerProps {
  disabledReason?: 'offline' | 'no_docs' | 'all_processing' | 'all_failed' | 'awaiting_answer';
  maxLength: number;              // từ GET /config -> max_question_length (DF-07)
  onSubmit: (text: string) => void;
}
```

## 4. Thay đổi dữ liệu

Không đụng CSDL. Lưu trữ phía client (SDD §3.4.4):

| Dữ liệu | Nơi lưu | Ghi chú |
|---|---|---|
| Bản nháp câu hỏi | `sessionStorage` | **Ngoại lệ có kiểm soát**, chờ ATTT duyệt (D-04/DQ-04); xóa ngay khi gửi thành công hoặc đăng xuất |
| Nội dung câu trả lời | RAM (Zustand) | **Không** ghi vào Web Storage (CN-06) |

## 5. Các bước triển khai

1. Dựng `ConversationStore` (Zustand): `messages[]`, `draft`, `phase` của câu trả lời đang chạy. Gọi `POST /conversations` (API-08) một lần khi mở màn hình để lấy `conversation_id`.
2. `Composer` là `<textarea>` autosize tối đa **6 dòng**, sau đó cuộn trong ô.
3. Phím tắt (IX-02): `Enter` gửi; `Shift+Enter` xuống dòng; `/` ở ngoài ô nhập đưa focus vào ô (bỏ qua nếu đang focus trong input khác).
4. `CharCounter` hiển thị `{len}/2.000` lấy `maxLength` từ `GET /config`, **không hard-code** 2000. Vượt giới hạn: bộ đếm chuyển màu `--color-danger`, nút Gửi `disabled` (ER-09).
5. `AIDisclaimer` cố định dưới ô nhập, cỡ chữ `--font-caption`, luôn hiển thị (UX-05, BRU-002).
6. Khi submit:
   a. Trim; nếu rỗng → không làm gì (AC-011.4).
   b. Thêm `UserMessage` + `AnswerVM{phase:'pending'}` vào store **ngay lập tức** (optimistic) → `TypingIndicator` xuất hiện trong cùng frame, đảm bảo ≤ 300 ms (IX-03).
   c. Phát sự kiện `question_submitted{question_length, language, ready_doc_count}` — **không gửi nội dung câu hỏi** (US-020).
   d. Mở SSE tới `POST /conversations/{cid}/questions` (T-304).
7. `TypingIndicator` hiển thị "Đang tìm trong **N** tài liệu…" với `N = ready_doc_count` nhận từ `event: meta`; trước khi có `meta` thì dùng số tài liệu ready đang biết từ `DocumentList`.
8. Khóa nút Gửi trong khi `phase ∈ {pending, streaming}`; vẫn cho phép gõ câu hỏi tiếp theo (điều kiện #5).
9. **Giữ bản nháp khi lỗi**:
   - NE-02 (`ANSWER_NETWORK`): giữ nguyên nội dung trong ô, hiện nút "Gửi lại".
   - NE-07 (`SESSION_EXPIRED`, 401): lưu `draft` vào `sessionStorage`, redirect `/login?returnTo=/`; sau khi đăng nhập lại, khôi phục vào ô rồi xóa khỏi storage (AC-001.3).
10. Trạng thái trống **ES-04** (có tài liệu ready, chưa hỏi câu nào): hiển thị khối "Bạn có thể hỏi, ví dụ:" với **câu mẫu tĩnh** (gợi ý thông minh từ nội dung tài liệu là P-05, post-MVP — không làm). Nhấn câu mẫu → điền vào ô, không tự gửi.
11. Khả năng truy cập: `<label class="sr-only">`, focus ring rõ ràng, nút bị vô hiệu luôn có tooltip giải thích lý do (§2.5 SDD).

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi UI |
|---|---|
| Ngoại tuyến (`navigator.onLine = false`) | Khóa ô + `OfflineBanner` (hoàn thiện ở T-405) |
| Dán 5.000 ký tự | Bộ đếm đỏ, nút Gửi khóa, **không** tự cắt bớt nội dung của người dùng |
| Gửi khi đang chờ câu trả lời trước | Nút Gửi khóa, vẫn gõ được (điều kiện #5) |
| Phiên hết hạn lúc đang gõ | Lưu nháp → `/login` → khôi phục nháp (AC-001.3) |
| Chỉ gõ khoảng trắng | Nút Gửi khóa (AC-011.4) |
| Tài liệu cuối cùng bị xóa lúc đang gõ | Ô chuyển sang khóa (ES-05), nội dung đang gõ **được giữ** |

## 7. Kiểm thử bắt buộc

- [x] `TypingIndicator` ≤ 300ms — thêm optimistic update đồng bộ (`setMessages` ngay khi submit, trước khi `await` bất kỳ API nào) nên `TypingIndicator` hiện trong cùng frame React; test `ChatPage.test.tsx` xác nhận `typing-indicator` xuất hiện ngay sau `fireEvent.click`
- [x] `Enter`/`Shift+Enter`/`/` — `Composer.tsx::handleKeyDown` chặn `Enter` (không Shift) để gửi, để `Shift+Enter` rơi qua hành vi mặc định (xuống dòng); listener `keydown` toàn `document` cho `/` focus vào `#question-input` khi không đang gõ ở input/textarea/contentEditable khác
- [x] Đủ 7 trạng thái Composer — `ChatPage.tsx` tính `disabledReason` theo đúng thứ tự ưu tiên offline → no_docs → all_processing → all_failed → awaiting_answer; `Composer.tsx` khóa toàn bộ ô cho 4 trạng thái đầu, chỉ khóa nút Gửi cho `awaiting_answer`; có test cho `no_docs`
- [x] Ngắt mạng giữa chừng → câu hỏi không mất, có nút Gửi lại — `streamQuestion` (shared/api/client.ts) không bao giờ `throw`, mọi lỗi mạng/đứt kết nối thành `{type:"error", code:"ANSWER_NETWORK"}`; composer giữ `draft` nguyên vẹn vì chỉ `setDraft("")` sau khi submit thành công tạo tin nhắn (không phụ thuộc kết quả SSE); `ErrorMessage` hiện nút "Gửi lại" gọi lại đúng câu hỏi cũ (lưu trong `questionByAnswerId` map)
- [x] Phiên hết hạn → khôi phục nháp (AC-001.3) — tái dùng hạ tầng đã có từ T-107 (`features/auth/draft.ts`): `ChatPageInner` gọi `restoreDraft()` khi khởi tạo state rồi `clearDraft()`, và `registerComposerSource(() => draft)` để interceptor 401 toàn cục lưu nháp khi `streamQuestion`/`apiFetch` gặp 401 giữa chừng
- [ ] axe-core — chưa chạy cho `Composer`/`ChatPage` (có sẵn cho `shared/ui`, chưa mở rộng sang `features/chat`)
- [x] Không lưu nội dung câu hỏi vào Web Storage — xác nhận bằng đọc code (chỉ `sessionStorage` khi hết phiên qua `draft.ts`, xóa ngay sau khi gửi/khôi phục thành công)

## 8. Định nghĩa Hoàn thành

- [ ] Khớp ảnh thiết kế — chưa đối chiếu
- [x] `data-testid` cho `question-input` — có, cùng `send-button`, `char-counter`, `typing-indicator`, `user-message`, `answer-message`
- [x] Chuỗi lấy từ `messages.vi.ts` — toàn bộ nhãn composer (`composerPlaceholder`, `composerSubmit`, `composerAiDisclaimer`, 5 tooltip khóa, bộ đếm, ví dụ câu hỏi) chuyển vào `uiText` trong `shared/i18n/messages.vi.ts`
- [x] `question_submitted` không chứa nội dung câu hỏi — `ready_doc_count` giờ lấy từ `readyDocCountRef.current` (tính từ `GET /documents` + SSE `/documents/events` thật), không còn hard-code `0`

### Ghi chú triển khai thực tế

Composer được viết lại thành `Composer.tsx` (textarea tự giãn tối đa 6
dòng, `CharCounter` đọc `max_question_length` từ `useAppConfig()`, lời
miễn trừ AI cố định) và `ChatPage.tsx` (điều phối trạng thái, không dùng
Zustand như gợi ý trong §5 mà dùng `useState`/`useRef` thuần — quyết định
thực dụng để tránh thêm phụ thuộc chéo trong lúc một phiên khác đang sửa
`features/auth`/`features/documents`/`App.tsx` song song; hành vi khớp đặc
tả 7 trạng thái). Danh sách tài liệu lấy qua `GET /documents` + SSE
`subscribeDocumentEvents` (không phụ thuộc `DocumentLibrary.tsx` để tránh
đụng file của phiên khác). `streamQuestion` (shared/api/client.ts) được mở
rộng để không bao giờ `throw`: mọi lỗi (mạng, 401/429/…, đứt SSE) được
chuẩn hoá thành sự kiện `error`, nên composer/`finally` không còn rủi ro
kẹt `busy=true`. AC-001.3 tái sử dụng đúng hạ tầng `features/auth/draft.ts`
đã có sẵn từ T-107. Còn thiếu: axe-core cho `features/chat`, đối chiếu ảnh
thiết kế. Giữ "In progress".

## 9. Tham chiếu

- [SDD UI/UX §3.2.3, §3.5.2, §3.7.3](../../design/SDD_UI_UX_Blueprint.md) — cây thành phần, phím tắt, bảng trạng thái Composer
- [User Stories US-011](../../design/User_Stories.md)
- Ảnh: [`SCR-02_12_ready-suggestions.png`](../../design/html_design/SCR-02_12_ready-suggestions.png) · [`SCR-02_13_typing-indicator.png`](../../design/html_design/SCR-02_13_typing-indicator.png) · [`SCR-02_25_question-too-long.png`](../../design/html_design/SCR-02_25_question-too-long.png)
- [implement_plan.md](../implement_plan.md) §5 Sprint 3
