# TC-012 — Trạng thái tài liệu cập nhật realtime (SSE) không cần tải lại trang

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-012 |
| User Story / AC | US-010 / AC-010.2, AC-010.3 |
| Task liên quan | T-204, T-205, T-208 |
| Mức ưu tiên | P1 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit/component (`StatusBadge.test.tsx`); độ trễ SSE ≤5s (AC-010.1) chưa đo trên staging. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Hạ tầng dữ liệu đang chạy (Postgres, Redis, MinIO, ClamAV, TEI — `make up`).

## Dữ liệu kiểm thử

- 1 tệp PDF hợp lệ, đủ lớn để quá trình xử lý (quét mã độc → trích xuất → embedding) không hoàn tất tức thì, đủ để quan sát được các trạng thái trung gian.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, mở DevTools → tab Network → lọc theo `EventSource`/`event-stream` để quan sát kết nối SSE.
2. Tải lên tệp PDF.
3. **Không** tải lại trang (F5) trong suốt quá trình theo dõi.
4. Quan sát badge trạng thái (`[data-testid="doc-status"]`) của tài liệu vừa tải thay đổi qua các bước (ví dụ: đang tải → đang xử lý → sẵn sàng) theo thời gian thực.
5. Ghi lại thời điểm tải lên xong và thời điểm badge chuyển sang "Sẵn sàng".

## Kết quả mong đợi

- KQ1: Có một kết nối SSE/EventSource đang mở trong tab Network trong suốt quá trình xử lý.
- KQ2: Badge trạng thái tự động cập nhật mà không cần F5, phản ánh đúng tiến trình xử lý thật.
- KQ3: Thời gian từ lúc tài liệu đổi trạng thái ở backend tới lúc UI cập nhật không có độ trễ cảm nhận được rõ ràng (ghi nhận thời gian quan sát được, không cần đạt chính xác ngưỡng ≤5s của AC-010.1 — đó là phép đo hiệu năng riêng, ngoài phạm vi ca này).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-012`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: tab Network thể hiện kết nối SSE, badge trạng thái ở từng giai đoạn (ít nhất 2 trạng thái trung gian khác nhau nếu quan sát được).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-012_trang-thai-tai-lieu-realtime/`.
7. Nếu không truy cập được `${TEST_BASE_URL}` hoặc hạ tầng dữ liệu chưa sẵn sàng, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-010 (AC-010.2, .3)
