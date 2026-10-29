# TC-009 — Đạt hạn mức số tài liệu, nút tải lên bị vô hiệu hoá

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-009 |
| User Story / AC | US-007 / AC-007.1 |
| Task liên quan | T-105, T-108 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | AC-007.1 pass thật ở mức unit. AC-007.2 (5 upload đồng thời tranh 2 chỗ quota) đã viết `test_upload_concurrency.py` bằng Testcontainers nhưng **chưa chạy thật** (không có Docker trong môi trường triển khai — xem `T-108_upload-api.md`). Ca này chỉ kiểm chứng AC-007.1 (hạn mức đã đạt, không phải tranh chấp đồng thời). |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Số tài liệu hiện có của tài khoản test **bằng đúng** `max_documents` (mặc định 50) — cần chuẩn bị trước bằng cách tải đủ số tài liệu, hoặc seed trực tiếp vào DB nếu có quyền truy cập (xem `backend/tests/integration/conftest.py::_insert_document` làm tham khảo cách chèn dữ liệu test, không chạy trực tiếp script test này trên DB thật).

## Dữ liệu kiểm thử

- 1 tệp PDF hợp lệ bất kỳ để thử tải lên khi đã đạt hạn mức.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}` với tài khoản đã có đủ `max_documents` tài liệu.
2. Quan sát bộ đếm (`[data-testid="doc-counter"]`) hiển thị đã đạt hạn mức (ví dụ "50/50").
3. Quan sát vùng tải lên (`[data-testid="upload-dropzone"]`) — kiểm tra trạng thái `disabled` và tooltip lý do (`[data-testid="upload-dropzone-tooltip"]`).
4. Thử kéo-thả hoặc chọn 1 tệp PDF hợp lệ vào vùng tải lên.

## Kết quả mong đợi

- KQ1: Bộ đếm hiển thị đúng số tài liệu hiện có / hạn mức tối đa.
- KQ2: Vùng tải lên ở trạng thái vô hiệu hoá (disabled), có tooltip giải thích lý do (đã đạt hạn mức).
- KQ3: Thử tải tệp mới vào vùng đã bị vô hiệu hoá không tạo ra request `POST /api/v1/documents` nào (kiểm tra tab Network).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-009`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: bộ đếm hạn mức, vùng tải lên bị vô hiệu hoá kèm tooltip, tab Network khi thử tải thêm.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-009_dat-han-muc-tai-lieu/`.
7. Nếu không chuẩn bị được tài khoản đã đạt đúng hạn mức, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-007 (AC-007.1)
- `backend/tests/integration/test_upload_concurrency.py` (AC-007.2, chưa chạy thật)
