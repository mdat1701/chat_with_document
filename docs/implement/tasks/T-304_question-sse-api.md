# T-304 — API hội thoại và luồng câu trả lời SSE

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | US-011 (nền cho US-012 – US-017) |
| Epic | EP-03 |
| Module (SADD §2.2.1) | `qa`, `api` |
| API liên quan | **API-08** `POST /conversations`, **API-09** `POST /conversations/{cid}/questions` |
| Vai trò chính | BE |
| Ước lượng | 3d |
| Phụ thuộc | T-301, T-302, T-303, T-105 (rate limit) |
| Trạng thái | To do |

## 1. Mục tiêu

Ghép `retrieval` (T-302), prompt + kiểm tra trích dẫn (T-303) và `LLMPort` (T-301) thành endpoint SSE hoàn chỉnh mà front-end tiêu thụ, đúng thứ tự sự kiện đã chốt trong SADD §2.4.2.

Đồng thời ghi **metadata** câu trả lời vào CSDL (không ghi nội dung — ADR-10) và phát sự kiện analytics `answer_rendered`.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-011.1 | Gửi câu hỏi có đáp án trong tài liệu → nhận câu trả lời có căn cứ |
| AC-011.3 | Chưa có tài liệu "Sẵn sàng" → ô câu hỏi bị vô hiệu (UI); máy chủ vẫn kiểm tra lại → `409 NO_READY_DOCUMENTS` |
| AC-011.4 | Ô câu hỏi trống hoặc chỉ khoảng trắng → không gửi được (UI chặn, máy chủ trả `400 QUESTION_INVALID`) |
| KR1.2 | p90 từ lúc gửi tới khi hiển thị đầy đủ ≤ 15 giây |
| US-020 | Sự kiện đo lường **không** chứa nội dung câu hỏi/câu trả lời |

## 3. Hợp đồng API / giao diện

```http
POST /conversations
→ 201 { "conversation_id": "uuid" }       # trạng thái phiên ngắn hạn, không lưu DB
```

```http
POST /conversations/{cid}/questions
Content-Type: application/json
X-CSRF-Token: <token từ GET /me>
{ "text": "Thời hạn thanh toán với đối tác A là bao lâu?" }

→ 200 Content-Type: text/event-stream
```

Thứ tự sự kiện SSE (**bắt buộc đúng**):

```
event: meta
data: {"answer_id":"uuid","ready_doc_count":9}

event: delta
data: {"text":"Thời hạn thanh toán là "}
event: delta
data: {"text":"**30 ngày** kể từ ngày ký [1]."}
… (n lần)

event: citations
data: {"items":[{"index":1,"document_id":"uuid","document_name":"HopDong_DoiTacA.pdf","page_start":12,"page_end":12}]}

event: done
data: {"type":"answered","latency_ms":6200,"uncited":false}
```

Hoặc kết thúc bằng lỗi:

```
event: error
data: {"code":"SERVICE_BUSY"}
```

Mã lỗi HTTP (trả trước khi mở stream):

| Mã | Điều kiện |
|---|---|
| `400 QUESTION_INVALID` | `text` rỗng sau trim hoặc > DF-07 (2.000 ký tự) |
| `409 NO_READY_DOCUMENTS` | `ready_doc_count = 0` |
| `429 RATE_LIMITED` | Vượt 10 câu hỏi/phút/người dùng |
| `401 SESSION_EXPIRED` / `403 NOT_AUTHORIZED` | Phiên/quyền |

## 4. Thay đổi dữ liệu

Sau khi hoàn tất câu trả lời, ghi **một** hàng `answer` — **chỉ metadata**:

| Cột | Giá trị |
|---|---|
| `id` | = `answer_id` đã gửi trong `meta` |
| `owner_id` | Từ phiên |
| `conversation_id`, `turn_index` | Từ ngữ cảnh phiên |
| `answer_type` | `answered` / `partial` / `not_found` |
| `latency_ms` | Từ lúc nhận request tới `done` |
| `citation_count`, `cited_doc_count` | Từ kết quả T-303 |
| `prompt_version`, `model_id` | Từ T-303 / T-301 |
| `created_at` | `now()` |

> **Tuyệt đối không** lưu `text` câu hỏi hay nội dung câu trả lời (ADR-10, P-03).

Ngoài ra: `INSERT analytics_event` tên `answer_rendered` với thuộc tính allow-list (`latency_ms`, `answer_type`, `citation_count`) — chi tiết allow-list ở T-404.

## 5. Các bước triển khai

1. `POST /conversations`: sinh `conversation_id` (UUID), lưu trạng thái hội thoại ngắn hạn trong Redis với TTL phiên. Không tạo bảng CSDL (DF-09 — không giữ lịch sử dài hạn).
2. `POST /conversations/{cid}/questions`:
   a. Validate CSRF + phiên; validate `text` (trim, 1…DF-07) → `400 QUESTION_INVALID`.
   b. Kiểm tra rate limit 10 câu/phút (Redis token bucket, T-105) → `429 RATE_LIMITED` kèm header `Retry-After`.
   c. Gọi `retrieval.retrieve()` (T-302). `ready_doc_count = 0` → `409 NO_READY_DOCUMENTS`.
3. Mở `StreamingResponse` với `media_type="text/event-stream"`, header `Cache-Control: no-cache`, `X-Accel-Buffering: no` (**bắt buộc** để Ingress NGINX không buffer làm mất tính "hiện dần").
4. Gửi ngay `event: meta` với `answer_id` (sinh trước) và `ready_doc_count` — client dùng để hiển thị "Đang tìm trong N tài liệu…" (IX-03, ≤ 300 ms).
5. **Nếu `passed_gate = False`** (cổng bằng chứng, T-302): bỏ qua LLM, gửi thẳng `done{type:"not_found", latency_ms}`. Đây là đường đi rẻ nhất và là lý do câu hỏi kiến thức chung không tốn chi phí LLM.
6. Nếu qua cổng: gọi `qa` (T-303) → stream `delta` từng mẩu đã ánh xạ `[S#]→[n]`.
7. Sau khi LLM kết thúc: gửi `event: citations` rồi `event: done`. Thứ tự này cố định — client chỉ hiển thị thẻ nguồn khi `phase='complete'` (IR-01).
8. **Timeout tổng phía client là DF-10 = 60s**; máy chủ hủy lời gọi LLM ở 50s (T-301) để còn kịp gửi `error{code:"ANSWER_TIMEOUT"}` trước khi client tự timeout.
9. Bắt `LLMError` → chuyển thành `event: error` với `code` tương ứng (`SERVICE_BUSY`, `ANSWER_TIMEOUT`, `ANSWER_INTERRUPTED`). **Không** đóng kết nối im lặng.
10. Client ngắt kết nối (đóng tab, bấm Esc): phát hiện qua `request.is_disconnected()` → hủy coroutine LLM, **không** ghi hàng `answer`.
11. Ghi `answer` + `analytics_event` sau khi gửi `done` thành công.
12. Span OTel: `http.request` → `retrieval.vector` → `llm.stream` → `qa.validate_citations`, thuộc tính `model_id`, `prompt_version`, số token, `ttft_ms`.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Không có tài liệu ready | `409 NO_READY_DOCUMENTS` trước khi mở stream |
| Câu hỏi > 2.000 ký tự | `400 QUESTION_INVALID` (UI đã chặn ở ER-09, máy chủ kiểm tra lại) |
| Vượt 10 câu/phút | `429 RATE_LIMITED` + `Retry-After` |
| LLM quá tải trước token đầu | `event: error {code:"SERVICE_BUSY"}` |
| Quá 50s | `event: error {code:"ANSWER_TIMEOUT"}` |
| Đứt sau khi đã stream | `event: error {code:"ANSWER_INTERRUPTED"}`, UI ẩn thẻ nguồn (IR-01) |
| Client đóng tab giữa chừng | Hủy LLM, không ghi `answer`, không tính vào analytics |
| Proxy buffer làm mất streaming | Đặt `X-Accel-Buffering: no`; kiểm thử qua Ingress thật, không chỉ localhost |

## 7. Kiểm thử bắt buộc

- [ ] Thứ tự sự kiện đúng: `meta` → `delta`×n → `citations` → `done`
- [ ] Nhánh cổng bằng chứng: `meta` → `done{type:"not_found"}`, **không có** `delta`, **không gọi LLM** (assert bằng mock)
- [ ] `409`, `400`, `429` trả đúng trước khi mở stream
- [ ] Ngắt kết nối client → lời gọi LLM bị hủy (mock ghi nhận), không có hàng `answer` mới
- [ ] Bảng `answer` sau một lượt hỏi **không** chứa chuỗi nào của câu hỏi/câu trả lời (test quét nội dung — hỗ trợ G-04)
- [ ] E2E qua Ingress staging: nội dung thực sự hiện dần, không bị buffer
- [ ] Đo p90 latency trên bộ câu hỏi mẫu ≤ 15s (KR1.2, đối chiếu lại ở T-505)

## 8. Định nghĩa Hoàn thành

- [ ] Luồng hỏi → trả lời có nguồn chạy end-to-end trên staging (mốc M-3)
- [ ] `answer` chỉ chứa metadata; kiểm thử tự động xác nhận không có nội dung
- [ ] `analytics_event answer_rendered` được phát đúng một lần mỗi câu trả lời
- [ ] Trace đầy đủ 4 span, có `ttft_ms`

## 9. Tham chiếu

- [SADD §2.2.3, §2.4.2, §3.2.2](../../requirements/SADD.md) — pipeline, hợp đồng API-08/09, sequence diagram và ngân sách độ trễ
- [User Stories US-011](../../design/User_Stories.md)
- [SDD UI/UX §3.5.1, §3.7.2](../../design/SDD_UI_UX_Blueprint.md) — hợp đồng API phía UI, vòng đời câu trả lời
- [implement_plan.md](../implement_plan.md) §5 Sprint 3, mốc M-3
