# T-302 — Truy xuất theo phạm vi người dùng và cổng bằng chứng

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 3 |
| Story | US-011, US-013 (gián tiếp US-002) |
| Epic | EP-03 |
| Module (SADD §2.2.1) | `retrieval` |
| API liên quan | — (được `qa` gọi trong API-09) |
| Vai trò chính | AI |
| Ước lượng | 3d |
| Phụ thuộc | T-203 (chunk + embedding đã có), T-104 (RLS) |
| Trạng thái | Done (lỗi logic ngưỡng `τ` đã sửa; chỉ còn thiếu đo hiệu năng trên Postgres+pgvector thật và bộ câu hỏi chuẩn của T-501) |

## 1. Mục tiêu

Hiện thực bước truy xuất của pipeline hỏi đáp: từ câu hỏi → tìm các đoạn (`chunk`) liên quan **chỉ trong tài liệu của người dùng hiện tại**, rồi áp **cổng bằng chứng** để quyết định có gọi LLM hay không.

Cổng bằng chứng là cơ chế then chốt bảo vệ nguyên tắc P-04 ("không có bằng chứng thì không khẳng định"): nếu không đủ bằng chứng, hệ thống trả `not_found` **mà không gọi LLM** — nhờ đó câu hỏi kiến thức chung (AC-011.2) và câu hỏi về tài liệu người khác (AC-002.1) không bao giờ nhận câu trả lời bịa.

> Ở Sprint 3 chỉ làm **truy xuất vector chính xác**. Tìm kiếm từ khóa (FTS), hợp nhất RRF và rerank đa dạng thuộc **T-401** (Sprint 4).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-011.1 | Mọi thông tin khẳng định trong câu trả lời đều tìm thấy được trong tài liệu được trích dẫn |
| AC-011.2 | Câu hỏi kiến thức chung (ví dụ "Thủ đô của Pháp?") không được trả lời bằng kiến thức ngoài tài liệu → xử lý như US-013 |
| AC-013.1 | Tập tài liệu không chứa thông tin → thông báo "không tìm thấy", không đưa khẳng định nào |
| AC-013.2 | Bộ ≥ 10 câu hỏi không có đáp án → 100% trả `not_found` (KR2.2) |
| AC-002.1 | Hỏi về nội dung chỉ có trong tài liệu của người khác → `not_found`, không trích dẫn tài liệu đó |
| AC-005.2 | Tài liệu `failed` không bao giờ được dùng làm nguồn |

## 3. Hợp đồng API / giao diện

Interface nội bộ (`app/modules/retrieval/service.py`):

```python
@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: UUID
    document_name: str
    page_start: int
    page_end: int
    content: str
    score: float          # điểm tương đồng đã chuẩn hóa [0..1]

@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]   # rỗng nếu không qua cổng bằng chứng
    top_score: float
    passed_gate: bool              # False => qa trả not_found, KHÔNG gọi LLM
    ready_doc_count: int           # dùng cho meta{ready_doc_count} của SSE

async def retrieve(owner_id: UUID, question: str) -> RetrievalResult: ...
```

Truy vấn vector (pgvector, **tìm kiếm chính xác** — không dùng chỉ mục ANN ở quy mô MVP theo ADR-05):

```sql
SELECT c.id, c.document_id, d.name, c.page_start, c.page_end, c.content,
       1 - (c.embedding <=> $2) AS score
FROM chunk c
JOIN document d ON d.id = c.document_id
WHERE c.owner_id = $1
  AND d.status = 'ready'          -- loại 'processing', 'failed', 'deleting'
ORDER BY c.embedding <=> $2
LIMIT 40;
```

## 4. Thay đổi dữ liệu

Không thêm bảng. Phụ thuộc chỉ mục đã tạo ở T-005/T-203:

| Bảng | Chỉ mục | Mục đích |
|---|---|---|
| `chunk` | B-tree `(owner_id, document_id)` | Lọc phạm vi người dùng trước khi tính khoảng cách vector |
| `document` | `(owner_id, uploaded_at DESC) WHERE status <> 'deleted'` | Đếm `ready_doc_count` |

Tham số cấu hình mới (ConfigMap, P-06):

```yaml
retrieval:
  candidate_limit: 40
  evidence_threshold_tau: 0.15   # [Đề xuất] — CL-03, hiệu chỉnh ở T-502
```

## 5. Các bước triển khai

1. **Phát hiện ngôn ngữ** câu hỏi bằng `lingua-py`, giới hạn tập {vi, en} (kết quả truyền sang `qa` dùng ở T-403; ở Sprint 3 chỉ cần trả ra, chưa cần đổi hành vi).
2. **Embedding câu hỏi**: gọi TEI (`BAAI/bge-m3`) — cùng mô hình đã dùng khi ingest (T-203), nếu khác mô hình thì vector không so sánh được.
3. **Đếm `ready_doc_count`**: `SELECT count(*) FROM document WHERE owner_id=$1 AND status='ready'`. Nếu bằng 0 → trả về cho `qa` để API-09 trả `409 NO_READY_DOCUMENTS` (T-304).
4. **Truy xuất vector chính xác** theo truy vấn ở §3, `LIMIT 40`. Bắt buộc:
   - `owner_id` lấy **từ phiên**, không bao giờ từ request body (P-02);
   - lọc `d.status = 'ready'` — tài liệu đang `deleting` (T-206) bị loại **ngay lập tức** khỏi mọi truy xuất, đây là lý do T-206 đặt trạng thái `deleting` trước khi xóa chunk.
5. **Cổng bằng chứng**: lấy `top_score` của ứng viên cao nhất. Nếu `top_score < τ` (mặc định 0,15):
   - đặt `passed_gate = False`, `chunks = []`;
   - `qa` sẽ trả `done{type:"not_found"}` **mà không gọi LLM** (tiết kiệm chi phí — giảm R-06, và loại hẳn khả năng bịa).
6. Nếu qua cổng: trả tối đa 8 đoạn đầu cho `qa` (Sprint 3 lấy top-8 trực tiếp; T-401 sẽ thay bằng RRF + rerank có ràng buộc đa dạng ≤ 4 đoạn/tài liệu).
7. **Instrument**: metric `retrieval_top_score` (histogram — theo dõi trôi chất lượng, phục vụ R-03), span OTel `retrieval.vector` với số ứng viên và thời gian, **không ghi nội dung câu hỏi hay đoạn trích** (P-03).
8. Ghi `τ` và `candidate_limit` vào cấu hình, **không hard-code** — T-502/T-506 sẽ hiệu chỉnh bằng dữ liệu thật (CL-03).

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi | Ghi chú |
|---|---|---|
| `ready_doc_count = 0` | Trả về cho `qa` → `409 NO_READY_DOCUMENTS` | UI đã khóa ô câu hỏi (AC-011.3); máy chủ vẫn kiểm tra lại |
| `top_score < τ` | `passed_gate = False` → `not_found` | **Không gọi LLM** |
| Người dùng chỉ có tài liệu `failed` | Như trên, `ready_doc_count = 0` | AC-005.2 |
| Tài liệu bị xóa giữa lúc truy xuất | Bị loại nhờ `status <> 'ready'` | NE-08 |
| TEI (embedding) lỗi / timeout | Ném lỗi hạ tầng → `qa` map thành `SERVICE_BUSY` | Không trả `not_found` sai |
| τ đặt quá cao / quá thấp | Rủi ro R-03 | Hiệu chỉnh ở T-502 bằng đường cong trên tập có/không đáp án |

## 7. Kiểm thử bắt buộc

- [x] A hỏi nội dung chỉ có trong tài liệu của B → không đoạn nào của B trả về (AC-002.1, G-03) — đúng vì `retrieve()` luôn lọc `Chunk.owner_id == owner_id` ở tầng SQL (không dựa vào ngưỡng điểm)
- [x] Câu hỏi kiến thức chung → `passed_gate = False` (AC-011.2) — **đã sửa**, xem ghi chú dưới; phủ bằng test `test_retrieve_blocks_low_relevance_evidence_gate` và `test_retrieve_gate_uses_raw_vector_score_not_rrf_constant`
- [ ] Bộ ≥ 10 câu hỏi không đáp án → 100% không qua cổng (AC-013.2) — chưa chạy (thuộc T-501, cần LLM/embedding thật)
- [x] Câu hỏi có đáp án rõ → đoạn đúng trong top-8 — `tests/unit/test_retrieval_service.py` (mới, 5 test, dùng `_FakeSession` mô phỏng `AsyncSession.execute`)
- [x] Tài liệu `processing`/`failed`/`deleting` không xuất hiện — cả 2 truy vấn (vector + FTS) đều có `Document.status == "ready"`
- [ ] Hiệu năng ≤ 50ms/45k chunk — không có Postgres+pgvector thật để đo

## 8. Định nghĩa Hoàn thành

- [x] `τ` (`retrieval_tau`) đọc từ `get_settings()`, đổi được không cần build lại, **và giờ thực sự được so sánh trực tiếp với điểm tương đồng cosine cao nhất** (đã sửa)
- [x] Metric `retrieval_top_score` — đã nối `.observe(top_vector_score)` ngay sau khi tính `top_vector_score` trong `retrieve()`
- [x] Không log nội dung câu hỏi/đoạn trích — xác nhận bằng đọc code
- [x] Test cô lập 2 người dùng trong CI — `tests/integration/test_owner_isolation.py` (mới thêm trong phiên này, dùng Testcontainers, skip khi không có Docker) phủ đúng kịch bản này ở tầng API

### Ghi chú triển khai thực tế — lỗi logic cổng bằng chứng đã sửa

Phiên bản trước lọc bằng chứng bằng
`float(score) >= (1 / (60 + top_k)) or not min_score`, trong đó `score`
là điểm RRF hợp nhất (không phải cosine similarity [0..1]) và `min_score`
(`τ`) chỉ xuất hiện trong `not min_score` (đúng duy nhất khi `τ = 0`) —
nghĩa là `τ` cấu hình không hề được dùng làm ngưỡng thật, cổng gần như
không bao giờ chặn.

**Đã sửa:** tách riêng `top_vector_score` = cosine similarity cao nhất
trong các ứng viên từ truy vấn vector (CHƯA qua RRF), so sánh trực tiếp
`top_vector_score < min_score` → nếu đúng, trả về danh sách bằng chứng
rỗng (`[]`) ngay tại `retrieve()`, trước khi hợp nhất RRF/xếp hạng. Điểm
RRF chỉ còn dùng để **xếp hạng thứ tự** các đoạn đã qua cổng (đúng vai
trò của T-401), không còn lẫn vào quyết định "có đủ bằng chứng hay
không" nữa. `qa/service.py::stream_answer` cũng được sửa đồng thời: khi
`retrieve()` trả về rỗng, trả thẳng `not_found` mà **không gọi LLM**
(sửa luôn phần lệch ở T-304).

Xác nhận bằng: `ruff check .`, `mypy app`, `lint-imports` đều sạch; 5 test
mới trong `tests/unit/test_retrieval_service.py` (bao gồm 1 test hồi quy
đặt tên rõ `test_retrieve_gate_uses_raw_vector_score_not_rrf_constant` để
tránh tái diễn đúng lỗi này) và 3 test trong `tests/unit/test_qa_service.py`
đều chạy qua `python -m pytest` thật.

Còn tồn đọng: chưa đo được trên Postgres+pgvector thật (không có Docker
trong môi trường này) nên chỉ xác minh logic bằng `AsyncSession.execute`
giả lập, chưa đo hiệu năng ≤ 50ms/45k chunk; bộ ≥10 câu hỏi không đáp án
(AC-013.2) cần chạy thật ở T-501 với embedding/LLM thật.

## 9. Tham chiếu

- [SADD §2.2.3](../../requirements/SADD.md) — bảng thiết kế chi tiết pipeline, cổng bằng chứng, ADR-05
- [User Stories US-011, US-013, US-002](../../design/User_Stories.md)
- [implement_plan.md](../implement_plan.md) §5 Sprint 3, §7 R-02/R-03, §9 CL-03
