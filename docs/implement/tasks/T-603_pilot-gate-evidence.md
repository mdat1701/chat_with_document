# T-603 — Tổng hợp bằng chứng và trình ký Pilot Gate

| Thuộc tính | Giá trị |
|---|---|
| Sprint | UAT & Pilot Gate |
| Story | Điều kiện phát hành cho toàn bộ 19 story P0/P1 |
| Epic | Tất cả |
| Module (SADD §2.2.1) | Không sửa code |
| API liên quan | Không |
| Vai trò chính | TL (chủ trì hồ sơ) + QA + PM/BA + ATTT + Chủ sở hữu nghiệp vụ |
| Ước lượng | 2 ngày công |
| Phụ thuộc | T-404, T-501 – T-506, T-601, T-602 |
| Trạng thái | To do (khung hồ sơ 6 gate đã có, toàn bộ ở trạng thái Pending) |

## 1. Mục tiêu

Thu thập đủ bằng chứng cho **7 cổng Pilot Gate** của PRD v0.2 §5.1, trình đúng người ký, và chốt danh sách vấn đề được phép tồn tại khi mở pilot.

> **Lưu ý về số hiệu gate (CL-01):** PRD v0.2 §5.1 chỉ định nghĩa **G-01 – G-07**. SADD và User Stories v0.4 còn sót tham chiếu tới `G-08`, `G-10`, `G-13` từ phiên bản cũ. Hồ sơ này dùng **PRD v0.2 làm chuẩn**; khi gặp mã cũ trong tài liệu khác, ánh xạ về gate tương ứng (ví dụ "retention G-08" → **G-05**).

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Nội dung |
|---|---|
| G-01 – G-07 | Toàn bộ 7 cổng có bằng chứng đầy đủ và chữ ký của đúng người chịu trách nhiệm |
| PRD §5.1 | Vấn đề còn lại chỉ thuộc nhóm được phép tồn tại khi ra mắt |

## 3. Bảng bằng chứng Pilot Gate (PRD v0.2 §5.1)

| Gate | Nhóm | Tiêu chí | Bằng chứng phải nộp | Nguồn (task) | Người ký |
|---|---|---|---|---|---|
| **G-01** | Luồng cốt lõi | Upload PDF → xử lý → hỏi → câu trả lời có nguồn hoặc `not_found` chạy end-to-end | Báo cáo chạy bộ E2E (xanh) + bản ghi demo luồng chính | T-504, T-601 | **QA Lead** |
| **G-02** | Chất lượng | Bộ câu hỏi chuẩn nhỏ chạy được offline; mọi câu trả lời **có căn cứ hoặc `not_found`**; ngưỡng chính thức chốt sau baseline | Phiếu đánh giá bộ câu hỏi chuẩn: tỷ lệ đúng, tỷ lệ `not_found` đúng, tách theo ngôn ngữ (AC-017.3) | T-501, T-502, T-506 | **BA Lead + PM** |
| **G-03** | Cô lập dữ liệu | Người dùng không thể xem hoặc truy vấn tài liệu của người khác | Kết quả integration test 2 người dùng chạy trong CI + xác nhận từ UAT | T-104, T-504 | **QA Lead + ATTT** |
| **G-04** | Quyền riêng tư và AI | Luồng xử lý AI, nơi lưu trữ và dữ liệu thử nghiệm được ATTT phê duyệt; log/analytics **không chứa nội dung** | Biên bản rà soát của ATTT + kết quả **canary test** (chuỗi canary không xuất hiện trong analytics/log/metric) | T-301 (D-01), T-404, T-503 | **ATTT** |
| **G-05** | Xóa và retention | Xóa thủ công và dọn dẹp hết hạn không còn cho phép truy xuất tài liệu | Integration test xóa + test retention với `retention_days` rút ngắn trên staging | T-206, T-207 | **QA Lead** |
| **G-06** | Hiệu năng tối thiểu | Tài liệu mẫu và câu hỏi mẫu hoàn thành trong giới hạn DF-03/DF-10 ở quy mô pilot | Báo cáo smoke/performance test (p90 thời gian trả lời, thời gian xử lý PDF 20 trang) | T-505 | **Tech Lead** |
| **G-07** | UAT | Nhóm người dùng thử nghiệm hoàn thành luồng chính, **không còn lỗi chặn** | Biên bản UAT có chữ ký + bảng lỗi đã đóng | T-601, T-602 | **Chủ sở hữu nghiệp vụ** |

## 4. Thay đổi dữ liệu

Không có. Task này chỉ tạo hồ sơ (tài liệu, báo cáo, biên bản) lưu cùng kho tài liệu dự án.

## 5. Các bước triển khai

1. **Dựng khung hồ sơ:** tạo một thư mục/trang hồ sơ Pilot Gate với 7 mục tương ứng 7 gate, mỗi mục có: tiêu chí, bằng chứng đính kèm, kết luận đạt/chưa đạt, người ký, ngày ký.
2. **Thu bằng chứng tự động:** xuất kết quả CI mới nhất (E2E, kiểm thử cô lập, canary test quyền riêng tư) kèm **số hiệu build và commit hash** để truy vết được.
3. **Thu bằng chứng thủ công:** phiếu đánh giá chất lượng (T-501), báo cáo hiệu năng (T-505), biên bản UAT (T-601), biên bản rà soát ATTT (T-503).
4. **Rà soát chéo với trạng thái quyết định mở:** xác nhận D-01 (phương án LLM) đã chốt — nếu chưa, **G-04 không thể ký**; ghi rõ trạng thái D-04 (cửa sổ backup 7 ngày) vì ảnh hưởng G-05.
5. **Chốt danh sách vấn đề được phép tồn tại** và đính kèm hồ sơ:
   - Lỗi **Minor** về giao diện còn mở (từ T-602).
   - Story **P1/P2 chưa hoàn thành** — nêu đích danh: US-016 (hỏi tiếp nối), US-018 (feedback), US-019 (báo cáo tuần), US-022 (chấm điểm), màn hình quản trị của US-023; và bất kỳ P1 nào bị cắt (US-009/US-010/US-015 nếu có).
   - Khẳng định các mục trên **không** ảnh hưởng tới: cô lập dữ liệu, nguồn trích dẫn, xóa dữ liệu, luồng upload → hỏi.
6. **Họp ký duyệt:** trình từng gate cho đúng người ký ở §3; ghi lại ý kiến phản đối (nếu có) và điều kiện kèm theo.
7. **Kết luận:** ra quyết định **mở pilot / hoãn pilot**. Nếu hoãn, nêu rõ gate nào chưa đạt, việc cần làm và ngày trình lại.
8. **Bàn giao:** chuyển hồ sơ cho T-604 (runbook) và lưu trữ làm đầu vào cho quyết định đầu tư mở rộng (BRD BO-003).

## 6. Trường hợp biên

| Tình huống | Xử lý |
|---|---|
| D-01 (phương án LLM) **chưa chốt** | **Không ký được G-04** → hoãn pilot. Đây là rủi ro R-01 đã dự báo; không có đường vòng |
| ATTT chỉ phê duyệt **có điều kiện** (ví dụ chỉ dùng tài liệu không nhạy cảm) | Ghi điều kiện vào hồ sơ G-04 và vào runbook T-604; thông báo rõ cho người dùng pilot |
| G-02 chưa đạt ngưỡng kỳ vọng nhưng mọi câu trả lời **đều có căn cứ hoặc `not_found`** | Vẫn có thể ký theo đúng lời văn PRD v0.2 (ngưỡng chính thức chốt **sau** baseline); PM ghi rõ số liệu thực tế làm baseline |
| Còn lỗi Major chưa vá | Chỉ ký khi PM + Chủ sở hữu nghiệp vụ chấp nhận có điều kiện bằng văn bản |
| Gặp mã gate cũ (G-08/G-10/G-13) trong tài liệu đầu vào | Ánh xạ về G-01 – G-07 theo PRD v0.2; ghi chú lại để đợt rà soát tài liệu sau sửa dứt điểm (CL-01) |
| Một người ký vắng mặt | Chấp nhận ủy quyền bằng văn bản; **không** bỏ qua chữ ký của ATTT ở G-04 |

## 7. Kiểm thử bắt buộc

- [ ] Mỗi gate trong §3 có **ít nhất một** bằng chứng cụ thể, truy vết được tới build/commit hoặc biên bản
- [ ] Kết quả CI đính kèm là bản chạy **mới nhất** trên commit sẽ triển khai pilot (không dùng kết quả cũ)
- [ ] Canary test quyền riêng tư (T-404) xanh trên chính bản build đó
- [ ] Bộ E2E + kiểm thử cô lập xanh trên chính bản build đó
- [ ] Danh sách "vấn đề được phép tồn tại" được đối chiếu với tiêu chí PRD §5.1, không chứa mục nào vi phạm 4 lĩnh vực cấm

## 8. Định nghĩa Hoàn thành

- [ ] 7/7 gate có kết luận và chữ ký (hoặc quyết định hoãn pilot với lý do rõ ràng)
- [ ] Hồ sơ Pilot Gate được lưu trữ ở nơi cả PM, ATTT và đội kỹ thuật truy cập được
- [ ] Danh sách story post-MVP chưa làm được nêu công khai trong hồ sơ, tránh hiểu nhầm phạm vi
- [ ] Quyết định mở/hoãn pilot được truyền đạt tới nhóm người dùng thử nghiệm
- [ ] Số liệu MET-003, MET-004 và baseline chất lượng được ghi lại phục vụ BRD BO-003

### Ghi chú triển khai thực tế

`docs/pilot/PILOT_GATE_EVIDENCE.md` đã có đủ khung cho cả 7 gate (G-01→G-07),
mỗi dòng ghi đúng nguồn bằng chứng sẽ cần (báo cáo T-504/T-501/canary/k6/
UAT) và người ký tương ứng, tất cả ở trạng thái "Pending" — không có kết
luận giả. Dựa trên các phát hiện thật trong phiên rà soát này, các gate
sau **chưa đủ điều kiện kết luận "Đạt" khi đến lượt**: G-02 (T-501 chưa có
số liệu), G-03 (test cô lập chỉ mới viết, chưa chạy thật — xem T-504),
G-06 (k6 chưa chạy). Giữ "To do".

## 9. Tham chiếu

- [PRD §5.1 — Tiêu chí Pilot Gate G-01 – G-07](../../requirements/PRD.md)
- [SADD §5.1 — Ma trận yêu cầu → thành phần → xác minh; §6 rủi ro/vấn đề mở](../../requirements/SADD.md)
- [User Stories v0.4 — phạm vi 19 story và các story post-MVP](../../design/User_Stories.md)
- [BRD §5.4 (hoãn sau MVP-lite), BO-003](../../requirements/BRD.md)
- [implement_plan.md §8.1 (ánh xạ gate), §9 CL-01](../implement_plan.md)
