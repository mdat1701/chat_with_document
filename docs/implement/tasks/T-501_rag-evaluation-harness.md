# T-501 — Bộ đánh giá chất lượng RAG (offline)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | Hỗ trợ kiểm chứng US-011, US-012, US-013, US-014, US-017 (không phải story riêng) |
| Epic | EP-03, EP-04 (kiểm chứng chất lượng) |
| Module (SADD §2.2.1) | `evaluation` — **script/CI tooling chạy ngoài sản phẩm**, không có module/API trong MVP-lite |
| API liên quan | Dùng API-09 như một client (hoặc gọi thẳng use case `qa`) |
| Vai trò chính | AI (chủ trì) · BA (bộ câu hỏi chuẩn) · TL (tích hợp CI) |
| Ước lượng | 3d |
| Phụ thuộc | T-304 (API hỏi đáp SSE), T-302, T-303 · Giả định A-03 (bộ câu hỏi + corpus) · D-01 (LLM) |
| Trạng thái | To do |

## 1. Mục tiêu

Dựng bộ đánh giá chất lượng **chạy ngoài sản phẩm** để trả lời được câu hỏi: *"câu trả lời của hệ thống có căn cứ trong tài liệu không, và khi không có dữ liệu thì hệ thống có nói rõ không?"* Đây là bằng chứng chính cho **Pilot Gate G-02** và là lưới an toàn chống hồi quy chất lượng khi đổi prompt, mô hình hay tham số chia đoạn.

Phạm vi rõ ràng: **không** xây màn hình chấm điểm, **không** thêm API `evaluation` vào sản phẩm (US-022 là post-MVP, SADD §2.2.1 ghi rõ MVP-lite chỉ có script offline).

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-02 | Bộ câu hỏi chuẩn nhỏ chạy được offline; mọi câu trả lời phải **có căn cứ** hoặc trả `not_found`; ngưỡng chính thức chốt sau baseline |
| KR2.2 / AC-013.2 | **100%** câu hỏi trong tập "không có đáp án" (≥ 10 câu) phải trả `not_found` |
| KR2.3 / AC-014.1 | 100% câu trả lời **có nội dung** phải kèm ≥ 1 trích dẫn hợp lệ (tỷ lệ `uncited` = 0) |
| AC-011.2 | Câu hỏi kiến thức chung ("Thủ đô của Pháp là gì?") không được trả lời bằng kiến thức ngoài tài liệu |
| AC-017.3 | Tỷ lệ đúng tính riêng cho từng ngôn ngữ (vi, en) |
| AC-014.3 | Thẻ nguồn trỏ đúng tệp/trang thực sự chứa thông tin |

## 3. Hợp đồng / kịch bản cụ thể

Cấu trúc thư mục (nằm ngoài `backend/app`, không được import vào mã sản phẩm):

```
tools/evaluation/
  datasets/
    golden_set.yaml        # câu CÓ đáp án trong corpus
    no_answer_set.yaml     # ≥10 câu KHÔNG có đáp án (KR2.2)
    corpus/                # PDF kiểm thử được phép dùng (BRD DEP-003)
  run_eval.py
  reports/
    baseline.json          # mốc so sánh cho CI
```

Lệnh chạy:

```bash
python -m tools.evaluation.run_eval \
  --datasets datasets/golden_set.yaml datasets/no_answer_set.yaml \
  --corpus datasets/corpus \
  --base-url https://staging.internal/api/v1 \
  --out reports/2027-01-05.json --html
```

Định dạng bộ câu hỏi:

```yaml
version: 1
items:
  - id: Q-001
    lang: vi
    question: "Thời hạn thanh toán trong hợp đồng với đối tác A là bao lâu?"
    expected_answer_type: answered        # answered | partial | not_found
    expected_facts: ["30 ngày"]
    expected_documents: ["HopDong_DoiTacA.pdf"]
    expected_pages: [12]
  - id: NQ-001
    lang: vi
    question: "Thủ đô của Pháp là gì?"
    expected_answer_type: not_found
```

Báo cáo kết quả (JSON — mỗi lần chạy **bắt buộc** ghi `prompt_version` và `model_id` theo SADD §2.2.3):

```json
{
  "run_id": "2027-01-05T02:10:00Z",
  "prompt_version": "v1", "model_id": "<LLM theo D-01>",
  "embedding_model": "BAAI/bge-m3", "chunk_size_tokens": 500, "tau": 0.15,
  "metrics": {
    "grounded_accuracy": 0.86,
    "not_found_recall": 1.0,
    "false_not_found_rate": 0.07,
    "uncited_rate": 0.0,
    "citation_page_accuracy": 0.91,
    "accuracy_by_lang": { "vi": 0.87, "en": 0.84 },
    "retrieval_top_score": { "p10": 0.11, "p50": 0.34, "p90": 0.62 },
    "latency_ms": { "p50": 6200, "p90": 12800 }
  }
}
```

## 4. Thay đổi dữ liệu

- **Không** tạo bảng mới trong CSDL sản phẩm. Các bảng `EVALUATION_*` trong SADD §3.1.1 thuộc phạm vi post-MVP và **không** được tạo ở MVP-lite.
- Kết quả lưu dạng **artifact** (JSON + HTML) của CI và trong `tools/evaluation/reports/`.
- Corpus kiểm thử nằm trong object storage của môi trường `staging`, tải lên bằng một tài khoản kiểm thử chuyên dụng.

## 5. Các bước triển khai

1. Cùng BA chốt bộ câu hỏi chuẩn: tối thiểu 30 câu có đáp án (phủ cả vi/en, có câu trải nhiều tài liệu cho US-012) và **≥ 10 câu không có đáp án**.
2. Chuẩn bị corpus: chỉ dùng **tài liệu kiểm thử được phép** (BRD DEP-003) — tuyệt đối không dùng tài liệu nghiệp vụ nhạy cảm khi OQ-010/D-01 chưa chốt (ràng buộc CON-004).
3. Viết `run_eval.py`: nạp corpus (gọi API-04 tải lên, chờ `status=ready` qua API-06), sau đó với mỗi câu hỏi gọi API-09 và gom luồng SSE (`meta` → `delta` → `citations` → `done`).
4. Chấm tự động: so `done.type` với `expected_answer_type`; kiểm tra `expected_facts` xuất hiện trong nội dung; so `citations[].document_name`/`page_start..page_end` với `expected_documents`/`expected_pages`.
5. Đánh dấu các mục cần **người chấm** (câu trả lời đúng ý nhưng diễn đạt khác) và xuất file để BA xác nhận — kết quả cuối ghi đè vào báo cáo.
6. Tính và xuất đủ các chỉ số ở §3, kèm biểu đồ phân bố `retrieval_top_score` phục vụ T-502.
7. Chốt `reports/baseline.json` sau lần chạy đầu tiên được BA/PM chấp nhận.
8. Tích hợp CI: chạy **nightly** và chạy bắt buộc khi PR chạm tới prompt, `model_id`, mô hình embedding hoặc tham số chia đoạn/rerank. **Chặn phát hành** nếu `not_found_recall < 1.0`, `uncited_rate > 0`, hoặc `grounded_accuracy` giảm quá biên độ cho phép so với baseline.
9. Ghi log chi phí token mỗi lần chạy để theo dõi R-06.

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| R-07 — bộ câu hỏi/corpus tới muộn (A-03) | Theo dõi từ Sprint 2; nếu trễ, chạy trước với bộ rút gọn (10 câu) để dò lỗi hệ thống, bổ sung sau |
| LLM không tất định dù `temperature=0.1` | Chạy mỗi câu 2 lần, báo cáo cả biên độ; chỉ coi là hồi quy khi vượt biên độ dao động đã đo |
| R-06 — chi phí token khi chạy nightly | Giới hạn số câu chạy nightly; bộ đầy đủ chỉ chạy trước mốc và khi đổi prompt/mô hình |
| Corpus phải tải lại mỗi lần chạy | Hỗ trợ cờ `--reuse-corpus` dùng lại tài liệu đã `ready` để tiết kiệm thời gian/chi phí embedding |
| D-01 chưa chốt | Chạy với phương án A trên corpus không nhạy cảm (A-04); ghi rõ `model_id` để so sánh lại sau khi chốt |

## 7. Kiểm thử bắt buộc

- [ ] Chạy trọn bộ trên `staging`, sinh ra báo cáo JSON + HTML đầy đủ các chỉ số ở §3
- [ ] Tập "không có đáp án" cho `not_found_recall = 1.0` (nếu chưa đạt → chuyển T-502)
- [ ] Câu hỏi kiến thức chung không nhận câu trả lời bịa (AC-011.2)
- [ ] Chạy lại hai lần liên tiếp cho kết quả ổn định trong biên độ đã công bố
- [ ] CI thất bại đúng như thiết kế khi cố tình hạ chất lượng (ví dụ đặt `tau=0.9`)

## 8. Định nghĩa Hoàn thành

- [ ] `run_eval.py` chạy được bằng một lệnh trên máy dev và trong CI
- [ ] `reports/baseline.json` đã được BA + PM xác nhận
- [ ] CI nightly + CI theo thay đổi prompt/mô hình đã bật và chặn được hồi quy
- [ ] Mã nguồn bộ đánh giá **không** nằm trong `backend/app` và không bị import bởi mã sản phẩm (kiểm tra bằng `import-linter`)
- [ ] Không có tài liệu nhạy cảm nào trong corpus; log của bộ đánh giá không chứa nội dung tài liệu (P-03)
- [ ] Báo cáo mới nhất được đính kèm vào hồ sơ bằng chứng Pilot Gate G-02

## 9. Tham chiếu

- [SADD §2.2.1 (module `evaluation`), §2.2.3 (pipeline hỏi đáp), §4.3 (đánh giá chất lượng liên tục)](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-02](../../requirements/PRD.md)
- [User Stories — US-011, US-013, US-014, US-017, US-022 (post-MVP)](../../design/User_Stories.md)
- [implement_plan.md §5 Sprint 5, §8.1](../implement_plan.md)
