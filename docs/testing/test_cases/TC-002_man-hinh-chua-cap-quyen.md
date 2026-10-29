# TC-002 — Màn hình "chưa được cấp quyền" cho người dùng không có quyền

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-002 |
| User Story / AC | US-001 / AC-001.3, AC-001.4 |
| Task liên quan | T-101, T-107 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | `AuthScreens.test.tsx` có test axe-core cho `NoAccessScreen` ở mức component (pass thật), nhưng chưa có kiểm chứng đầu-cuối qua IdP thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).
- Cần IdP thật đã cấu hình (như TC-001). Nếu chưa có, BLOCKED.

## Tiền điều kiện

- Có một tài khoản hợp lệ trên IdP nhưng **chưa** được cấp quyền truy cập ứng dụng (không chạy `grant-access` cho email này, hoặc đã `revoke-access`).
- Xác nhận bằng `python -m app.cli list-users --active-only` rằng email dùng để test không nằm trong danh sách.

## Dữ liệu kiểm thử

- Tài khoản IdP thật chưa được cấp quyền: `<email chưa grant-access>`.

## Các bước thực hiện

1. Mở trình duyệt ẩn danh, truy cập `${TEST_BASE_URL}`.
2. Đăng nhập qua IdP bằng tài khoản **chưa** được cấp quyền.
3. Quan sát ứng dụng sau khi IdP chuyển hướng về.

## Kết quả mong đợi

- KQ1: Người dùng không được vào thư viện tài liệu; thay vào đó thấy màn hình "Không có quyền truy cập" (`NoAccessScreen`).
- KQ2: Màn hình này có thông điệp rõ ràng bằng tiếng Việt, không lộ thông tin kỹ thuật (stack trace, mã lỗi nội bộ) cho người dùng cuối.
- KQ3: Không có cách nào từ màn hình này điều hướng thẳng tới dữ liệu tài liệu (không có liên kết ẩn/API call thành công nào trả về danh sách tài liệu — kiểm tra tab Network).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-002`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng (màn hình "No access", tab Network nếu kiểm tra KQ3).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-002_man-hinh-chua-cap-quyen/`.
7. Nếu không có IdP thật hoặc không có tài khoản phù hợp tiền điều kiện, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-001 (AC-001.3, AC-001.4)
