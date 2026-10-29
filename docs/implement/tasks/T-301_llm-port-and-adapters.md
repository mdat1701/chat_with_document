# T-301 — `LLMPort` và hai adapter nhà cung cấp

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | — (hạ tầng cho US-011 – US-017) |
| Epic | EP-03 |
| Module (SADD §2.2.1) | `ports/`, `adapters/` |
| API liên quan | — (nội bộ, phục vụ API-09) |
| Vai trò chính | TL |
| Ước lượng | 3d |
| Phụ thuộc | **D-01** (ADR-03 — chốt phương án LLM), T-007 (logging/OTel) |
| Trạng thái | In progress (port/2 adapter chạy được; retry/circuit-breaker/phân loại lỗi/metric đã cài trong phiên này; chưa chạy trên LLM thật) |

## 1. Mục tiêu

Dựng cổng trừu tượng `LLMPort` để module `qa` **không phụ thuộc** vào nhà cung cấp LLM cụ thể, cùng hai adapter hiện thực:

- **Phương án A** — API được quản lý trong vùng ATTT phê duyệt (ví dụ Claude Sonnet qua Amazon Bedrock).
- **Phương án B** — mô hình mở tự lưu trữ qua vLLM (giao thức openai-compatible).

Nhờ ADR-03, khi **D-01** được chốt theo hướng nào thì **chỉ đổi cấu hình adapter**, không sửa code miền. Đây là biện pháp giảm thiểu rủi ro R-01 (ATTT không cho phép LLM bên ngoài).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-011.1 | Câu trả lời sinh ra từ LLM phải dựa trên các đoạn được cung cấp (adapter phải truyền đúng prompt và stream lại nguyên vẹn) |
| BR-019 | Chỉ câu hỏi và tối đa 8 đoạn trích được gửi tới LLM; không gửi toàn bộ tài liệu |
| P-03 | Prompt/nội dung trả lời **không** được ghi vào log, trace hay metric |
| TC-08 | Timeout tổng phía máy chủ 50s, nằm trong ngân sách DF-10 = 60s của client |

## 3. Hợp đồng API / giao diện

Interface nội bộ (Python, `app/ports/llm.py`):

```python
from dataclasses import dataclass
from typing import AsyncIterator, Literal, Sequence

@dataclass(frozen=True)
class LLMMessage:
    role: Literal["system", "user"]
    content: str

@dataclass(frozen=True)
class LLMParams:
    temperature: float = 0.1
    max_tokens: int = 900
    timeout_s: int = 50          # nằm trong DF-10 = 60s của client

class LLMError(Exception):
    """code ∈ {SERVICE_BUSY, ANSWER_TIMEOUT, ANSWER_INTERRUPTED}"""
    code: str
    tokens_emitted: int          # > 0 nghĩa là đã gửi nội dung cho client

class LLMPort(Protocol):
    @property
    def model_id(self) -> str: ...

    async def stream(
        self,
        messages: Sequence[LLMMessage],
        params: LLMParams,
    ) -> AsyncIterator[str]:
        """Yield từng mẩu văn bản. Hủy (cancel) coroutine => hủy lời gọi LLM."""
```

Cấu hình chọn adapter (ConfigMap, P-06 — không hard-code):

```yaml
llm:
  provider: managed_api | self_hosted   # D-01
  model_id: "<tên model>"
  endpoint: "<url nội bộ hoặc endpoint vùng được duyệt>"
  temperature: 0.1
  max_tokens: 900
  timeout_s: 50
  breaker:
    failure_threshold: 5
    open_seconds: 30
```

## 4. Thay đổi dữ liệu

Không đổi schema. Chỉ ghi `model_id` vào bảng `answer` ở T-304 (metadata, không nội dung).

## 5. Các bước triển khai

1. Định nghĩa `LLMPort` (Protocol) + `LLMMessage`, `LLMParams`, `LLMError` trong `app/ports/llm.py`. Quy tắc DR: `modules/*` chỉ import `ports/`, không import `adapters/`.
2. Viết `adapters/bedrock_llm.py` (phương án A): gọi streaming API của nhà cung cấp trong vùng được duyệt, map lỗi nhà cung cấp → `LLMError.code`.
3. Viết `adapters/openai_compat_llm.py` (phương án B): gọi endpoint vLLM `/v1/chat/completions` với `stream=true`; cùng cách map lỗi.
4. Factory `adapters/llm_factory.py` đọc `llm.provider` từ config và trả về adapter tương ứng; đăng ký qua dependency injection của FastAPI.
5. **Chính sách lỗi** (khác nhau theo thời điểm hỏng — bắt buộc đúng):
   - Hỏng **trước token đầu tiên** (`tokens_emitted == 0`): retry **đúng 1 lần**; vẫn hỏng → `LLMError(code="SERVICE_BUSY")`.
   - Hỏng **sau khi đã gửi** nội dung (`tokens_emitted > 0`): **không retry** → `LLMError(code="ANSWER_INTERRUPTED")`.
   - Quá `timeout_s` = 50s → `LLMError(code="ANSWER_TIMEOUT")`, hủy lời gọi phía nhà cung cấp.
   - Client ngắt kết nối SSE → coroutine bị cancel → adapter phải **đóng kết nối tới LLM** (giải phóng token/chi phí, giảm R-06).
6. Circuit breaker bọc adapter: mở sau 5 lần lỗi liên tiếp trong cửa sổ, giữ mở 30 giây, trong thời gian mở trả ngay `SERVICE_BUSY` (không gọi nhà cung cấp). Metric `circuit_breaker_state`.
7. Instrument metric: `llm_ttft_seconds` (histogram, thời gian tới token đầu), `llm_tokens_total{direction="in|out"}`, `llm_errors_total{code}`. Span OTel `llm.stream` với thuộc tính `model_id`, `prompt_version`, số token — **tuyệt đối không ghi nội dung prompt/answer** (P-03).
8. Viết fake adapter `adapters/fake_llm.py` cho unit test và E2E (phát lại kịch bản streaming cố định, không tốn chi phí) — dùng trong CI.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Mã trả về | Ghi chú |
|---|---|---|
| Nhà cung cấp 5xx/quá tải trước token đầu | `SERVICE_BUSY` | Sau 1 lần retry |
| Vượt 50s | `ANSWER_TIMEOUT` | Client còn 10s dự phòng trước DF-10 |
| Đứt kết nối sau khi đã stream | `ANSWER_INTERRUPTED` | Không retry; UI ẩn thẻ nguồn (IR-01) |
| Circuit breaker đang mở | `SERVICE_BUSY` | Trả ngay, không gọi nhà cung cấp |
| Client đóng tab giữa chừng | — | Hủy lời gọi LLM, không ghi `answer` |
| D-01 chưa chốt | — | Chạy phương án A trên tài liệu **không nhạy cảm** (Giả định A-04) |

## 7. Kiểm thử bắt buộc

- [x] Retry 1 lần trước token đầu rồi `SERVICE_BUSY` — **đã cài**: `OpenAICompatibleLLM.stream()` thử lại đúng 1 lần nếu lỗi xảy ra trước token đầu (`tokens_emitted == 0`), vẫn hỏng thì raise `LLMError("SERVICE_BUSY")` — test `test_retries_once_before_first_token_then_succeeds` + `test_fails_before_first_token_twice_raises_service_busy`
- [x] Lỗi sau khi đã yield ≥ 1 mẩu → `ANSWER_INTERRUPTED`, không retry — **đã sửa**: `conversations.py` giờ bắt riêng `LLMError` và phát đúng `exc.code` (thay vì gộp chung `SERVICE_BUSY`) — test `test_failure_after_first_token_is_interrupted_without_retry`
- [x] Vượt `timeout_s` → `ANSWER_TIMEOUT` — `httpx.TimeoutException` được bắt riêng và phân loại đúng mã trước khi token đầu — test `test_timeout_before_first_token_raises_answer_timeout`; dùng `settings.llm_timeout_s` (mới, mặc định 50s theo TC-08) thay vì tái dùng `answer_timeout_ms` (60s, ngân sách DF-10 phía client)
- [ ] Hủy coroutine đóng stream — `async with client.stream(...)` tự đóng khi context thoát, nhưng chưa có test xác nhận `aclose` được gọi khi coroutine bị hủy giữa chừng
- [x] Circuit breaker mở sau N lỗi — **đã cài**: breaker theo tiến trình (module-level, không cần Redis cho MVP-lite) trong `adapters/openai_llm.py`, mở sau `settings.llm_breaker_failure_threshold` lỗi liên tiếp, tự đóng sau `llm_breaker_open_seconds` — test `test_circuit_breaker_opens_after_threshold_and_skips_calls`
- [x] Đổi `llm.provider` không cần sửa `modules/qa` — đúng: `modules/qa/service.py` chỉ biết `LLMPort`, việc chọn `FakeLLM`/`OpenAICompatibleLLM` nằm ở `api.deps.get_llm_port()` theo `settings.llm_provider`
- [x] Không log/metric/trace chứa nội dung prompt/answer — xác nhận bằng đọc code (không có log nào in `request.user`/token nội dung)

## 8. Định nghĩa Hoàn thành

- [x] `import-linter` xanh — xác nhận (3 contract pass, bao gồm `modules/*` không import `adapters/*`)
- [ ] Cả hai adapter chạy trên staging — chưa có staging/LLM endpoint thật
- [x] Metric `llm_ttft_seconds`, `llm_tokens_total`, `circuit_breaker_state` — đã thêm vào `core/metrics.py`, nối `.observe()`/`.inc()`/`.set()` thật trong `OpenAICompatibleLLM.stream()`; thêm cả `llm_errors_total{code}` (không có trong DoD gốc nhưng cùng mục đích quan sát)
- [x] Fake adapter dùng trong CI không gọi mạng — `FakeLLM.stream` chỉ `yield` một chuỗi cố định
- [x] Ghi chú ATTT về dữ liệu rời TB-2 — xem mục riêng "Ghi chú ATTT — dữ liệu rời TB-2" dưới đây

### Ghi chú ATTT — dữ liệu rời TB-2

Theo nguyên tắc tối thiểu hóa dữ liệu của SADD §4.1.3 (BR-019): toàn bộ
PDF, bước trích xuất, embedding và rerank chạy trong TB-2 (hạ tầng nội
bộ); **chỉ** câu hỏi và tối đa `settings.rerank_top_out` đoạn trích
(mặc định **8 đoạn**, ~500 token/đoạn theo `chunk_size_tokens` — tổng
~4.000 token) được gửi ra TB-3 (dịch vụ LLM) cho mỗi câu hỏi. Xác nhận
bằng đọc đúng đường đi của dữ liệu trong code (không phải suy đoán từ
tài liệu thiết kế):

1. `qa/service.py::stream_answer` gọi `retrieve()` rồi `diversify_evidence(
   limit=settings.rerank_top_out)` — giới hạn cứng số đoạn trước khi dựng
   prompt, không có đường nào gửi nguyên văn PDF hay toàn bộ `chunk` của
   một tài liệu ra ngoài hàm này.
2. `qa/prompt.py::build_prompt` chỉ ghép `question` + nội dung từng đoạn
   đã được giới hạn ở bước 1 (bọc trong thẻ `<source>`, xem T-303) — không
   đưa thêm trường nào khác (không `document_name`, không metadata khác)
   vào phần nội dung gửi LLM ngoài những gì đã qua cổng bằng chứng.
3. `LLMRequest` (`ports/llm_port.py`) chỉ có 4 trường: `system`, `user`
   (= `build_prompt(...)`), `model`, `temperature` — không có trường nào
   mang dữ liệu khác của người dùng (không `user_id`, không `email`).
4. Lựa chọn phương án A/B (ADR-03) hoàn toàn qua cấu hình
   (`settings.llm_provider`, `llm_base_url`) — đổi phương án không cần
   sửa `modules/qa` hay `modules/retrieval` (đã xác nhận ở DoD khác).

**Việc KHÔNG thể xác nhận trong môi trường này:** hợp đồng xử lý dữ liệu
với nhà cung cấp (zero data retention, không huấn luyện lại mô hình),
kết nối riêng (PrivateLink/VPC endpoint) giữa TB-2 và TB-3, và TLS giữa
TEI/PostgreSQL/Redis trong TB-2 — đây đều là cấu hình hạ tầng/hợp đồng
ngoài phạm vi code, cần ATTT xác nhận trước khi mở pilot (G-04, cùng cổng
với T-503).

### Ghi chú triển khai thực tế

Kiến trúc port/adapter đúng (`LLMPort` trong `ports/`, 2 adapter trong
`adapters/`, lựa chọn qua DI ở `api/deps.py`) và kiểm tra tĩnh sạch.

**Đã sửa (phiên này) — cả 4 khoảng trống engineering đã nêu trước đó:**
1. Retry đúng 1 lần khi lỗi xảy ra **trước** token đầu tiên.
2. Circuit breaker tự viết (module-level, không dùng thư viện ngoài) —
   mở sau `settings.llm_breaker_failure_threshold` lỗi liên tiếp, tự đóng
   sau `llm_breaker_open_seconds`.
3. Thêm `LLMError(code, tokens_emitted)` vào `app/ports/llm_port.py`;
   `OpenAICompatibleLLM.stream()` phân loại đúng `SERVICE_BUSY` /
   `ANSWER_TIMEOUT` / `ANSWER_INTERRUPTED` tùy thời điểm lỗi xảy ra;
   `conversations.py::stream()` bắt riêng `LLMError` và phát đúng
   `exc.code` thay vì gộp chung một mã.
4. Metric `llm_ttft_seconds` (histogram), `llm_tokens_total{direction}`,
   `llm_errors_total{code}`, `circuit_breaker_state` (gauge) — khai báo
   trong `core/metrics.py` và nối thật trong adapter.

Thêm `settings.llm_timeout_s` (mặc định 50s, TC-08) thay vì tái dùng
`answer_timeout_ms` (60s — đó là DF-10, ngân sách TỔNG phía client, không
phải timeout gọi LLM riêng lẻ) — sửa luôn một lệch nhỏ so với spec.

Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports` (3 hợp đồng vẫn
giữ) và 6 test mới trong `tests/unit/test_openai_llm.py` (monkeypatch
`_stream_once` để cô lập logic retry/breaker khỏi `httpx` thật — không
cần LLM endpoint thật để kiểm chứng hành vi resilience).

**Chưa làm:** cả hai adapter chưa chạy trên LLM thật/staging; chưa có
test xác nhận `aclose()` được gọi khi coroutine bị hủy giữa chừng (client
đóng tab); circuit breaker là theo-tiến-trình nên không chia sẻ trạng
thái giữa nhiều worker process (chấp nhận được cho MVP-lite một
instance, cần Redis nếu scale ngang nhiều worker).

## 9. Tham chiếu

- [SADD §2.2.3, Phụ lục C ADR-03](../../requirements/SADD.md) — pipeline hỏi đáp, quyết định cổng LLM
- [User Stories US-011](../../design/User_Stories.md) — ghi chú kiến trúc về LLM
- [implement_plan.md](../implement_plan.md) §5 Sprint 3, §6 D-01, §7 R-01/R-06
