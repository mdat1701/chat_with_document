# T-602 — Phân loại và khắc phục lỗi phát hiện trong UAT

| Thuộc tính | Giá trị |
|---|---|
| Sprint | UAT & Pilot Gate |
| Story | Bảo vệ toàn bộ 19 story P0/P1 |
| Epic | Tất cả |
| Module (SADD §2.2.1) | Tùy lỗi — có thể chạm mọi module |
| API liên quan | Tùy lỗi |
| Vai trò chính | Toàn đội (TL điều phối), QA xác minh lại |
| Ước lượng | **Dự phòng** — giữ ~30% năng lực đội trong tuần UAT, không lập kế hoạch task khác chen vào |
| Phụ thuộc | T-601 (nguồn lỗi), T-504 (bộ E2E để chạy hồi quy) |
| Trạng thái | To do (quy trình triage đã viết, chờ T-601 có lỗi thật) |

## 1. Mục tiêu

Phân loại, xử lý và xác minh lại các lỗi phát hiện trong UAT, sao cho khi trình Pilot Gate (T-603) **không còn lỗi Blocker**, và các lỗi còn lại nằm trong nhóm được phép tồn tại theo PRD §5.1.

Nguyên tắc: **ưu tiên theo tác động tới gate**, không theo thứ tự lỗi được báo.

## 2. Tiêu chí phân loại (kiểm chứng được)

| Mức | Định nghĩa | Ví dụ | Xử lý |
|---|---|---|---|
| **Blocker** | Chặn luồng cốt lõi, hoặc vi phạm cô lập dữ liệu / trích dẫn / xóa dữ liệu | Người dùng A thấy tài liệu của B; câu trả lời có nội dung nhưng **không** có trích dẫn nào; xóa xong vẫn truy vấn được; không tải lên được PDF hợp lệ | **Bắt buộc vá trước pilot** |
| **Major** | Ảnh hưởng đáng kể trải nghiệm nhưng có đường vòng | Trạng thái tài liệu cập nhật chậm > 5 giây; thông báo lỗi khó hiểu; ngăn trượt tablet kẹt focus | Vá nếu kịp; nếu không, cần PM + Chủ sở hữu nghiệp vụ chấp nhận có điều kiện |
| **Minor** | Lỗi giao diện nhỏ, không ảnh hưởng chức năng | Lệch khoảng cách, chữ hoa/thường, tooltip thiếu | **Được phép tồn tại khi ra mắt** (PRD §5.1) |
| **Đề xuất** | Mong muốn tính năng mới | "Muốn có nút 👍", "muốn hỏi tiếp nối" | Đưa **backlog** (US-016/US-018…), **không** mở rộng phạm vi pilot |

> Chiếu theo PRD §5.1: *"lỗi Minor về giao diện và các story P1/P2 chưa hoàn thành được phép tồn tại, miễn là không ảnh hưởng tới cô lập dữ liệu, nguồn trích dẫn, xóa dữ liệu hoặc luồng upload → hỏi."*

## 3. Quy trình xử lý

```
Lỗi được báo (UAT)
   → QA tái hiện  ──không tái hiện──►  ghi "không tái hiện được" + đóng (kèm log/trace_id)
   → phân loại Blocker / Major / Minor / Đề xuất
   → gán owner theo module (SADD §2.2.1)
   → sửa trên nhánh riêng + bổ sung ca kiểm thử hồi quy
   → CI xanh (unit + E2E + kiểm thử cô lập)
   → triển khai staging
   → QA xác minh lại + người báo lỗi xác nhận
   → đóng
```

Mỗi lỗi ghi tối thiểu: bước tái hiện, kết quả mong đợi, kết quả thực tế, `trace_id` (lấy từ thông báo lỗi — SADD §4.3), ảnh chụp màn hình, mức phân loại, gate bị ảnh hưởng.

## 4. Thay đổi dữ liệu

Không có thay đổi schema theo kế hoạch. Nếu một lỗi Blocker buộc phải đổi schema, áp dụng đúng quy ước **expand → migrate → contract** (SADD §4.4), không đổi tên/xóa cột trong cùng bản phát hành.

## 5. Các bước triển khai

1. **Triage hằng ngày (15 phút/ngày trong tuần UAT):** TL + QA + PM duyệt lỗi mới, phân loại, gán owner. Không để lỗi nằm chờ quá 1 ngày chưa phân loại.
2. **Ưu tiên:** Blocker → Major ảnh hưởng gate G-01/G-03/G-04/G-05 → Major khác → Minor (chỉ làm nếu còn thời gian).
3. **Mỗi lần sửa phải kèm ca kiểm thử hồi quy** ở mức phù hợp (unit hoặc E2E) — không vá "trần" để tránh lỗi quay lại.
4. **Không gộp** nhiều lỗi không liên quan vào một PR; giữ PR nhỏ để review nhanh trong tuần UAT.
5. **Chạy lại toàn bộ bộ E2E + kiểm thử cô lập (T-504)** sau mỗi lần triển khai staging, không chỉ chạy test của lỗi vừa sửa.
6. **Với lỗi chất lượng câu trả lời** (sai, thiếu căn cứ): **không** vá bằng cách sửa prompt vội vàng; chuyển thành ca kiểm thử bổ sung cho bộ câu hỏi chuẩn và xử lý qua vòng hiệu chỉnh (T-502/T-506), tránh làm giảm chỉ số đã đạt.
7. **Lỗi quyền riêng tư** (bất kỳ dấu hiệu nội dung lọt vào log/analytics): coi là **Blocker tuyệt đối**, dừng pilot cho tới khi canary test (T-404) xanh trở lại.
8. Cập nhật trạng thái lỗi vào hồ sơ Pilot Gate để T-603 tổng hợp.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Lỗi không tái hiện được | Đóng với lý do rõ ràng, **đính kèm `trace_id`** và khoảng thời gian để tra cứu lại nếu tái phát |
| Lỗi do dữ liệu người dùng (PDF scan, PDF hỏng) | Không phải lỗi hệ thống nếu đã hiển thị đúng mã lỗi `PDF_NO_TEXT`/`PDF_CORRUPTED`; nếu thông báo khó hiểu thì phân loại **Major** về nội dung thông báo |
| Lỗi chỉ xuất hiện trên một trình duyệt | Vẫn tính trong phạm vi nếu thuộc Chrome/Edge/Firefox (2 phiên bản mới nhất); ngoài danh sách này thì ghi nhận, không chặn |
| Hết tuần UAT vẫn còn Blocker | **Hoãn pilot** — không ký G-07; lên lịch vá và chạy lại phần UAT liên quan |
| Người báo lỗi không xác nhận lại được (bận) | QA xác minh thay, ghi rõ trong hồ sơ ai là người xác minh |
| Sửa lỗi làm hỏng chỗ khác | Bộ E2E đầy đủ phải phát hiện trước khi đóng; nếu lọt, bổ sung ngay ca kiểm thử còn thiếu |

## 7. Kiểm thử bắt buộc

- [ ] Mỗi lỗi Blocker/Major đã sửa có **ít nhất 1 ca kiểm thử tự động** gắn với nó
- [ ] Bộ E2E luồng chính chạy xanh trên bản triển khai staging cuối cùng
- [ ] Kiểm thử cô lập dữ liệu 2 người dùng (T-504) chạy xanh sau tất cả bản vá
- [ ] Canary test quyền riêng tư (T-404) chạy xanh sau tất cả bản vá
- [ ] Người báo lỗi (hoặc QA thay thế) xác nhận lại trên staging đối với mọi lỗi Blocker

## 8. Định nghĩa Hoàn thành

- [ ] **0 lỗi Blocker** đang mở
- [ ] Mọi lỗi Major còn lại có quyết định rõ ràng: đã vá, hoặc được PM + Chủ sở hữu nghiệp vụ chấp nhận có điều kiện (ghi trong hồ sơ)
- [ ] Lỗi Minor còn lại được liệt kê thành danh sách "chấp nhận khi ra mắt" đính kèm T-603
- [ ] Đề xuất tính năng đã chuyển backlog, **không** có tính năng post-MVP nào bị lén đưa vào pilot
- [ ] Bảng theo dõi lỗi được chốt và đính kèm hồ sơ Pilot Gate

### Ghi chú triển khai thực tế

`docs/pilot/T602_TRIAGE.md` (quy trình 6 bước) và `docs/pilot/UAT_DEFECT_LOG.md`
(bảng log với 1 dòng mẫu `UAT-001` trống) đã có sẵn, định nghĩa rõ "Blocker"
gồm rò rỉ dữ liệu chéo owner, trích dẫn sai, xóa không thành công, luồng
upload→hỏi đáp hỏng — khớp đúng các phát hiện thật đã ghi ở T-302/T-303/
T-301 trong phiên rà soát này (cổng bằng chứng yếu, thiếu phân loại lỗi
LLM). Chưa thể xử lý lỗi UAT vì chưa có UAT thật (T-601 chưa chạy).

## 9. Tham chiếu

- [PRD §5.1 — Pilot Gate và "vấn đề được phép tồn tại khi ra mắt"](../../requirements/PRD.md)
- [SADD §4.3 (trace_id trong lỗi), §4.4 (quy ước migration)](../../requirements/SADD.md)
- [SDD UI/UX §3.4.3 — danh mục mã lỗi hiển thị](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 UAT, §7 Rủi ro, §8](../implement_plan.md)
