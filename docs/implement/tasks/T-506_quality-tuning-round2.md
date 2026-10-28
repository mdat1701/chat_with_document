# T-506 — Hiệu chỉnh chất lượng vòng 2 (có điều kiện)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | Hỗ trợ US-011, US-012, US-013, US-014, US-017 |
| Epic | EP-03, EP-04 |
| Module (SADD §2.2.1) | `retrieval`, `qa`, `ingestion` |
| API liên quan | API-09 |
| Vai trò chính | AI (chủ trì) · BE (trích xuất PDF) · BA + PM (quyết định ngưỡng) |
| Ước lượng | 2d |
| Phụ thuộc | T-501, T-502 (chỉ chạy khi T-502 **chưa** đạt ngưỡng G-02) |
| Trạng thái | To do (có điều kiện) |

## 1. Mục tiêu

Vòng hiệu chỉnh thứ hai, **chỉ kích hoạt nếu sau T-502 chất lượng vẫn chưa đạt ngưỡng G-02**. Khác với T-502 (chủ yếu xoay quanh tham số truy xuất), vòng 2 tập trung vào **nguyên nhân gốc còn lại** — thường nằm ở khâu trích xuất/chia đoạn hoặc ở prompt — và kết thúc bằng một quyết định rõ ràng: đạt ngưỡng, hạ ngưỡng chấp nhận, hoặc lùi mốc.

Nguyên tắc: nếu T-502 đã đạt, **không chạy task này** — trả lại 2 ngày công cho việc khắc phục lỗi hoặc dự phòng UAT.

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-02 | Bộ câu hỏi chuẩn đạt ngưỡng do BA Lead + PM chấp nhận; **mọi câu trả lời có nội dung đều có căn cứ** |
| KR2.2 | `not_found_recall` vẫn giữ 100% sau mọi thay đổi |
| KR2.3 | `uncited_rate` vẫn giữ 0 |
| AC-012.1 | Câu trả lời tổng hợp trích dẫn đủ các tài liệu liên quan |
| AC-014.3 | Thẻ nguồn trỏ đúng tệp và trang thực sự chứa thông tin |
| R-04 (AR-04) | Tài liệu có bảng biểu không còn gây sai số liệu một cách hệ thống |

## 3. Hợp đồng / kịch bản cụ thể

Phân loại lỗi còn lại từ báo cáo T-501 → hướng xử lý tương ứng:

| Nhóm lỗi quan sát được | Giả thuyết nguyên nhân | Hướng xử lý ở vòng 2 |
|---|---|---|
| Sai số liệu trong tài liệu có **bảng** | PyMuPDF đọc bảng sai thứ tự cột/hàng (AR-04) | Bổ sung `pdfplumber` cho trang chứa bảng, hoặc giữ cấu trúc bảng dạng markdown khi trích xuất |
| Trích dẫn đúng tệp nhưng **sai trang** | Ranh giới đoạn cắt ngang trang, `page_start/page_end` chưa chuẩn | Rà soát lại logic gán trang ở T-202; ưu tiên không cắt đoạn qua trang khi có thể |
| Thiếu **tài liệu thứ hai** trong câu trả lời tổng hợp | Rerank dồn hết suất cho một tài liệu | Giảm `RERANK_MAX_CHUNKS_PER_DOC`, hoặc đảm bảo tối thiểu 1 suất cho tài liệu xếp hạng 2 |
| Câu trả lời **lan man / không bám nguồn** | Prompt chưa đủ ràng buộc | Nâng `prompt_version` v1 → v1.1: siết yêu cầu mỗi khẳng định phải gắn `[S#]` |
| Hỏi **tiếng Việt không dấu** không ra kết quả | Nhánh FTS `unaccent` chưa phát huy (AR-02) | Kiểm tra lại truy vấn `unaccent`, trọng số RRF giữa vector và FTS |

Quy trình chạy mỗi thay đổi (bắt buộc đo lại, không sửa "theo cảm giác"):

```bash
# 1. Áp dụng đúng MỘT thay đổi
# 2. Re-ingest nếu thay đổi chạm tới trích xuất/chia đoạn
python -m tools.evaluation.reingest_corpus --corpus datasets/corpus
# 3. Đo lại toàn bộ
python -m tools.evaluation.run_eval --datasets datasets/golden_set.yaml \
    datasets/no_answer_set.yaml --out reports/r2_<thay-doi>.json
# 4. So với baseline; giữ lại nếu cải thiện, loại bỏ nếu không
python -m tools.evaluation.compare reports/baseline.json reports/r2_<thay-doi>.json
```

## 4. Thay đổi dữ liệu

- Thay đổi logic trích xuất/chia đoạn ⇒ **re-ingest toàn bộ corpus kiểm thử** (ghi đè `chunk`, idempotent theo `document_id` — P-07).
- Nếu đổi prompt: tăng `prompt_version` (ví dụ `v1` → `v1.1`) và ghi vào mọi bản ghi `answer` cùng báo cáo đánh giá, để so sánh được về sau.
- Nếu bổ sung `pdfplumber`: thêm phụ thuộc vào `backend` và cập nhật bảng công nghệ ở SADD Phụ lục A.

## 5. Các bước triển khai

1. **Cổng vào:** xác nhận T-502 đã kết thúc mà chưa đạt ngưỡng. Nếu đã đạt → đóng task, ghi lý do.
2. Lấy danh sách lỗi còn lại từ T-501, phân loại theo bảng ở §3, xếp theo **tần suất** — xử lý nhóm lớn nhất trước.
3. Áp dụng **từng thay đổi một**, đo lại sau mỗi lần (không gộp nhiều thay đổi rồi mới đo — sẽ không biết cái nào có tác dụng).
4. Với lỗi bảng biểu: thử `pdfplumber` chỉ cho trang được phát hiện có bảng, giữ PyMuPDF cho phần còn lại để không làm chậm toàn bộ pipeline.
5. Với lỗi prompt: chỉ sửa ràng buộc trích dẫn và cách nêu phần không tìm thấy; **không** nới lỏng quy tắc "không có bằng chứng thì không khẳng định" (P-04).
6. Sau mỗi thay đổi được giữ lại, kiểm tra **không gây hồi quy**: `not_found_recall` vẫn 100%, `uncited_rate` vẫn 0, độ trễ p90 vẫn trong ngân sách (đối chiếu T-505).
7. Cập nhật nhật ký hiệu chỉnh và `reports/baseline.json`.
8. **Điểm quyết định:** nếu sau vòng 2 vẫn chưa đạt, trình BA Lead + PM (người ký G-02) ba phương án: (a) chấp nhận ngưỡng thấp hơn cho pilot kèm cảnh báo rõ trong UAT, (b) lùi mốc để làm vòng 3, (c) thu hẹp loại tài liệu được phép tải lên trong pilot (ví dụ loại tài liệu nhiều bảng).

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| Hiệu chỉnh vô tận, không có điểm dừng | Task có hộp thời gian cứng 2 ngày; hết hạn phải leo thang theo bước 8 |
| Sửa lỗi nhóm này làm hỏng nhóm khác | Luôn chạy **toàn bộ** bộ câu hỏi sau mỗi thay đổi, không chỉ các câu đang sửa |
| `pdfplumber` làm chậm ingestion đáng kể | Chỉ áp dụng cho trang có bảng; đo lại AC-003.3 (≤ 60 giây/20 trang) sau khi thêm |
| Overfit vào bộ câu hỏi chuẩn | Giữ nguyên tập kiểm chứng riêng từ T-502, không dùng để dò tham số |
| R-07 — hết thời gian trước UAT | Ưu tiên giữ KR2.2 (không bịa) hơn là tăng tỷ lệ trả lời đúng; thà `not_found` còn hơn sai |

## 7. Kiểm thử bắt buộc

- [ ] Sau mỗi thay đổi được giữ lại: chạy đủ bộ T-501, không có chỉ số nào xấu đi
- [ ] `not_found_recall = 1.0` và `uncited_rate = 0` được giữ nguyên
- [ ] Nếu thêm `pdfplumber`: đo lại thời gian ingestion PDF 20 trang vẫn ≤ 60 giây
- [ ] Nếu nâng `prompt_version`: mọi bản ghi `answer` mới ghi đúng phiên bản prompt
- [ ] Chạy lại tập kiểm chứng riêng để xác nhận không overfit

## 8. Định nghĩa Hoàn thành

- [ ] Đạt một trong ba kết cục rõ ràng: (a) đạt ngưỡng G-02, (b) ngưỡng điều chỉnh được PM + BA chấp nhận bằng văn bản, (c) quyết định lùi mốc có người chịu trách nhiệm và ngày mới
- [ ] Nhật ký hiệu chỉnh vòng 2 đầy đủ: thay đổi nào được giữ, thay đổi nào bị loại và vì sao
- [ ] `reports/baseline.json` cập nhật; tham số cuối cùng nằm trong ConfigMap
- [ ] Mọi rủi ro còn lại về chất lượng được ghi vào hồ sơ UAT để người đánh giá biết trước
- [ ] Không còn thay đổi chất lượng nào chưa được đo lường bằng T-501

### Ghi chú triển khai thực tế

Khung ghi log (`docs/pilot/QUALITY_TUNING_R2.md`) đã có, đúng tinh thần
trung thực ("Pending staging evaluation" ở mọi cột, không số liệu giả).
Chưa thể bắt đầu vì phụ thuộc T-501/T-502 chưa có số liệu.

## 9. Tham chiếu

- [SADD §2.2.2 (trích xuất, chia đoạn), §2.2.3 (rerank, prompt), §6.1 AR-02/AR-03/AR-04, nguyên tắc P-04/P-07](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-02](../../requirements/PRD.md)
- [User Stories — US-012, US-013, US-014, US-017](../../design/User_Stories.md)
- [T-501](T-501_rag-evaluation-harness.md) · [T-502](T-502_quality-tuning-round1.md) · [T-505](T-505_performance-smoke-test.md)
- [implement_plan.md §5 Sprint 5, §7 R-02/R-03/R-04/R-07](../implement_plan.md)
