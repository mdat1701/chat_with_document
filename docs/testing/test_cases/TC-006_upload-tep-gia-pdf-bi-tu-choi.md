# TC-006 — Tải lên tệp giả PDF (sai magic-bytes), bị từ chối

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-006 |
| User Story / AC | US-005 / AC-005.2 |
| Task liên quan | T-109, T-201 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | `hasPdfSignature()`/`validateFiles()` có unit test pass thật (`files.test.ts::rejects a PNG renamed to .pdf`), nhưng chưa có E2E xác nhận qua UI thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có sẵn 1 tệp ảnh PNG/JPEG thật, đổi tên đuôi thành `.pdf` (ví dụ `anh-gia-mao.pdf`, nội dung byte thực chất là ảnh, không có chữ ký `%PDF-` ở đầu tệp).

## Dữ liệu kiểm thử

- Tệp: `anh-gia-mao.pdf` (nội dung thực là PNG/JPEG, đổi đuôi tệp thành `.pdf`).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, mở DevTools → tab Network, lọc theo `documents`.
2. Kéo-thả hoặc chọn `anh-gia-mao.pdf` vào vùng tải lên (`[data-testid="upload-dropzone"]`).
3. Quan sát giao diện ngay sau khi chọn tệp.
4. Kiểm tra tab Network xem có request `POST /api/v1/documents` nào được gửi với tệp này hay không.

## Kết quả mong đợi

- KQ1: Tệp bị từ chối **trước khi** vào hàng đợi tải lên — không xuất hiện dòng tiến trình nào cho nó.
- KQ2: Tab Network xác nhận **không có** request `POST /api/v1/documents` nào được gửi (kiểm tra magic-bytes chặn thành công phía client, đúng `hasPdfSignature()`).
- KQ3: Thông báo từ chối hiển thị cùng mã lý do với tệp "không phải PDF" thông thường (`FILE_NOT_PDF`), không có thông điệp gây hiểu lầm khác.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-006`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: giao diện ngay sau khi chọn tệp, thông báo từ chối, tab Network.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-006_upload-tep-gia-pdf-bi-tu-choi/`.
7. Nếu không truy cập được `${TEST_BASE_URL}` hoặc không chuẩn bị được tệp giả mạo đúng mô tả, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-005 (AC-005.2)
- `frontend/src/shared/validation/files.ts` (`hasPdfSignature`)
