# TC-007 — Tải nhiều tệp đồng thời, hàng đợi giới hạn 3 song song

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-007 |
| User Story / AC | US-004 / AC-004.1, AC-004.2, AC-004.3 |
| Task liên quan | T-108, T-109 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Hàng đợi 3 đồng thời có code + đọc xác nhận đúng; chưa có test tự động mô phỏng lỗi mạng giữa chừng một tệp trong hàng đợi (xem `T-109_upload-client.md` §7). |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Hạn mức tài liệu còn ít nhất 5 chỗ trống.
- Có sẵn 5 tệp PDF hợp lệ, kích thước khác nhau (để phân biệt trên hàng đợi).

## Dữ liệu kiểm thử

- 5 tệp: `tep-1.pdf` .. `tep-5.pdf` (PDF hợp lệ).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, vào màn hình thư viện tài liệu.
2. Chọn cùng lúc cả 5 tệp và thả vào vùng tải lên.
3. Ngay sau khi thả, quan sát hàng đợi (`[data-testid="upload-queue"]`) — đếm số dòng đang ở trạng thái "đang tải" (uploading) so với "đang chờ" (queued).
4. Theo dõi tới khi tất cả 5 tệp lần lượt hoàn tất.
5. Kiểm tra danh sách tài liệu (`[data-testid="doc-list"]`) có đủ 5 tài liệu mới.

## Kết quả mong đợi

- KQ1: Ngay sau khi thả 5 tệp, tối đa **3** tệp ở trạng thái "đang tải" cùng lúc; 2 tệp còn lại ở trạng thái "đang chờ" cho tới khi có chỗ trống.
- KQ2: Khi một tệp đang tải hoàn tất, tệp đang chờ tiếp theo tự động bắt đầu (không cần thao tác thủ công).
- KQ3: Sau khi hoàn tất, cả 5 tài liệu xuất hiện trong danh sách, không có tệp nào bị bỏ sót hoặc trùng lặp.
- KQ4: Mỗi tệp được gửi bằng một request `POST /api/v1/documents` riêng (kiểm tra tab Network — không gộp nhiều tệp vào 1 request).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-007`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: ngay sau khi thả 5 tệp (để thấy rõ 3 đang tải + 2 đang chờ), trạng thái giữa chừng, và danh sách tài liệu cuối cùng với đủ 5 tệp.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-007_upload-nhieu-tep-dong-thoi/`.
7. Nếu không truy cập được `${TEST_BASE_URL}` hoặc hạn mức không đủ chỗ trống, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-004 (AC-004.1–.3)
- `frontend/src/features/documents/useUploadQueue.ts` (`MAX_CONCURRENT`)
