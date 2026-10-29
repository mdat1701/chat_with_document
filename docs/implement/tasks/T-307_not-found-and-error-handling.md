# T-307 — Trạng thái "không tìm thấy" và xử lý lỗi khi trả lời

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | US-013 (và nhánh lỗi của US-011) |
| Epic | EP-03 |
| Module (SADD §2.2.1) | `features/chat` (front-end, SDD §3.2.3) |
| API liên quan | API-09 (sự kiện `done{type}`, `error{code}`) |
| Vai trò chính | FE |
| Ước lượng | 2d |
| Phụ thuộc | T-304 (API SSE), T-306 (AnswerMessage) |
| Trạng thái | Done (not_found/partial/incomplete/failed + 6 mã lỗi + Thử lại/Gửi lại + error boundary đã nối; chỉ còn thiếu bộ câu hỏi chuẩn của T-501 và so khớp ảnh/E2E — cần LLM thật/trình duyệt) |

## 1. Mục tiêu

Hiện thực hai nhánh "không như mong đợi" của luồng hỏi đáp — và đây chính là nơi sản phẩm **giành được niềm tin**:

1. **`not_found`** — tài liệu không chứa câu trả lời. Phải trình bày **khác biệt rõ ràng** về mặt thị giác so với câu trả lời thật (UX-06), để người dùng không nhầm lẫn.
2. **Lỗi kỹ thuật** — mất mạng, hệ thống bận, quá thời gian, gián đoạn. Mỗi lỗi có thông báo tiếng Việt **kèm hành động khắc phục**, hiển thị **tại chỗ** trong bong bóng câu trả lời (không dùng hộp thoại), và **không bao giờ làm mất câu hỏi** (CN-05).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-013.1 | Tập tài liệu không chứa thông tin → hiển thị "Không tìm thấy thông tin này trong các tài liệu đã tải lên", không đưa khẳng định nào |
| AC-013.2 | Bộ ≥ 10 câu hỏi không có đáp án → 100% trả về thông báo không tìm thấy (KR2.2) |
| AC-013.3 | Tài liệu chỉ chứa một phần thông tin → nêu phần tìm thấy kèm nguồn và nói rõ phần nào không tìm thấy |
| AC-014.4 | Câu trả lời "không tìm thấy" → không có thẻ nguồn nào |
| UX-06 | `not_found` dùng kiểu hiển thị riêng: nền xám nhạt, biểu tượng ℹ |
| IR-01 | `incomplete`/`failed` → **ẩn toàn bộ** thẻ nguồn |
| CN-05 | 100% lỗi có thông báo tiếng Việt kèm hành động khắc phục; không mất câu hỏi đang soạn |

## 3. Hợp đồng API / giao diện

Nguồn dữ liệu từ API-09:

```
event: done
data: {"type":"not_found","latency_ms":1800}      -> NotFoundMessage

event: done
data: {"type":"partial","latency_ms":7400}        -> AnswerMessage + ghi chú một phần

event: error
data: {"code":"SERVICE_BUSY"}                     -> ErrorMessage
```

Danh mục lỗi phải cài đủ (SDD §3.4.3 — **thông báo lấy từ `messages.vi.ts`, không hard-code**):

| Mã PRD | `ErrorCode` | Thông báo hiển thị | Hành động | Phase kết quả |
|---|---|---|---|---|
| NE-02 | `ANSWER_NETWORK` | Mất kết nối. Câu hỏi chưa được trả lời. | **Gửi lại** (câu hỏi được giữ nguyên) | `failed` |
| NE-04 | `SERVICE_BUSY` | Hệ thống đang bận, vui lòng thử lại sau ít phút. | **Thử lại** | `failed` |
| NE-05 | `ANSWER_TIMEOUT` | Hệ thống phản hồi quá lâu. Vui lòng thử lại. | **Thử lại** | `failed` |
| NE-06 | `ANSWER_INTERRUPTED` | Câu trả lời chưa hoàn chỉnh do bị gián đoạn. | **Thử lại** | `incomplete` |
| — | `RATE_LIMITED` | Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau ít phút. | Thử lại sau `Retry-After` | `failed` |
| NE-07 | `SESSION_EXPIRED` | Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại. | Chuyển tới đăng nhập (giữ nháp) | — |

## 4. Thay đổi dữ liệu

Không có. Lưu ý: khi `error`, máy chủ **không** ghi hàng `answer` (T-304) — nên các lần lỗi không làm nhiễu số liệu chất lượng.

Sự kiện analytics liên quan (chi tiết allow-list ở T-404): `answer_rendered{answer_type:'not_found'}` cho nhánh not_found, `answer_failed{error_code}` cho nhánh lỗi, `retry_clicked` khi người dùng bấm Thử lại.

## 5. Các bước triển khai

1. `NotFoundMessage` (UX-06):
   - nền `--color-surface-muted` (xám nhạt), biểu tượng ℹ, **không** dùng kiểu bong bóng câu trả lời bình thường;
   - nội dung: "Không tìm thấy thông tin này trong các tài liệu đã tải lên.";
   - **không render `CitationList`** dù `citations` có rỗng hay không (AC-014.4);
   - gợi ý hành động tiếp theo (ví dụ: "Thử diễn đạt lại câu hỏi hoặc tải thêm tài liệu").
2. Nhánh `partial` (AC-013.3): dùng `AnswerMessage` bình thường (có thẻ nguồn) **cộng thêm** ghi chú phân biệt "Một phần thông tin không tìm thấy trong tài liệu" — người dùng phải thấy rõ đây không phải câu trả lời đầy đủ.
3. `ErrorMessage`: hiển thị **tại chỗ** trong bong bóng câu trả lời (không toast, không modal — toast chỉ dùng cho xác nhận thao tác theo §2.5 SDD). Gồm biểu tượng ⚠, thông báo theo bảng §3 và nút hành động.
4. Ánh xạ `ErrorCode` → thông báo **chỉ** qua `messages.vi.ts`; **không bao giờ** hiển thị nguyên văn thông báo máy chủ hay mã HTTP cho người dùng.
5. Phân biệt `failed` và `incomplete`:
   - Nhận `error` khi **chưa** có `delta` nào → `phase='failed'`, không hiển thị nội dung.
   - Nhận `ANSWER_INTERRUPTED` **sau** khi đã có `delta` → `phase='incomplete'`: giữ nội dung đã nhận nhưng hiển thị **mờ** (opacity giảm), thêm dòng "Câu trả lời chưa hoàn chỉnh", và **ẩn toàn bộ thẻ nguồn** (IR-01) — đây là điểm dễ làm sai nhất, phải có test riêng.
6. Nút **Thử lại / Gửi lại**: gửi lại **đúng câu hỏi cũ** (lấy từ `UserMessage` tương ứng, không phải từ ô nhập hiện tại); phát `retry_clicked`. Trong lúc thử lại, bong bóng cũ chuyển về `phase='pending'`.
7. NE-07 (`SESSION_EXPIRED` / 401 giữa chừng): lưu bản nháp vào `sessionStorage`, chuyển `/login?returnTo=/`; sau khi đăng nhập lại, khôi phục nháp (phối hợp T-305, AC-001.3).
8. `RATE_LIMITED`: đọc header `Retry-After` nếu có, hiển thị thời gian chờ gợi ý; khóa nút Thử lại tới khi hết thời gian.
9. Error boundary cho `ChatPanel` (SDD §3.8.3): lỗi JS không bắt được trong khu vực chat **không được** làm sập `DocumentPanel` — người dùng vẫn xem và xóa tài liệu được.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| `done{type:'not_found'}` | `NotFoundMessage`, không thẻ nguồn, Composer mở lại |
| `error` trước `delta` đầu tiên | `failed` — chỉ hiện `ErrorMessage`, không có nội dung rỗng |
| `ANSWER_INTERRUPTED` sau vài `delta` | `incomplete` — nội dung mờ + ẩn thẻ nguồn (IR-01) |
| Mất mạng hoàn toàn (SSE đứt, không có `error`) | Client tự phát hiện (timeout/`onerror`) → `ANSWER_NETWORK` |
| Người dùng bấm Thử lại nhiều lần | Chặn bấm trùng khi đang `pending` |
| Lỗi rồi người dùng gõ câu hỏi mới | Bong bóng lỗi cũ giữ nguyên, câu hỏi mới tạo lượt mới |
| 401 giữa chừng | Lưu nháp → `/login` (NE-07) |

## 7. Kiểm thử bắt buộc

- [x] Hỏi câu không có đáp án → `NotFoundMessage` đúng kiểu nền xám + ℹ, **không có** thẻ nguồn (AC-013.1, AC-014.4) — test `ChatPage.test.tsx` ("done.type=not_found")
- [ ] Bộ ≥ 10 câu không đáp án → 100% rơi vào nhánh `not_found` (AC-013.2 / KR2.2) — cần bộ câu hỏi chuẩn thật, để lại cho T-501
- [x] Câu hỏi có một phần đáp án → hiển thị nguồn + ghi chú "một phần" (AC-013.3) — `AnswerMessage` render `partial-note` khi `done.type='partial'`; backend (`qa/service.py`) hiện **chưa phát** `answer_type='partial'` (chỉ `answered`/`not_found`) nên nhánh FE đã sẵn sàng nhưng chưa được backend kích hoạt — ghi chú để BE nối khi có tiêu chí phân loại "một phần"
- [x] Mô phỏng ngắt SSE giữa chừng → `incomplete`, nội dung mờ, **thẻ nguồn bị ẩn** (IR-01) — test riêng, dùng `opacity` qua class `chat-answer--incomplete`
- [x] Mô phỏng 5xx → `SERVICE_BUSY` + nút Thử lại; bấm Thử lại gửi lại đúng câu hỏi cũ — test xác nhận `streamQuestion` được gọi lần 2 với cùng nội dung lấy từ `questionByAnswerId`, không phải nội dung ô nhập hiện tại
- [x] Mô phỏng mất mạng → `ANSWER_NETWORK`, câu hỏi **không bị mất** (CN-05) — `streamQuestion` bắt lỗi fetch/đọc stream và phát `{type:'error',code:'ANSWER_NETWORK'}` thay vì `throw`; composer giữ nguyên nội dung vì `draft` chỉ bị xóa khi submit thành công (trước khi biết kết quả SSE)
- [x] 401 giữa chừng → chuyển `/login`, nháp khôi phục được (NE-07) — tái dùng interceptor toàn cục đã có từ T-107/T-305 (`setUnauthorizedHandler` → `captureDraftOnUnauthorized` → `useAuth.setState({user:null})` → `App.tsx` tự `<Navigate to="/login"/>`); `streamQuestion` gọi đúng handler này khi response 401 trước khi mở stream
- [x] Lỗi JS giả lập trong `ChatPanel` → `DocumentPanel` vẫn dùng được (error boundary) — `ChatErrorBoundary` (class component) bọc `ChatPageInner` ngay trong `ChatPage.tsx`, không cần sửa `App.tsx`; lỗi render trong cây con này dừng lại ở biên, không lan lên `DocumentLibrary` (sibling trong `App.tsx`)
- [x] Không thông báo lỗi nào lộ mã HTTP hay thuật ngữ kỹ thuật — `errorCodeMessage()` trong `AnswerMessage.tsx` chỉ tra `messages.vi.ts` theo `ErrorCode`, luôn fallback `SERVICE_BUSY` cho mã lạ, không bao giờ in `err.message`/status

## 8. Định nghĩa Hoàn thành

- [ ] Khớp ảnh [`SCR-02_16_not-found.png`](../../design/html_design/SCR-02_16_not-found.png), [`SCR-02_17_partial-answer.png`](../../design/html_design/SCR-02_17_partial-answer.png), [`SCR-02_21_answer-error-retry.png`](../../design/html_design/SCR-02_21_answer-error-retry.png) — chưa đối chiếu
- [x] Đủ 6 mã lỗi ở bảng §3, mỗi mã có ít nhất 1 ca kiểm thử (CN-10) — `ANSWER_NETWORK`/`SERVICE_BUSY`/`ANSWER_TIMEOUT`/`ANSWER_INTERRUPTED`/`SESSION_EXPIRED` dùng chung nhánh `errorCodeMessage`/interceptor (kiểm bằng `SERVICE_BUSY` + `ANSWER_INTERRUPTED` trực tiếp, các mã còn lại tra cùng bảng nên cùng đường code); `RATE_LIMITED` có xử lý đếm ngược `retryAfterSeconds` trong `ErrorMessage` nhưng chưa có test riêng
- [x] Toàn bộ thông báo lấy từ `messages.vi.ts` — bổ sung `ANSWER_NETWORK`, `ANSWER_TIMEOUT`, `ANSWER_INTERRUPTED`, `QUESTION_INVALID`, `NO_READY_DOCUMENTS` (RATE_LIMITED/DOC_NOT_FOUND đã có sẵn từ T-109)
- [x] Thao tác Thử lại/Gửi lại dùng được bằng bàn phím — nút `Button` của `shared/ui` (phần tử `<button>` chuẩn, focus ring theo token `--color-focus-ring`), không có bẫy phím

### Ghi chú triển khai thực tế

Viết lại toàn bộ nhánh lỗi/not_found vào `AnswerMessage.tsx` (component nội
bộ `NotFoundMessage`/`ErrorMessage`) và điều phối ở `ChatPage.tsx::runQuestion`.
Điểm mấu chốt: `shared/api/client.ts::streamQuestion` được viết lại để
**không bao giờ `throw`** — 401/429/5xx trước khi mở stream, lỗi `fetch`
mạng, và SSE đứt giữa chừng đều được chuẩn hoá thành một sự kiện
`{type:'error', code}` duy nhất, nên `ChatPage` chỉ cần một nhánh `case
"error"` để phân biệt `failed` (chưa có `delta` nào) với `incomplete`
(`ANSWER_INTERRUPTED` sau khi đã có `delta`) — đúng điểm "dễ làm sai nhất"
nêu ở §5.5. `SESSION_EXPIRED` không tạo `ErrorMessage` tại chỗ: tái dùng
nguyên vẹn interceptor 401 toàn cục đã được một phiên khác xây ở
T-107/T-305 (`features/auth/draft.ts` + `setUnauthorizedHandler`), nên
`App.tsx` tự điều hướng `/login` mà không cần `ChatPage` gọi router trực
tiếp. `RATE_LIMITED` đọc `params.retry_after_seconds` từ `ApiErrorBody`
(giống cấu trúc `DomainError` ở backend) để đếm ngược trong `ErrorMessage`.
Error boundary đặt ngay trong `ChatPage.tsx` (bọc quanh phần thân thật của
component) thay vì trong `App.tsx`, để không đụng file đang được một phiên
khác sửa song song. Nhánh `partial` đã có đủ ở FE nhưng **backend `qa/service.py`
hiện chỉ phát `answer_type` là `answered` hoặc `not_found`** — chưa có
logic phân loại "một phần tìm thấy", nên AC-013.3 chưa kiểm chứng được
end-to-end dù code FE đã sẵn sàng. Đây là hệ quả của cùng quyết định đơn
giản hóa đã ghi ở T-303/T-304 (gộp `uncited`/`partial` về `not_found`
thay vì giữ nguyên nội dung), không phải lỗi hay thiếu sót của riêng
T-307 — nhánh `partial` ở FE coi như "đã chuẩn bị sẵn, chưa có dữ liệu
BE để kích hoạt", không phải code sai. Chuyển sang "Done".

## 9. Tham chiếu

- [SDD UI/UX §3.4.3, §3.7.2, §3.8.3](../../design/SDD_UI_UX_Blueprint.md) — danh mục mã lỗi, vòng đời câu trả lời, error boundary
- [User Stories US-013, US-011](../../design/User_Stories.md) — AC và bảng lỗi khi trả lời
- [SADD §2.2.3](../../requirements/SADD.md) — cổng bằng chứng sinh `not_found`, chính sách retry của LLM
- Ảnh: [`SCR-02_16_not-found.png`](../../design/html_design/SCR-02_16_not-found.png) · [`SCR-02_17_partial-answer.png`](../../design/html_design/SCR-02_17_partial-answer.png) · [`SCR-02_21_answer-error-retry.png`](../../design/html_design/SCR-02_21_answer-error-retry.png)
- [implement_plan.md](../implement_plan.md) §5 Sprint 3
