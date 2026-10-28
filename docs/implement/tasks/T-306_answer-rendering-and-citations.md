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
| Trạng thái | In progress (hiển thị + chip nguồn cơ bản, chưa markdown/sanitize/hover) |

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

- [x] XSS không thực thi — hiện render answer bằng `{answer}` trong JSX (React escape mặc định, không `dangerouslySetInnerHTML`) nên an toàn mặc định; nhưng cũng có nghĩa là **không có markdown nào được render** dù `react-markdown`/`rehype-sanitize`/`remark-gfm` có trong `package.json` — phụ thuộc chưa được dùng
- [x] Thẻ nguồn không xuất hiện khi streaming — `citations` chỉ được `setCitations` khi nhận `event: citations`, đúng sau khi `delta` kết thúc và trước `done` (khớp thứ tự backend ở T-304)
- [ ] `incomplete` → ẩn thẻ nguồn — **chưa có khái niệm `incomplete`** ở FE (không xử lý `event: error`/ngắt kết nối giữa chừng)
- [ ] `[n]` không khớp → chữ thường — không áp dụng vì câu trả lời không được parse thành các đoạn `[n]` tương tác, chỉ hiện thô
- [ ] Hover `[1]` nổi bật chip — chưa có (chip chỉ có `onClick` phát `citation_viewed`, không có hover-link với vị trí trong văn bản)
- [ ] 4 tài liệu → 4 chip không trùng — về lý thuyết đúng vì `citations.map` render mọi phần tử nhận được, chưa có test
- [ ] aria-live công bố "Đã có câu trả lời" — `aria-live="polite"` có trên vùng trả lời nhưng nội dung thay đổi dần theo từng token (có thể đọc nhiều lần, không có thông báo hoàn tất riêng)
- [ ] axe-core — chưa cài

## 8. Định nghĩa Hoàn thành

- [ ] Khớp ảnh thiết kế — chưa đối chiếu
- [ ] Bảng `phase` 7 dòng — chỉ có trước/trong/sau stream (3 trạng thái ngầm), chưa đủ 7
- [x] Không lưu câu trả lời vào Web Storage — xác nhận bằng đọc code
- [x] `citation_viewed` không chứa tên tệp/nội dung — `track("citation_viewed", {citation_index: i+1})`, chỉ gửi chỉ số

### Ghi chú triển khai thực tế

Phần cốt lõi (ẩn thẻ nguồn khi đang stream, chỉ hiện sau khi nhận đủ) đã
đúng nhờ thứ tự sự kiện SSE của T-304. Thiếu: markdown rendering (dependency
đã cài nhưng chưa dùng), liên kết hover giữa `[n]` trong văn bản và chip
nguồn, xử lý trạng thái `incomplete` khi SSE bị ngắt giữa chừng, và a11y
(axe-core, thông báo hoàn tất riêng cho trình đọc màn hình). Giữ
"In progress".

## 9. Tham chiếu

- [SDD UI/UX §3.2.3, §3.4.1, §3.4.2, §3.7.2](../../design/SDD_UI_UX_Blueprint.md) — cây thành phần, view model, IR-01 – IR-04, vòng đời câu trả lời
- [User Stories US-011, US-014](../../design/User_Stories.md)
- [SADD §2.2.3](../../requirements/SADD.md) — nguồn gốc dữ liệu `citations`
- Ảnh: [`SCR-02_14_answer-with-citations.png`](../../design/html_design/SCR-02_14_answer-with-citations.png) · [`SCR-02_15_answer-multi-source.png`](../../design/html_design/SCR-02_15_answer-multi-source.png) · [`SCR-02_24_streaming.png`](../../design/html_design/SCR-02_24_streaming.png)
- [implement_plan.md](../implement_plan.md) §5 Sprint 3
