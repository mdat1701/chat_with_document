# T-601 — Thực hiện UAT với nhóm người dùng thử nghiệm

| Thuộc tính | Giá trị |
|---|---|
| Sprint | UAT & Pilot Gate |
| Story | Kiểm chứng toàn bộ 19 story P0/P1 |
| Epic | Tất cả (EP-01 – EP-05) |
| Module (SADD §2.2.1) | Không sửa code — kiểm chứng hệ thống đã triển khai trên `staging` |
| API liên quan | Toàn bộ API-01 – API-09 (gián tiếp qua giao diện) |
| Vai trò chính | PM · BA (chính) + QA + Chủ sở hữu nghiệp vụ |
| Ước lượng | 1 tuần (lịch), ~3 ngày công của PM/BA + 1 ngày công QA |
| Phụ thuộc | Toàn bộ Sprint 1 – Sprint 5; T-103 (cấp quyền CLI) để mở tài khoản cho người tham gia |
| Trạng thái | To do |

## 1. Mục tiêu

Để **~12 người dùng thật** (PER-01 — chuyên viên PTKD) tự chạy luồng cốt lõi trên môi trường staging với tài liệu nghiệp vụ **không nhạy cảm**, nhằm:
- Lấy bằng chứng cho Pilot Gate **G-07** (không còn lỗi chặn).
- Đo **MET-003** (mức độ hoàn thành luồng cốt lõi) và **MET-004** (mức độ hữu ích) — MET-004 thu bằng **phiếu UAT**, vì MVP-lite **không có nút feedback 👍👎 trong sản phẩm** (US-018 là post-MVP).

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Nội dung |
|---|---|
| G-07 | Nhóm người dùng thử nghiệm hoàn thành luồng chính, **không còn lỗi chặn** — bằng chứng: biên bản UAT, người ký: Chủ sở hữu nghiệp vụ |
| MET-003 | Số người hoàn thành trọn "tải PDF → hỏi → kiểm chứng nguồn" ÷ tổng số người tham gia UAT |
| MET-004 | Mức độ hữu ích do người dùng tự đánh giá, thu qua phiếu UAT (không bắt buộc nút feedback trong sản phẩm) |
| §2.4 SDD | Người dùng lần đầu, **không được hướng dẫn**, hoàn thành tài liệu đầu tiên + câu trả lời đầu tiên có nguồn trong ≤ 3 phút (không tính thời gian xử lý tệp) |

## 3. Kịch bản UAT (bám đúng 8 bước hành trình — PRD §2)

| # | Bước | Người dùng làm | Kết quả mong đợi | Story |
|---|---|---|---|---|
| 1 | Truy cập | Mở đường dẫn và đăng nhập | Vào màn hình chính nếu có quyền; báo rõ nếu chưa được cấp quyền | US-001 |
| 2 | Trạng thái trống | Quan sát màn hình lần đầu | Thấy hướng dẫn 3 bước; nút "Tải tài liệu lên" nổi bật; ô câu hỏi bị khóa | US-003 |
| 3 | Tải lên | Chọn hoặc kéo thả **nhiều** PDF | Thấy tiến trình và trạng thái từng tệp: Đang xử lý → Sẵn sàng / Lỗi kèm lý do | US-003 – US-007, US-009, US-010 |
| 4 | Hỏi | Gõ câu hỏi tiếng Việt **hoặc** tiếng Anh | Thấy chỉ báo đang trả lời; câu trả lời xuất hiện kèm thẻ nguồn | US-011, US-012, US-017 |
| 5 | Không có đáp án | Hỏi điều **không** có trong tài liệu | Nhận thông báo "Không tìm thấy thông tin này trong các tài liệu đã tải lên" | US-013 |
| 6 | Kiểm chứng | Đọc tên tệp và số trang ở thẻ nguồn, mở tệp kiểm tra | Thẻ nguồn hiển thị tên tệp + số trang; thông tin **đúng** như câu trả lời nêu | US-014, US-015 |
| 7 | Câu hỏi tiếp theo | Gửi **câu hỏi đầy đủ** (không dựa vào ngữ cảnh câu trước) | Trả lời dựa trên nội dung tài liệu. *Lưu ý: hỏi tiếp nối theo ngữ cảnh là post-MVP (US-016) — nhắc người tham gia trước* | US-011 |
| 8 | Dọn dẹp | Xóa tài liệu cũ hoặc tải nhầm | Hộp xác nhận ghi tên tệp; tài liệu biến mất khỏi danh sách **và khỏi phạm vi trả lời** | US-008 |

## 4. Chuẩn bị dữ liệu và môi trường

| Hạng mục | Yêu cầu |
|---|---|
| Môi trường | `staging` đã qua T-503, T-504, T-505; cấu hình giống `prod` trừ `retention_days` (có thể rút ngắn để minh họa US-021) |
| Tài khoản | ~12 tài khoản thật, cấp quyền bằng CLI (T-103); mỗi người **một tập tài liệu riêng** để kiểm chứng cô lập dữ liệu |
| Tài liệu | Mỗi người chuẩn bị 3 – 5 PDF nghiệp vụ **không nhạy cảm** (tuân thủ BRD CON-004, chờ phê duyệt ATTT nếu dùng tài liệu thật) |
| Phiếu UAT | Biểu mẫu thu: hoàn thành từng bước (Có/Không), thời gian tới câu trả lời đầu tiên, mức hữu ích 1–5, nhận xét tự do, lỗi gặp phải |
| Hỗ trợ | QA trực kênh chat trong suốt tuần UAT để ghi nhận lỗi ngay khi phát sinh |

## 5. Các bước triển khai

1. **Trước UAT (1–2 ngày):** chốt danh sách người tham gia; cấp quyền bằng `python -m app.cli grant-access` (T-103); gửi thư mời kèm đường dẫn staging, phạm vi MVP-lite và **những gì chưa có** (không có feedback 👍👎, không có báo cáo, không hỏi tiếp nối).
2. **Buổi khởi động (30 phút):** giới thiệu mục tiêu; **không** hướng dẫn thao tác chi tiết — để đo được tiêu chí "người dùng lần đầu không được hướng dẫn" của SDD §2.4.
3. **Ngày 1 – 4:** người tham gia tự dùng theo kịch bản §3, ghi phiếu UAT sau mỗi phiên. QA theo dõi log/metric để đối chiếu lỗi người dùng báo với lỗi hệ thống ghi nhận.
4. **Ghi nhận lỗi:** mọi lỗi vào một bảng theo dõi chung, phân loại **Blocker / Major / Minor** ngay khi nhận (chuyển sang T-602 để xử lý).
5. **Ngày 5:** buổi tổng kết, thu toàn bộ phiếu; tổng hợp MET-003 và MET-004.
6. **Biên bản UAT:** PM/BA lập biên bản gồm số người tham gia, tỷ lệ hoàn thành từng bước, MET-003, MET-004, danh sách lỗi còn lại kèm phân loại và kết luận "đạt / chưa đạt G-07"; trình Chủ sở hữu nghiệp vụ ký.

## 6. Trường hợp biên và rủi ro khi chạy UAT

| Tình huống | Xử lý |
|---|---|
| Người tham gia không có PDF phù hợp | BA chuẩn bị sẵn bộ tài liệu mẫu không nhạy cảm để dùng thay |
| ATTT **chưa** phê duyệt dùng tài liệu thật (BRD CON-004) | Chỉ dùng tài liệu mẫu; ghi rõ giới hạn này trong biên bản UAT |
| Người dùng kỳ vọng tính năng post-MVP (feedback, báo cáo, hỏi tiếp nối) | Ghi nhận là **đề xuất backlog**, không tính là lỗi chặn G-07 |
| Lỗi Blocker xuất hiện giữa tuần | Chuyển ngay sang T-602, vá nóng trên staging, yêu cầu người tham gia chạy lại bước liên quan |
| Tỷ lệ hoàn thành MET-003 thấp do khó dùng (không phải do lỗi) | Ghi vào biên bản như phát hiện UX; PM quyết định có chặn pilot hay không |
| Số người tham gia thực tế < 12 | Vẫn chạy, nhưng ghi rõ cỡ mẫu trong biên bản để không suy diễn quá mức từ số liệu |

## 7. Kiểm thử bắt buộc (đầu ra UAT)

- [ ] ≥ 12 người tham gia được cấp quyền và đăng nhập thành công ít nhất 1 lần
- [ ] Cả 8 bước kịch bản §3 được **ít nhất 80%** người tham gia thực hiện
- [ ] Mỗi người hoàn thành ít nhất: 1 lần tải lên nhiều tệp, 3 câu hỏi có đáp án, 1 câu hỏi không có đáp án, 1 lần kiểm chứng nguồn, 1 lần xóa tài liệu
- [ ] Không người dùng nào nhìn thấy tài liệu của người khác (đối chiếu với kết quả tự động của T-504)
- [ ] MET-003 và MET-004 được tính và ghi vào biên bản
- [ ] Toàn bộ lỗi phát sinh đã phân loại Blocker/Major/Minor và chuyển T-602

## 8. Định nghĩa Hoàn thành

- [ ] Biên bản UAT hoàn chỉnh, có chữ ký **Chủ sở hữu nghiệp vụ**
- [ ] **Không còn lỗi Blocker** nào mở (điều kiện cứng của G-07)
- [ ] Danh sách lỗi Major còn lại có kế hoạch xử lý rõ ràng (vá trước pilot hoặc chấp nhận có điều kiện)
- [ ] MET-003 và MET-004 đã ghi nhận làm số liệu nền cho quyết định đầu tư (BRD BO-003)
- [ ] Các đề xuất tính năng thu được trong UAT đã đưa vào backlog, **không** tự ý mở rộng phạm vi pilot

## 9. Tham chiếu

- [PRD §2 — Hành trình người dùng 8 bước; §5.1 G-07; MET-003, MET-004](../../requirements/PRD.md)
- [User Stories v0.4 — 19 story P0/P1 trong phạm vi](../../design/User_Stories.md)
- [SDD UI/UX §2.4 — kịch bản chất lượng "dễ dùng ≤ 3 phút"](../../design/SDD_UI_UX_Blueprint.md)
- [BRD §5.4 (post-MVP), CON-004 (dữ liệu thật)](../../requirements/BRD.md)
- [implement_plan.md §4 M-6, §5 UAT, §8.1](../implement_plan.md)
