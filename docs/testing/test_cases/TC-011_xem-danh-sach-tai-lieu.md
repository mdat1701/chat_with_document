# TC-011 — Xem danh sách tài liệu, bộ đếm hiển thị đúng

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-011 |
| User Story / AC | US-009 / AC-009.1, AC-009.3, AC-009.4 |
| Task liên quan | T-205 |
| Mức ưu tiên | P1 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | `DocumentLibrary.test.tsx` pass thật (skeleton, điều hướng mũi tên); AC-009.2 (hiệu năng cuộn 50 tài liệu ≤100ms) chưa đo trên dữ liệu thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 3 tài liệu ở các trạng thái khác nhau nếu có thể (ví dụ 1 đang xử lý, 2 sẵn sàng) để kiểm tra hiển thị badge khác nhau.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, vào thư viện tài liệu.
2. Quan sát danh sách (`[data-testid="doc-list"]`), đếm số dòng (`[data-testid="doc-item"]`) và đối chiếu với bộ đếm (`[data-testid="doc-counter"]`).
3. Nhấn vào một dòng tài liệu, dùng phím mũi tên `↓`/`↑` để di chuyển giữa các dòng (focus roving).
4. Kiểm tra mỗi dòng hiển thị đúng tên tệp, trạng thái (`[data-testid="doc-status"]`).

## Kết quả mong đợi

- KQ1: Số dòng trong danh sách khớp đúng với giá trị hiển thị ở bộ đếm.
- KQ2: Mỗi tài liệu hiển thị đúng tên và badge trạng thái tương ứng (màu/icon khác nhau theo trạng thái).
- KQ3: Phím `↓`/`↑` di chuyển focus tuần tự giữa các dòng, dừng ở đầu/cuối danh sách (không xoay vòng), không ảnh hưởng tới phần tử khác trên trang.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-011`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: toàn bộ danh sách, trạng thái focus khi dùng phím mũi tên.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-011_xem-danh-sach-tai-lieu/`.
7. Nếu không có đủ dữ liệu tài liệu mẫu, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-009 (AC-009.1, .3, .4)
