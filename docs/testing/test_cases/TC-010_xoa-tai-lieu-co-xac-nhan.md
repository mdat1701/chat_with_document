# TC-010 — Xóa tài liệu có hộp thoại xác nhận

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-010 |
| User Story / AC | US-008 / AC-008.1, AC-008.2, AC-008.3 |
| Task liên quan | T-206, T-208 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | `DeleteConfirmDialog.test.tsx` pass thật ở mức component; chưa có E2E thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 1 tài liệu ở trạng thái `ready` trong thư viện.

## Dữ liệu kiểm thử

- Tài liệu có sẵn bất kỳ, ghi lại tên để đối chiếu sau khi xóa.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, vào thư viện tài liệu.
2. Ghi lại số lượng tài liệu hiện có và tên tài liệu sẽ xóa.
3. Nhấn nút xóa trên dòng tài liệu đó (`[data-testid="doc-delete"]`).
4. Quan sát hộp thoại xác nhận xuất hiện (`[data-testid="delete-confirm"]`).
5. Nhấn Hủy (`[data-testid="delete-cancel"]`) — xác nhận tài liệu vẫn còn trong danh sách.
6. Lặp lại thao tác xóa, lần này nhấn Xác nhận (`[data-testid="delete-submit"]`).
7. Quan sát danh sách tài liệu sau khi xác nhận.

## Kết quả mong đợi

- KQ1: Nhấn nút xóa luôn mở hộp thoại xác nhận trước, không xóa ngay lập tức.
- KQ2: Nhấn Hủy không làm thay đổi gì — tài liệu vẫn còn nguyên trong danh sách.
- KQ3: Nhấn Xác nhận làm tài liệu biến mất khỏi danh sách và bộ đếm (`[data-testid="doc-counter"]`) giảm đúng 1.
- KQ4: Không có lỗi nào hiện trên Console/Network khi thực hiện xóa.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-010`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: danh sách trước khi xóa, hộp thoại xác nhận, danh sách sau khi Hủy, danh sách sau khi Xác nhận xóa.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-010_xoa-tai-lieu-co-xac-nhan/`.
7. Nếu không có tài liệu sẵn có để xóa, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-008 (AC-008.1–.3)
