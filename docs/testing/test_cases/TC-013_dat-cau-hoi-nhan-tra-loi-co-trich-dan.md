# TC-013 — Đặt câu hỏi, nhận trả lời dạng streaming kèm trích dẫn

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-013 |
| User Story / AC | US-011 / AC-011.1, AC-011.2, AC-011.3, AC-011.4 |
| Task liên quan | T-302, T-303, T-304, T-305, T-306 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit/component với `FakeLLM`/dữ liệu giả. **AC-011.5 (≥85% đúng) cần T-501 chạy thật với LLM thật** — ngoài phạm vi ca này (xem test_plan.md §6.1.6/§11). Ca này dùng `LLM_PROVIDER=fake` hoặc LLM thật tuỳ cấu hình môi trường — câu trả lời có thể là chuỗi cố định nếu dùng fake, không phản ánh chất lượng thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 1 tài liệu ở trạng thái `ready`, nội dung có chứa thông tin trả lời được cho câu hỏi dự kiến đặt.

## Dữ liệu kiểm thử

- Câu hỏi mẫu bằng tiếng Việt liên quan trực tiếp tới nội dung tài liệu đã tải lên.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, chọn tài liệu đã sẵn sàng.
2. Nhập câu hỏi vào ô soạn thảo (`[data-testid="question-input"]`).
3. Nhấn gửi (`[data-testid="send-button"]`).
4. Quan sát chỉ báo đang nhập/trả lời (`[data-testid="typing-indicator"]`, `[data-testid="streaming-cursor"]`).
5. Chờ câu trả lời hoàn tất (`[data-testid="answer-message"]`, `[data-testid="answer-markdown"]`).
6. Quan sát danh sách trích dẫn (`[data-testid="citation-list"]`) và các chip trích dẫn (`[data-testid="citation-chip"]`/`[data-testid="citation-ref"]`) trong nội dung trả lời.
7. Quan sát độ trễ hiển thị (`[data-testid="answer-latency"]`) nếu có.

## Kết quả mong đợi

- KQ1: Câu trả lời xuất hiện theo kiểu streaming (từng phần nối tiếp), có con trỏ đang gõ trong lúc chờ.
- KQ2: Câu trả lời có ít nhất 1 trích dẫn liên kết tới tài liệu đã tải lên, trích dẫn hiển thị dưới dạng số thứ tự `[n]` trong văn bản và danh sách trích dẫn ở cuối.
- KQ3: Hover/click vào trích dẫn trong văn bản làm nổi bật đúng mục tương ứng trong danh sách trích dẫn.
- KQ4: Không có lỗi Console/Network trong suốt quá trình hỏi-đáp.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-013`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: lúc đang streaming, câu trả lời hoàn chỉnh kèm trích dẫn, trạng thái hover/click trích dẫn.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-013_dat-cau-hoi-nhan-tra-loi-co-trich-dan/`.
7. Nếu không có tài liệu sẵn sàng hoặc không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do. Nếu môi trường dùng `LLM_PROVIDER=fake`, ghi rõ trong "Ghi chú/Sai lệch" rằng nội dung câu trả lời là giả lập, không đánh giá chất lượng nội dung — chỉ đánh giá hành vi giao diện/trích dẫn.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-011 (AC-011.1–.4)
