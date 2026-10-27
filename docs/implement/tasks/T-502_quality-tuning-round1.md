# T-502 — Hiệu chỉnh chất lượng vòng 1 (τ, chia đoạn, rerank)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | Hỗ trợ US-011, US-012, US-013, US-017 |
| Epic | EP-03, EP-04 |
| Module (SADD §2.2.1) | `retrieval`, `qa`, `ingestion` (tham số chia đoạn) |
| API liên quan | API-09 (hành vi đầu ra), API-02 `/config` (phát tham số nếu cần) |
| Vai trò chính | AI (chủ trì) · BE (đổi tham số, re-ingest) · BA (chấm lại mẫu) |
| Ước lượng | 3d |
| Phụ thuộc | T-501 (phải có báo cáo baseline), T-302, T-303, T-202 |
| Trạng thái | To do |

## 1. Mục tiêu

Dựa trên số liệu của T-501, hiệu chỉnh các tham số chi phối chất lượng câu trả lời để đạt đồng thời hai điều kiện của **G-02**: không bịa (mọi câu có nội dung đều có căn cứ) và không "không tìm thấy" sai. Trọng tâm là **ngưỡng cổng bằng chứng τ** — tham số rủi ro nhất của hệ thống (AR-03 / R-03).

Nguyên tắc bắt buộc: **mọi tham số hiệu chỉnh phải đọc từ cấu hình** (nguyên tắc P-06 của SADD), không hard-code trong mã nguồn — để đổi giá trị không cần build lại.

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-02 | Sau hiệu chỉnh, bộ câu hỏi chuẩn đạt: mọi câu trả lời có nội dung đều có căn cứ, hoặc hệ thống trả `not_found` |
| KR2.2 | `not_found_recall = 100%` trên tập ≥ 10 câu không có đáp án |
| KR2.3 | `uncited_rate = 0` |
| AC-013.3 | Câu hỏi chỉ có **một phần** đáp án trả về `partial`, nêu rõ phần không tìm thấy |
| AC-012.1/012.2 | Câu hỏi cần thông tin ở nhiều tài liệu trích dẫn đủ các tài liệu liên quan |
| AC-017.3 | Chênh lệch tỷ lệ đúng giữa tiếng Việt và tiếng Anh nằm trong mức chấp nhận được |

## 3. Hợp đồng / kịch bản cụ thể

Tập tham số được phép hiệu chỉnh (tất cả nằm trong ConfigMap / biến môi trường):

```
RETRIEVAL_TAU                = 0.15    # ngưỡng cổng bằng chứng (khởi điểm, SADD §2.2.3)
RETRIEVAL_VECTOR_TOP_K       = 40      # ứng viên vector
RETRIEVAL_FTS_TOP_K          = 40      # ứng viên full-text
RETRIEVAL_RRF_K              = 60      # hằng số Reciprocal Rank Fusion
RERANK_TOP_IN                = 20      # số ứng viên đưa vào cross-encoder
RERANK_TOP_OUT               = 8       # số đoạn gửi LLM
RERANK_MAX_CHUNKS_PER_DOC    = 4       # đa dạng nguồn (US-012)
CHUNK_SIZE_TOKENS            = 500     # yêu cầu re-ingest khi đổi
CHUNK_OVERLAP_TOKENS         = 50      # yêu cầu re-ingest khi đổi
```

Kịch bản quét τ (chạy lại T-501 cho từng giá trị):

```bash
for TAU in 0.05 0.10 0.15 0.20 0.25 0.30; do
  RETRIEVAL_TAU=$TAU python -m tools.evaluation.run_eval \
     --datasets datasets/golden_set.yaml datasets/no_answer_set.yaml \
     --reuse-corpus --out reports/sweep_tau_$TAU.json
done
python -m tools.evaluation.plot_curve reports/sweep_tau_*.json --out reports/tau_curve.html
```

Đường cong cần vẽ: trục X là τ, hai đường — `false_not_found_rate` (tăng theo τ) và `uncited_rate` + tỷ lệ trả lời không có căn cứ (giảm theo τ). **Điểm chọn:** τ nhỏ nhất mà vẫn giữ `not_found_recall = 100%`, đồng thời `grounded_accuracy` cao nhất.

## 4. Thay đổi dữ liệu

- Đổi `CHUNK_SIZE_TOKENS`/`CHUNK_OVERLAP_TOKENS` **bắt buộc re-ingest toàn bộ corpus kiểm thử** (chia lại đoạn + embedding lại). Lên lịch chạy ngoài giờ, tính cả thời gian TEI.
- Không thay đổi lược đồ CSDL. `chunk.embedding` bị ghi đè khi re-ingest (idempotent theo `document_id`, nguyên tắc P-07).
- Giá trị tham số cuối cùng được ghi vào ConfigMap của `staging` và `prod`, đồng thời cập nhật lại số liệu ví dụ trong SADD §2.2.3 nếu lệch đáng kể.

## 5. Các bước triển khai

1. Đọc báo cáo baseline từ T-501, xác định nhóm lỗi chiếm tỷ trọng lớn nhất (không tìm thấy sai / trích dẫn sai trang / thiếu tài liệu thứ hai / sai ngôn ngữ).
2. Chạy quét τ theo kịch bản ở §3; vẽ đường cong; chọn τ theo quy tắc "nhỏ nhất mà `not_found_recall` vẫn 100%".
3. Nếu lỗi chủ yếu là **thiếu ngữ cảnh** (câu trả lời cụt, trích dẫn đúng tài liệu nhưng sai đoạn): thử `CHUNK_SIZE_TOKENS` ∈ {300, 500, 800} và overlap ∈ {0, 50}; mỗi lần đổi phải re-ingest rồi chạy lại T-501.
4. Nếu lỗi chủ yếu là **thiếu tài liệu thứ hai** trong câu trả lời tổng hợp (AC-012.1): tăng `RERANK_MAX_CHUNKS_PER_DOC` xuống 3 hoặc tăng `RERANK_TOP_OUT`, cân nhắc đánh đổi với ngân sách token (R-06).
5. Nếu lỗi chủ yếu ở **tiếng Việt không dấu / từ ghép** (AR-02 / R-02): kiểm tra nhánh FTS `unaccent` có thực sự được hợp nhất qua RRF không; cân chỉnh trọng số giữa vector và FTS.
6. Sau mỗi thay đổi, chạy lại T-501 và **ghi lại** vào bảng nhật ký hiệu chỉnh: tham số, lý do thử, kết quả 4 chỉ số chính.
7. Chốt bộ tham số; cập nhật ConfigMap; chạy xác nhận cuối cùng; cập nhật `reports/baseline.json`.
8. Ghi tóm tắt quyết định (τ cuối cùng và lý do) vào tài liệu để phục vụ hồ sơ G-02 và cho người sau hiểu vì sao chọn giá trị đó.

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| R-03 — τ quá cao gây `not_found` sai, quá thấp gây bịa | Quyết định bằng đường cong, không bằng cảm tính; ưu tiên tuyệt đối cho KR2.2 = 100% |
| Re-ingest tốn thời gian và chi phí embedding | Giới hạn số lần đổi `CHUNK_SIZE`; chỉ đổi khi dữ liệu cho thấy đó là nguyên nhân chính |
| Hiệu chỉnh quá khớp (overfit) với bộ câu hỏi chuẩn | Giữ lại ~20% câu làm tập kiểm chứng riêng, không dùng khi dò tham số |
| R-04 — PDF bảng biểu trích xuất sai thứ tự | Nếu lỗi tập trung ở tài liệu có bảng, **không** giải bằng τ — ghi nhận và chuyển sang T-506 (cân nhắc `pdfplumber`) |
| Đổi tham số làm tăng độ trễ vượt ngân sách | Đối chiếu với T-505; `RERANK_TOP_OUT` lớn hơn làm tăng token và TTFT |

## 7. Kiểm thử bắt buộc

- [ ] Có file `reports/tau_curve.html` thể hiện rõ cơ sở chọn τ
- [ ] Bộ tham số cuối cùng đạt `not_found_recall = 1.0` và `uncited_rate = 0`
- [ ] `grounded_accuracy` trên tập kiểm chứng riêng (không dùng để dò tham số) không thấp hơn đáng kể so với tập đã dò
- [ ] Đổi tham số qua ConfigMap có hiệu lực **không cần build lại** (xác minh P-06)
- [ ] Độ trễ p90 sau hiệu chỉnh vẫn trong ngân sách (đối chiếu T-505)

## 8. Định nghĩa Hoàn thành

- [ ] Bộ tham số cuối cùng đã nằm trong ConfigMap của `staging` và sẵn sàng cho `prod`
- [ ] Nhật ký hiệu chỉnh (tham số → lý do → kết quả) được lưu cùng báo cáo T-501
- [ ] `reports/baseline.json` được cập nhật và BA + PM xác nhận
- [ ] Không còn giá trị τ / kích thước đoạn / tham số rerank nào hard-code trong mã nguồn
- [ ] Nếu chưa đạt ngưỡng G-02 → mở T-506 kèm danh sách lỗi còn lại đã phân loại

## 9. Tham chiếu

- [SADD §2.2.3 (cổng bằng chứng, rerank, RRF), §6.1 AR-02/AR-03, nguyên tắc P-06](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-02](../../requirements/PRD.md)
- [User Stories — US-012 (AC-012.1/012.2), US-013 (AC-013.3), US-017 (AC-017.3)](../../design/User_Stories.md)
- [implement_plan.md §5 Sprint 5, §7 R-02/R-03, §9 CL-03](../implement_plan.md)
