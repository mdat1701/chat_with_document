# TC-005 — Tải lên tệp không phải PDF, bị chặn ngay phía client

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-005 |
| User Story / AC | US-003/US-005 / AC-005.1 |
| Task liên quan | T-109, T-201 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | `validateFiles()` có 5 unit test pass thật (`files.test.ts`), nhưng chưa có E2E xác nhận qua UI thật rằng request KHÔNG được gửi đi. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có sẵn 1 tệp không phải PDF, ví dụ `ghi-chu.txt`.

## Dữ liệu kiểm thử

- Tệp: `ghi-chu.txt` (văn bản thuần, không phải PDF).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, mở DevTools → tab Network, lọc theo `documents`.
2. Kéo-thả hoặc chọn `ghi-chu.txt` vào vùng tải lên (`[data-testid="upload-dropzone"]`).
3. Quan sát giao diện ngay sau khi chọn tệp (không chờ phản hồi mạng).
4. Kiểm tra tab Network xem có request `POST /api/v1/documents` nào được gửi với tệp này hay không.
5. Quan sát thông báo tệp bị từ chối (`[data-testid="rejected-files-notice"]`).

## Kết quả mong đợi

- KQ1: Tệp **không** xuất hiện trong hàng đợi tải lên (`[data-testid="upload-queue"]`), không có dòng tiến trình nào được tạo cho nó.
- KQ2: Tab Network xác nhận **không có** request `POST /api/v1/documents` nào được gửi cho tệp `ghi-chu.txt` (bị chặn hoàn toàn phía client, đúng thiết kế "chặn trước khi gọi API").
- KQ3: Có thông báo rõ ràng bằng tiếng Việt cho người dùng biết tệp bị từ chối và lý do (loại tệp không hợp lệ), không có tên tệp đầy đủ bị lộ ra sự kiện phân tích (chỉ kiểm tra UI, không cần xác nhận lại phần analytics ở ca này — xem TC-020).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-005`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: giao diện ngay sau khi chọn tệp, thông báo từ chối, và tab Network (zoom đủ rõ để thấy không có request `/documents` mới).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-005_upload-tep-khong-phai-pdf-bi-tu-choi/`.
7. Nếu không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-005 (AC-005.1)
- `frontend/src/shared/validation/files.ts`, `files.test.ts`
