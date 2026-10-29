# TC-008 — Tải tệp vượt kích thước tối đa, bị chặn kèm thông báo rõ ràng

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-008 |
| User Story / AC | US-006 / AC-006.1, AC-006.2, AC-006.3 |
| Task liên quan | T-105, T-108, T-109 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Unit + component test pass thật (`validateFiles` kiểm `FILE_TOO_LARGE`); chưa có E2E thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Biết giá trị `max_file_size_bytes` hiện tại qua `GET /config` (mặc định 20MB — `MAX_FILE_SIZE_BYTES` trong `.env.example`).
- Có sẵn 1 tệp PDF hợp lệ về định dạng nhưng vượt quá `max_file_size_bytes` (ví dụ tạo tệp PDF giả lớn hơn giới hạn bằng cách nhồi thêm dữ liệu).

## Dữ liệu kiểm thử

- Tệp: `tep-qua-lon.pdf` (có chữ ký PDF hợp lệ, dung lượng > `max_file_size_bytes`).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, mở DevTools → tab Network.
2. Kéo-thả hoặc chọn `tep-qua-lon.pdf` vào vùng tải lên.
3. Quan sát giao diện ngay sau khi chọn tệp.
4. Kiểm tra tab Network xem có request `POST /api/v1/documents` nào được gửi hay không.

## Kết quả mong đợi

- KQ1: Tệp bị từ chối trước khi vào hàng đợi, kèm thông báo nêu rõ lý do "vượt kích thước tối đa" (có thể kèm giới hạn cụ thể).
- KQ2: Không có request `POST /api/v1/documents` nào được gửi cho tệp này (chặn phía client theo `max_file_size_bytes` lấy từ `GET /config`, không hard-code).
- KQ3: Các tệp khác hợp lệ trong cùng một lần chọn (nếu test kèm nhiều tệp) không bị ảnh hưởng bởi tệp quá khổ này.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-008`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: thông báo từ chối, tab Network xác nhận không có request mới.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-008_upload-tep-vuot-kich-thuoc/`.
7. Nếu không truy cập được `${TEST_BASE_URL}` hoặc không tạo được tệp vượt kích thước phù hợp, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-006 (AC-006.1–.3)
