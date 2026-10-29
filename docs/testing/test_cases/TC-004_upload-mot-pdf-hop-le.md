# TC-004 — Tải lên 1 PDF hợp lệ, theo dõi trạng thái tới "ready"

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-004 |
| User Story / AC | US-003 / AC-003.1, AC-003.2, AC-003.3 |
| Task liên quan | T-108, T-109, T-201, T-202, T-203, T-208 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Unit test pipeline ingestion/upload pass thật (175 test gộp); chưa có E2E thật chạy với ClamAV/TEI thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Hạ tầng dữ liệu (`make up`: Postgres+pgvector, Redis, MinIO, ClamAV, TEI) đang chạy và khoẻ (`make smoke-infra`).
- Thư viện tài liệu hiện chưa đạt hạn mức (`max_documents`, mặc định 50).
- Có sẵn 1 tệp PDF hợp lệ, dung lượng nhỏ hơn `max_file_size_bytes` (mặc định 20MB), số trang nhỏ hơn `max_pages` (mặc định 300).

## Dữ liệu kiểm thử

- Tệp: `tai-lieu-hop-le.pdf` (PDF thật, vài trang, có nội dung văn bản).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, vào màn hình thư viện tài liệu.
2. Kéo-thả hoặc chọn `tai-lieu-hop-le.pdf` vào vùng tải lên (`[data-testid="upload-dropzone"]`).
3. Quan sát dòng tải lên mới xuất hiện trong hàng đợi (`[data-testid="upload-queue"]` / `[data-testid="upload-queue-item"]`) với thanh tiến trình.
4. Sau khi tải lên xong, quan sát tài liệu xuất hiện trong danh sách (`[data-testid="doc-list"]` → `[data-testid="doc-item"]`) với badge trạng thái (`[data-testid="doc-status"]`).
5. Theo dõi badge trạng thái chuyển từ "Đang xử lý"/tương đương sang "Sẵn sàng" (`ready`) mà **không cần tải lại trang** (SSE).
6. Kiểm tra bộ đếm số tài liệu (`[data-testid="doc-counter"]`) tăng thêm 1.

## Kết quả mong đợi

- KQ1: Tệp được chấp nhận vào hàng đợi tải lên ngay (không bị từ chối phía client).
- KQ2: Thanh tiến trình tải lên chạy tới 100% và dòng hàng đợi biến mất sau khi hoàn tất.
- KQ3: Tài liệu xuất hiện trong danh sách với badge trạng thái cập nhật realtime, cuối cùng đạt "Sẵn sàng"/`ready` trong một khoảng thời gian hợp lý mà không cần F5.
- KQ4: Bộ đếm số tài liệu tăng đúng 1.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-004`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: trước khi tải lên, trong lúc tiến trình chạy, ngay sau khi hoàn tất (trạng thái xử lý), và khi đạt "Sẵn sàng".
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-004_upload-mot-pdf-hop-le/`.
7. Nếu không truy cập được `${TEST_BASE_URL}` hoặc hạ tầng dữ liệu chưa sẵn sàng, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-003 (AC-003.1–.3)
