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
| Trạng thái | To do |

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

- [ ] Unit: lỗi trước token đầu → retry đúng **1** lần rồi `SERVICE_BUSY`
- [ ] Unit: lỗi sau khi đã yield ≥ 1 mẩu → **không** retry, trả `ANSWER_INTERRUPTED`
- [ ] Unit: vượt `timeout_s` → `ANSWER_TIMEOUT` và kết nối tới nhà cung cấp được đóng
- [ ] Unit: hủy coroutine → adapter đóng stream (kiểm tra bằng mock ghi nhận `aclose`)
- [ ] Unit: breaker mở sau 5 lỗi, trả `SERVICE_BUSY` tức thì, tự đóng sau 30s
- [ ] Đổi `llm.provider` giữa A và B **không cần sửa code** `modules/qa`
- [ ] Kiểm thử tự động: không có log/metric/trace nào chứa nội dung prompt hoặc answer (P-03)

## 8. Định nghĩa Hoàn thành

- [ ] `import-linter` xanh: `modules/*` không import `adapters/*`
- [ ] Cả hai adapter chạy được trên staging với tài liệu không nhạy cảm
- [ ] Metric `llm_ttft_seconds`, `llm_tokens_total`, `circuit_breaker_state` hiển thị trên Grafana
- [ ] Fake adapter dùng được trong CI, không gọi mạng ngoài
- [ ] Ghi chú cho ATTT: danh sách chính xác dữ liệu rời khỏi TB-2 (câu hỏi + ≤ 8 đoạn trích) — đầu vào cho Pilot Gate G-04

## 9. Tham chiếu

- [SADD §2.2.3, Phụ lục C ADR-03](../../requirements/SADD.md) — pipeline hỏi đáp, quyết định cổng LLM
- [User Stories US-011](../../design/User_Stories.md) — ghi chú kiến trúc về LLM
- [implement_plan.md](../implement_plan.md) §5 Sprint 3, §6 D-01, §7 R-01/R-06
