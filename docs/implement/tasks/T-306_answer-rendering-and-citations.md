# T-306 — Hiển thị câu trả lời và thẻ nguồn

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | US-011, US-014 |
| Epic | EP-03, EP-04 |
| Module (SADD §2.2.1) | `features/chat` (front-end, SDD §3.2.3) |
| API liên quan | API-09 (sự kiện `delta`, `citations`, `done`) |
| Vai trò chính | FE |
| Ước lượng | 3d |
| Phụ thuộc | T-304 (API SSE), T-305 (Composer/store) |
| Trạng thái | In progress (markdown + rehype-sanitize + hover `[n]`↔chip + IR-01/02/03 đã nối; còn thiếu axe-core và so khớp ảnh thiết kế) |

## 1. Mục tiêu

Hiển thị câu trả lời hiện dần theo luồng SSE và danh sách thẻ nguồn — **trụ cột "kiểm chứng được"** của sản phẩm (CN-01). Quy tắc quan trọng nhất: thẻ nguồn **chỉ xuất hiện khi câu trả lời đã hoàn tất** (IR-01), tránh việc người dùng tin vào nguồn của một câu trả lời còn dang dở.

Mọi nội dung do AI sinh ra **bắt buộc đi qua `rehype-sanitize`** trước khi render (IR-04) — chống XSS từ nội dung tài liệu hoặc từ LLM.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-011.1 | Câu trả lời hiển thị đầy đủ nội dung do máy chủ gửi |
| AC-014.1 | Câu trả lời có nội dung → hiển thị ít nhất một thẻ nguồn ghi tên tệp PDF |
| AC-014.2 | Tổng hợp từ N tài liệu → có thẻ nguồn cho cả N tài liệu |
| AC-014.4 | Câu trả lời "không tìm thấy" → không có thẻ nguồn nào |
| IR-01 | Thẻ nguồn chỉ hiển thị khi `phase = 'complete'`; `incomplete`/`failed` → **ẩn toàn bộ** |
| IR-02 | `answered` nhưng `citations` rỗng → nhãn cảnh báo "Không xác định được nguồn — vui lòng kiểm chứng" |
| IR-03 | `[n]` không khớp thẻ nguồn nào → hiển thị chữ thường, không tạo liên kết |
| IR-04 | Nội dung luôn qua `rehype-sanitize`; không cho HTML thô, script, iframe |
| UX-04 | Di chuột vào `[n]` trong nội dung → làm nổi bật thẻ nguồn tương ứng |

## 3. Hợp đồng API / giao diện

View model (SDD §3.4.1):

```ts
type AnswerPhase = 'pending' | 'streaming' | 'complete' | 'failed' | 'incomplete';
type AnswerType  = 'answered' | 'partial' | 'not_found';

interface CitationVM {
  index: number;            // khớp [n] trong markdown
  documentId: string;
  documentName: string;
  page?: number;            // định dạng chi tiết ở T-402 (US-015)
}

interface AnswerVM {
  id: string;
  phase: AnswerPhase;
  type?: AnswerType;        // có khi phase = 'complete'
  markdown: string;         // nội dung tích lũy dần khi streaming
  citations: CitationVM[];  // nhận ở event 'citations'
  latencyMs?: number;
  uncited?: boolean;
  errorCode?: string;
}
```

Bảng hiển thị theo `phase` (SDD §3.7.2) — **bảng này là đặc tả, không phải gợi ý**:

| Phase | Nội dung | Thẻ nguồn | Composer |
|---|---|---|---|
| `pending` | `TypingIndicator` | Ẩn | Khóa nút Gửi |
| `streaming` | Nội dung hiện dần + con trỏ nhấp nháy | **Ẩn** | Khóa nút Gửi |
| `complete` · `answered` | Nội dung + `[n]` có liên kết | **Hiện** | Mở |
| `complete` · `partial` | Nội dung + ghi chú "Một phần thông tin không tìm thấy" | Hiện | Mở |
| `complete` · `not_found` | `NotFoundMessage` (T-307) | Không có | Mở |
| `failed` | `ErrorMessage` + Thử lại (T-307) | Ẩn | Mở |
| `incomplete` | Nội dung đã nhận (mờ) + "Câu trả lời chưa hoàn chỉnh" | **Ẩn** (IR-01) | Mở |

## 4. Thay đổi dữ liệu

Không có. Câu trả lời chỉ sống trong RAM (Zustand + cache TanStack Query), **không** ghi vào `localStorage`/`IndexedDB` (CN-06, DF-09). Cache bị xóa khi đăng xuất.

## 5. Các bước triển khai

1. `MessageList` với `aria-live="polite"`: tự cuộn xuống cuối khi có tin nhắn mới, **trừ khi** người dùng đang cuộn lên đọc (giữ vị trí cuộn — kiểm tra khoảng cách tới đáy trước khi auto-scroll).
2. Xử lý sự kiện SSE trong store:
   - `meta` → `phase = 'pending'`, lưu `answer_id`, `ready_doc_count`.
   - `delta` → `phase = 'streaming'`, **nối thêm** vào `markdown` (không thay thế).
   - `citations` → lưu `citations[]` nhưng **chưa hiển thị**.
   - `done` → `phase = 'complete'`, lưu `type`, `latencyMs`, `uncited`; **lúc này mới** render `CitationList`.
   - `error` → `phase = 'failed'` (hoặc `'incomplete'` nếu `code = ANSWER_INTERRUPTED` và đã nhận ≥ 1 `delta`).
3. `AnswerMessage` render markdown bằng `react-markdown` + **`rehype-sanitize` (bắt buộc, IR-04)**. Cấu hình sanitize: chỉ cho phép thẻ văn bản cơ bản (`p`, `strong`, `em`, `ul`, `ol`, `li`, `code`, `br`) — **chặn** `script`, `iframe`, `img`, `a href` tùy ý, mọi thuộc tính `on*`.
4. Trong lúc `streaming`: hiển thị con trỏ nhấp nháy ở cuối nội dung. Markdown chưa đóng thẻ (ví dụ `**` dở) phải render không vỡ bố cục — test với chuỗi cắt ngẫu nhiên.
5. Component `CitationRef` thay thế token `[n]` trong markdown:
   - Nếu `n` khớp một `CitationVM.index` → render chip nhỏ có thể focus (`<button>`), liên kết tới thẻ nguồn tương ứng.
   - Nếu **không khớp** → render chữ thường `[n]`, **không** tạo liên kết (IR-03).
6. `CitationList` (chỉ khi `phase = 'complete'`): danh sách `CitationChip` dạng `[n] 🗎 TenTep.pdf · tr. X`. Định dạng số trang chi tiết thuộc T-402.
7. **Tương tác UX-04**: hover/focus vào `[n]` trong nội dung → chip tương ứng được làm nổi bật (viền `--color-primary`); hover vào chip → `[n]` tương ứng nổi bật. Dùng state dùng chung `highlightedIndex`, không thao tác DOM trực tiếp.
8. **IR-02**: nếu `done.uncited = true` (hoặc `type='answered'` mà `citations` rỗng) → hiển thị nhãn cảnh báo "Không xác định được nguồn — vui lòng kiểm chứng" ngay dưới nội dung, kiểu cảnh báo (`--color-warning`).
9. Thông báo cho trình đọc màn hình khi hoàn tất: vùng `aria-live` công bố "Đã có câu trả lời" (không đọc lại toàn bộ nội dung để tránh làm phiền).
10. Phát sự kiện `citation_viewed` khi người dùng **hover ≥ 500 ms** hoặc **nhấn** vào chip — thuộc tính allow-list (không gửi tên tệp, US-020; xem T-404).
11. Hiển thị `latencyMs` dạng "Trả lời trong 6,2 giây" dưới câu trả lời (khớp ảnh thiết kế).

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| `ANSWER_INTERRUPTED` sau khi đã có nội dung | `phase='incomplete'`: nội dung mờ, **ẩn toàn bộ thẻ nguồn** (IR-01), nút Thử lại |
| `type='answered'`, `citations=[]` | Hiện nội dung + cảnh báo IR-02 |
| `[5]` xuất hiện nhưng chỉ có 2 thẻ nguồn | `[5]` render chữ thường, không link (IR-03) |
| LLM trả nội dung chứa `<script>` | Bị `rehype-sanitize` loại bỏ (IR-04) — **phải có test** |
| Markdown bị cắt giữa chừng khi streaming | Render không vỡ bố cục |
| Người dùng cuộn lên đọc trong lúc đang stream | **Không** tự cuộn xuống |
| Câu trả lời rất dài (> `max_tokens`) | Hiển thị đầy đủ phần nhận được, không cắt phía client |

## 7. Kiểm thử bắt buộc

- [x] XSS không thực thi — `AnswerMessage.tsx` render qua `react-markdown` + `remark-gfm` + `rehype-sanitize` với schema giới hạn (`p, strong, em, ul, ol, li, code, br`, không thuộc tính); test `ChatPage.test.tsx` ("IR-04: nội dung `<script>` bị rehype-sanitize loại bỏ") gửi một `delta` chứa `<script>window.__xss=true</script>` và xác nhận `document.querySelector("script")` là `null` và biến global không được set
- [x] Thẻ nguồn không xuất hiện khi streaming — `citations` chỉ cập nhật khi nhận `event: citations`; `CitationList` chỉ render khi `phase === 'complete'` (IR-01, không chỉ khi "chưa stream")
- [x] `incomplete` → ẩn thẻ nguồn — `ChatPage.tsx::runQuestion` đặt `phase='incomplete'` khi `event:error{code:'ANSWER_INTERRUPTED'}` đến **sau** ít nhất một `delta`; `AnswerMessage` không render `CitationList` khi `phase!=='complete'`; có test riêng xác nhận `citation-list` không tồn tại trong DOM ở nhánh này
- [x] `[n]` không khớp → chữ thường — `CitationRef` (trong `AnswerMessage.tsx`, dùng từ `CitationChip.tsx`) trả `<span>[n]</span>` thuần khi không tìm thấy trong `citationsByIndex`; test "CitationRef [n] không khớp" xác nhận không có `citation-ref` nhưng text `[5]` vẫn hiển thị
- [x] Hover `[1]` nổi bật chip — `highlightedIndex` dùng chung giữa `CitationRef` và `CitationChip` trong `AnswerMessage`, cập nhật qua `onMouseEnter/onFocus` cả hai chiều (UX-04)
- [x] 4 tài liệu → 4 chip không trùng — `citations.map` theo `index` nhận từ server, key `${documentId}-${index}` đảm bảo duy nhất
- [~] aria-live công bố "Đã có câu trả lời" — có vùng `aria-live="polite"` riêng (`data-testid="answer-announcer"`, ẩn bằng `.sr-only`) chỉ cập nhật text khi `done` tới, tách khỏi `message-list` (cũng `aria-live="polite"` nhưng đổi nội dung mỗi token); về lý thuyết giảm đọc lặp nhưng chưa kiểm bằng trình đọc màn hình thật
- [ ] axe-core — chưa chạy cho `features/chat` (có sẵn hạ tầng `expectNoA11yViolations` ở `shared/testing/axe.ts`, dùng trong `shared/ui/*.test.tsx`, chưa áp dụng ở đây)

## 8. Định nghĩa Hoàn thành

- [ ] Khớp ảnh thiết kế — chưa đối chiếu
- [x] Bảng `phase` 7 dòng — `AnswerMessage.tsx` xử lý đủ `pending`/`streaming`/`complete·answered`/`complete·partial`/`complete·not_found`/`failed`/`incomplete` theo đúng bảng §3 (ẩn/hiện thẻ nguồn, khóa composer tương ứng qua `awaitingAnswer`)
- [x] Không lưu câu trả lời vào Web Storage — xác nhận bằng đọc code (chỉ `useState` trong `ChatPage.tsx`)
- [x] `citation_viewed` không chứa tên tệp/nội dung — `CitationChip.tsx` phát `track("citation_viewed", {citation_index})` khi hover ≥500ms (dùng `setTimeout`, hủy ở `mouseleave`) hoặc khi click; có test dùng fake timers xác nhận không phát khi rời chuột trước 500ms

### Ghi chú triển khai thực tế

Viết lại hoàn toàn phần hiển thị câu trả lời thành
`frontend/src/features/chat/AnswerMessage.tsx` +
`frontend/src/features/chat/CitationChip.tsx`. Markdown dùng
`react-markdown`/`remark-gfm`/`rehype-sanitize` với schema tag tối giản
đúng §5.3; việc thay token `[n]` bằng `CitationRef` được làm bằng một hàm
đệ quy (`renderWithCitationRefs`) duyệt `children` của các thẻ `p/li/strong/em`
do `react-markdown` trả về và tách chuỗi theo regex `/\[(\d+)\]/g` — cách
này tương thích với nội dung markdown bị cắt giữa chừng khi streaming
(không parse toàn bộ AST lại mỗi token). `highlightedIndex` là state cục
bộ trong `AnswerMessage` dùng chung cho `CitationRef` và `CitationChip`
(UX-04). IR-02 (uncited) dùng `Banner tone="warning"`; `not_found` dùng
`Banner tone="info"` với icon ℹ (UX-06, T-307). Còn thiếu: axe-core cho
`features/chat`, so khớp ảnh thiết kế, kiểm thử trình đọc màn hình thật
cho vùng `aria-live`. Giữ "In progress".

## 9. Tham chiếu

- [SDD UI/UX §3.2.3, §3.4.1, §3.4.2, §3.7.2](../../design/SDD_UI_UX_Blueprint.md) — cây thành phần, view model, IR-01 – IR-04, vòng đời câu trả lời
- [User Stories US-011, US-014](../../design/User_Stories.md)
- [SADD §2.2.3](../../requirements/SADD.md) — nguồn gốc dữ liệu `citations`
- Ảnh: [`SCR-02_14_answer-with-citations.png`](../../design/html_design/SCR-02_14_answer-with-citations.png) · [`SCR-02_15_answer-multi-source.png`](../../design/html_design/SCR-02_15_answer-multi-source.png) · [`SCR-02_24_streaming.png`](../../design/html_design/SCR-02_24_streaming.png)
- [implement_plan.md](../implement_plan.md) §5 Sprint 3
