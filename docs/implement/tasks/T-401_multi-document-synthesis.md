# T-401 — Tổng hợp câu trả lời từ nhiều tài liệu

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 4 |
| Story | US-012 |
| Epic | EP-03 — Hỏi đáp trên tài liệu |
| Module (SADD §2.2.1) | `retrieval`, `qa` |
| API liên quan | API-09 `POST /conversations/{cid}/questions` |
| Vai trò chính | AI (chính) + BE |
| Ước lượng | 2 ngày công |
| Phụ thuộc | T-302 (truy xuất vector + cổng bằng chứng), T-303 (prompt v1 + kiểm tra trích dẫn) |
| Trạng thái | In progress (FTS+RRF+đa dạng hoá đã làm ở T-302; cross-encoder rerank đã cài trong phiên này, chưa chạy với TEI thật) |

## 1. Mục tiêu

Nâng bước truy xuất từ **chỉ vector** (T-302) lên **truy xuất lai** để câu trả lời tổng hợp được thông tin nằm rải rác ở nhiều tài liệu, và khi hai tài liệu mâu thuẫn thì nêu cả hai kèm nguồn riêng thay vì chọn bừa một bên.

Ba thay đổi kỹ thuật:
1. Bổ sung **tìm kiếm từ khóa** (PostgreSQL FTS) song song với tìm kiếm vector.
2. **Hợp nhất** hai danh sách kết quả bằng Reciprocal Rank Fusion, rồi **rerank** bằng cross-encoder.
3. **Đảm bảo đa dạng tài liệu** trong 8 đoạn gửi LLM, và cập nhật prompt để xử lý mâu thuẫn.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-012.1 | Đáp án nằm ở 2 tài liệu khác nhau (ví dụ: giá trị hợp đồng ở tài liệu X, điều khoản thanh toán ở tài liệu Y) → câu trả lời chứa thông tin từ **cả hai** và trích dẫn cả X lẫn Y |
| AC-012.2 | Hai tài liệu có thông tin **mâu thuẫn** về cùng một nội dung → câu trả lời nêu **cả hai** thông tin và nguồn của từng thông tin, thay vì chỉ chọn một |
| AC-014.2 | Câu trả lời tổng hợp từ N tài liệu → có thẻ nguồn cho cả N tài liệu |

## 3. Hợp đồng API / giao diện

API-09 **không đổi** về mặt hợp đồng; chỉ thay đổi chất lượng tập đoạn đưa vào LLM. Thứ tự sự kiện SSE giữ nguyên:

```
meta      {answer_id, ready_doc_count}
delta     {text}            × n
citations {items: [{index, document_id, document_name, page_start, page_end}, ...]}
done      {type, latency_ms, uncited?}
```

Pipeline truy xuất sau task này (SADD §2.2.3):

```
câu hỏi
  ├─ embedding  → vector search  (owner_id, doc_status='ready')  top-40
  └─ FTS        → ts_rank_cd                                     top-40
            ↓
     RRF hợp nhất (k = 60)
            ↓
     rerank cross-encoder trên top-20 → giữ top-8
            ↓
     lọc đa dạng: tối đa 4 chunk / tài liệu
            ↓
     cổng bằng chứng (τ) → prompt S1..S8
```

## 4. Thay đổi dữ liệu

| Đối tượng | Thay đổi |
|---|---|
| `chunk.tsv` | Cột generated `to_tsvector('simple', unaccent(content))` — đã khai báo từ T-005/T-203; task này **xác nhận** cột tồn tại và đúng cấu hình `simple` (PostgreSQL không có từ điển tiếng Việt) |
| Chỉ mục GIN `chunk(tsv)` | Bổ sung migration nếu chưa có — bắt buộc để FTS top-40 chạy nhanh |
| Extension `unaccent` | Bảo đảm đã `CREATE EXTENSION unaccent` trong migration baseline |
| `answer.cited_doc_count` | Bắt đầu ghi giá trị thật (số tài liệu riêng biệt được trích dẫn) để theo dõi AC-012.1 |

Không thêm bảng mới.

## 5. Các bước triển khai

1. **FTS query** trong `retrieval`: truy vấn `chunk` theo `owner_id` + tài liệu `ready`, xếp hạng bằng `ts_rank_cd(tsv, websearch_to_tsquery('simple', unaccent(:q)))`, lấy **top-40**. Mục đích: bắt số hợp đồng, mã, tên riêng mà vector hay bỏ sót.
2. **RRF hợp nhất**: với mỗi chunk xuất hiện trong danh sách vector và/hoặc FTS, tính `score = Σ 1/(60 + rank_i)` (k = 60). Sắp xếp giảm dần, giữ **top-20** đưa sang rerank.
3. **Rerank**: gọi TEI với `BAAI/bge-reranker-v2-m3` (cross-encoder) trên cặp (câu hỏi, nội dung chunk) cho 20 ứng viên; giữ **top-8** theo điểm rerank.
4. **Lọc đa dạng**: duyệt danh sách top-8 theo thứ tự điểm giảm dần, **tối đa 4 chunk cho mỗi `document_id`**; nếu sau khi lọc chưa đủ 8 đoạn thì lấy bù từ các ứng viên còn lại. **Ngoại lệ:** nếu chỉ có đúng 1 tài liệu liên quan trong tập ứng viên thì bỏ giới hạn 4 (tránh cắt mất bằng chứng khi người dùng chỉ có 1 tài liệu).
5. **Cổng bằng chứng**: ngưỡng τ nay áp lên **điểm rerank cao nhất** (không phải điểm vector thô) — giữ nguyên hành vi `not_found` khi dưới ngưỡng (T-302). Ghi lại τ dùng thực tế vào metric `retrieval_top_score`.
6. **Cập nhật prompt (phối hợp T-303)**: bổ sung hai ràng buộc —
   - "Khi thông tin cần thiết nằm ở nhiều đoạn thuộc các tài liệu khác nhau, hãy tổng hợp đầy đủ và gắn nguồn `[S#]` cho từng khẳng định."
   - "Khi các đoạn **mâu thuẫn** nhau về cùng một nội dung, hãy nêu **cả hai** giá trị kèm nguồn tương ứng; **không** tự chọn một bên." (AC-012.2)
7. Tăng `prompt_version` và ghi vào `answer.prompt_version` để đối chiếu khi đánh giá chất lượng ở T-501.
8. Thêm span OTel `retrieval.fts` và `retrieval.rerank` (SADD §4.3) để đo ngân sách độ trễ.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| TEI reranker không phản hồi / timeout | Ghi cảnh báo, **bỏ qua bước rerank**, dùng thẳng top-8 từ RRF; không được làm hỏng cả câu trả lời |
| Chỉ có 1 tài liệu `ready` | Bỏ giới hạn 4 chunk/tài liệu; kết quả giống hành vi Sprint 3 |
| FTS trả về 0 kết quả (câu hỏi toàn từ phổ thông) | RRF vẫn chạy với riêng danh sách vector — không coi là lỗi |
| Mâu thuẫn nhưng LLM vẫn chọn một bên | Không chặn tự động được ở code; bắt bằng ca kiểm thử chuyên biệt trong bộ câu hỏi chuẩn (T-501) và hiệu chỉnh prompt ở T-502 |
| Tài liệu bị xóa giữa lúc truy xuất | Bước kiểm tra trích dẫn (T-303) loại trích dẫn trỏ tới tài liệu không còn tồn tại (NE-08) |

## 7. Kiểm thử bắt buộc

- [ ] AC-012.1 (đáp án rải 2 tài liệu) — logic RRF hợp nhất vector+FTS hỗ trợ việc này về nguyên tắc; giờ đã có test cho `retrieve()` (xem các mục dưới) nhưng chưa có ca cụ thể cho "2 tài liệu khác nhau" — cần Postgres thật hoặc fixture phức tạp hơn
- [ ] AC-012.2 (mâu thuẫn, nêu cả hai nguồn) — phụ thuộc hành vi LLM thật theo `prompt.py::build_prompt` ("Nếu có mâu thuẫn, nêu cả hai giá trị"), không kiểm chứng được với `FakeLLM`
- [x] Đa dạng tài liệu — `diversify_evidence(max_chunks_per_doc=4, limit=8)`; test `test_diversify_evidence_caps_chunks_per_document` (`tests/unit/test_retrieval_service.py`)
- [x] FTS tìm được mã dạng `HD-2026/A-17` — dùng `websearch_to_tsquery('simple', unaccent(query_text))`, về nguyên tắc đúng vì FTS không phụ thuộc embedding; chưa test với Postgres thật
- [x] Không dấu khớp có dấu nhờ `unaccent` — cả truy vấn và `tsv` đều áp `unaccent`, nhất quán hai chiều
- [x] Rerank lỗi vẫn trả lời được — **đã cài**: `TeiRerankerAdapter.rerank()` ném `RuntimeError` khi TEI lỗi/hình dạng phản hồi sai, `retrieve()` bắt riêng `RuntimeError` và quay về xếp hạng RRF thô, không làm hỏng câu trả lời — test `test_retrieve_falls_back_to_rrf_when_reranker_fails`
- [ ] p90 ≤ 15s — không đo được (không có staging/LLM/TEI reranker thật)

## 8. Định nghĩa Hoàn thành

- [ ] AC-012.1/AC-012.2 có test tự động trong CI — chưa có (cần Postgres+LLM thật)
- [x] `answer.cited_doc_count` — tính bằng `len({item["document_id"] for item in citations})` trong `conversations.py`
- [ ] Chỉ mục GIN trên `chunk(tsv)` — khai báo `Index("ix_chunk_tsv_gin", "tsv", postgresql_using="gin")` trong model, chưa `EXPLAIN` trên Postgres thật
- [ ] Span `retrieval.fts`/`retrieval.rerank` trong trace — không có span thủ công nào cho các bước này
- [x] `prompt_version="v2"` ghi vào `answer`
- [x] Không log nội dung — xác nhận bằng đọc code
- [x] `rrf_k`/`max_chunks_per_doc`/`τ`/`top_in`/`top_out` đều đọc từ `get_settings()` — xác nhận trong `qa/service.py::stream_answer`, không hard-code

### Ghi chú triển khai thực tế

Phần lớn T-401 **đã được làm sẵn khi triển khai T-302** (code không tách
rời "chỉ vector" rồi "thêm FTS" theo đúng trình tự 2 task — `retrieve()` đã
làm FTS+RRF+đa dạng hoá ngay từ đầu).

**Đã sửa/thêm (phiên này):**
1. Lỗi logic cổng bằng chứng `τ` ghi ở T-302 đã được sửa — xem ghi chú ở
   đó; T-401 kế thừa trực tiếp bản sửa này.
2. Thêm bước **rerank cross-encoder** đúng §5 bước 3-5: `app/ports/
   reranker_port.py` (`RerankerPort`, Protocol — `modules.retrieval` chỉ
   biết interface này, không biết TEI), `app/adapters/tei_reranker.py`
   (`TeiRerankerAdapter`, gọi `POST {tei_rerank_url}/rerank`, khôi phục
   đúng thứ tự đầu vào từ `index` trong phản hồi TEI). `retrieve()` nhận
   thêm tham số `reranker: RerankerPort | None` — khi có, lấy top-20 ứng
   viên sau RRF, gọi rerank, **cổng bằng chứng áp lên điểm rerank cao
   nhất** thay vì cosine thô (đúng §5 bước 5); khi reranker ném lỗi hoặc
   không được cấu hình (`None`), quay về hành vi RRF+cosine-gate của
   T-302 — không làm hỏng câu trả lời (đúng §6).
3. `api/deps.py::get_reranker_port()` chọn adapter theo `settings.
   llm_provider` (cùng cờ `"fake"` dùng cho `get_llm_port()`): môi trường
   dev/test trả `None` (bỏ qua rerank), môi trường thật trả
   `TeiRerankerAdapter()` — `modules.qa`/`modules.retrieval` không tự
   chọn adapter (nguyên tắc P-01), tiêm qua `conversations.py`.
4. Thêm `settings.tei_rerank_url` (instance TEI riêng cho model
   cross-encoder, khác `tei_embed_url`).

Xác nhận bằng `ruff check .`, `mypy app`, `lint-imports` (3 hợp đồng vẫn
giữ) và 11 test mới (`tests/unit/test_retrieval_service.py`: 3 test
rerank mới + 5 test gate cũ; `tests/unit/test_tei_reranker.py`: 3 test
cho việc khôi phục thứ tự/báo lỗi của adapter) — `pytest` 121 passed.

**Chưa làm:** chưa chạy với TEI reranker thật (không có hạ tầng trong
sandbox); span OTel `retrieval.fts`/`retrieval.rerank` thủ công; test
Postgres thật cho AC-012.1 (đáp án rải 2 tài liệu) và AC-012.2 (mâu
thuẫn) — cần LLM thật để đánh giá nội dung câu trả lời, không chỉ cấu
trúc dữ liệu.

## 9. Tham chiếu

- [SADD §2.2.3 — Pipeline hỏi đáp](../../requirements/SADD.md) · ADR-05 (truy xuất), §4.3 (quan sát)
- [User Stories — US-012, US-014](../../design/User_Stories.md)
- [SDD UI/UX §3.4.2 — IR-01 – IR-03](../../design/SDD_UI_UX_Blueprint.md)
- Ảnh thiết kế: [`SCR-02_15_answer-multi-source.png`](../../design/html_design/SCR-02_15_answer-multi-source.png)
- [implement_plan.md §5 Sprint 4](../implement_plan.md)
