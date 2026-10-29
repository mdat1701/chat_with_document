# TC-015 — Câu hỏi không có đáp án trong tài liệu

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-015 |
| User Story / AC | US-013 / AC-013.1, AC-013.3 |
| Task liên quan | T-302, T-307 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit (cổng bằng chứng τ, `NotFoundMessage`); AC-013.2 (bộ ≥10 câu không đáp án, KR2.2) cần T-501 chạy thật — ngoài phạm vi ca này. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 1 tài liệu ở trạng thái `ready`.

## Dữ liệu kiểm thử

- Câu hỏi hoàn toàn không liên quan tới nội dung tài liệu đã tải lên (ví dụ hỏi về chủ đề không hề xuất hiện trong tài liệu).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, chọn tài liệu đã sẵn sàng.
2. Nhập câu hỏi không liên quan tới nội dung tài liệu.
3. Gửi câu hỏi và chờ phản hồi.
4. Quan sát thông báo "không tìm thấy" (`[data-testid="not-found-message"]`).

## Kết quả mong đợi

- KQ1: Hệ thống **không bịa** câu trả lời — trả về thông báo rõ ràng kiểu "không tìm thấy thông tin trong tài liệu" thay vì một câu trả lời nghe hợp lý nhưng vô căn cứ.
- KQ2: Thông báo "không tìm thấy" hiển thị rõ ràng bằng tiếng Việt, không có trích dẫn nào đi kèm (vì không có bằng chứng).
- KQ3: Giao diện vẫn cho phép đặt câu hỏi tiếp theo ngay sau đó, không bị kẹt ở trạng thái lỗi.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-015`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: câu hỏi đã nhập, thông báo "không tìm thấy" hiển thị.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-015_cau-hoi-khong-co-dap-an/`.
7. Nếu không có tài liệu sẵn sàng hoặc không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-013 (AC-013.1, .3)
