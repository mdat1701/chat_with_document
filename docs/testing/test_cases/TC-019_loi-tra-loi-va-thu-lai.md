# TC-019 — Lỗi khi trả lời và luồng Thử lại

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-019 |
| User Story / AC | US-011 (nhánh lỗi) / AC-011.3 (xử lý lỗi), liên quan US-013 |
| Task liên quan | T-304, T-307 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | 6 mã lỗi + not_found/partial/incomplete + error boundary đã nối và có unit/component test pass thật (`T-307_not-found-and-error-handling.md`); chưa có E2E thật mô phỏng lỗi mạng giữa chừng. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có 1 tài liệu ở trạng thái `ready`.
- Có khả năng mô phỏng lỗi mạng/timeout (ví dụ dùng DevTools → Network → "Offline"/throttling, hoặc tắt backend giữa chừng nếu chạy trên máy test có thể kiểm soát được).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, bắt đầu đặt một câu hỏi.
2. Ngay sau khi gửi câu hỏi (trong lúc đang streaming), dùng DevTools chuyển mạng sang "Offline" hoặc dừng backend để mô phỏng lỗi.
3. Quan sát thông báo lỗi hiển thị (`[data-testid="error-message"]`) và mã lỗi tương ứng.
4. Khôi phục mạng/backend.
5. Nhấn nút Thử lại (`[data-testid="retry-button"]`).
6. Quan sát kết quả sau khi thử lại.

## Kết quả mong đợi

- KQ1: Khi xảy ra lỗi mạng/timeout giữa chừng, giao diện hiển thị thông báo lỗi rõ ràng với mã lỗi xác định (không phải màn hình trắng/crash im lặng).
- KQ2: Nút "Thử lại" xuất hiện cùng thông báo lỗi.
- KQ3: Sau khi khôi phục kết nối và nhấn "Thử lại", hệ thống gửi lại câu hỏi và nhận được câu trả lời hoàn chỉnh (hoặc thông báo lỗi mới nếu vẫn còn sự cố — không bị kẹt ở trạng thái cũ).
- KQ4: Không có lỗi JavaScript không bắt được (unhandled exception) nào xuất hiện trên Console trong suốt quá trình.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-019`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: thông báo lỗi với mã lỗi, nút Thử lại, kết quả sau khi thử lại thành công.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-019_loi-tra-loi-va-thu-lai/`.
7. Nếu không có cách mô phỏng lỗi mạng trong môi trường thực thi (ví dụ không có quyền điều khiển backend/DevTools), báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-011, US-013
- `docs/implement/tasks/T-307_not-found-and-error-handling.md`
