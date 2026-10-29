# TC-020 — Không lộ nội dung nhạy cảm qua Network/sự kiện phân tích

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-020 |
| User Story / AC | US-020 / AC-020.1 |
| Task liên quan | T-007, T-404, T-503 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện, kiểm tra Network) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit (allow-list, hash một chiều, `test_logging_scrub.py` canary-string); **canary end-to-end thật** (G-04) qua UI thật chưa có — ca này chính là lần kiểm chứng đó. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).
- `TEST_API_BASE_URL`: URL gốc backend (mặc định `http://localhost:8000`) — dùng để đối chiếu nếu cần xem trực tiếp response.

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Chuẩn bị 1 tài liệu PDF có chứa một chuỗi "canary" duy nhất, dễ nhận diện, không trùng với bất kỳ nội dung nào khác (ví dụ `ZZCANARY7781`), chèn vào nội dung văn bản của tài liệu.
- Chuẩn bị 1 câu hỏi có chứa chuỗi canary khác (ví dụ `ZZQUESTION9912`) để kiểm tra chuỗi câu hỏi không bị lộ.

## Dữ liệu kiểm thử

- Tài liệu: `tai-lieu-canary.pdf` (chứa chuỗi `ZZCANARY7781`), tên tệp đặt tên nhạy cảm giả định để kiểm tra không lộ tên tệp (ví dụ `bao-cao-mat-2026.pdf`).
- Câu hỏi: chứa chuỗi `ZZQUESTION9912`.

## Các bước thực hiện

1. Mở DevTools → tab Network, bắt đầu ghi lại (Preserve log) trước khi thao tác.
2. Tải lên `tai-lieu-canary.pdf`, chờ tới `ready`.
3. Đặt câu hỏi chứa chuỗi `ZZQUESTION9912` liên quan tới nội dung tài liệu.
4. Chờ câu trả lời hoàn tất.
5. Xóa tài liệu vừa tải (xem TC-010).
6. Trong tab Network, lọc/tìm kiếm toàn bộ request/response (đặc biệt các request tới `/events`, `/api/v1/conversations*`) để tìm chuỗi `ZZCANARY7781`, `ZZQUESTION9912`, và tên tệp `bao-cao-mat-2026.pdf`.

## Kết quả mong đợi

- KQ1: Không có request/response nào trong tab Network (đặc biệt các request gửi sự kiện phân tích tới `/events`) chứa chuỗi `ZZCANARY7781` (nội dung tài liệu).
- KQ2: Không có request/response nào chứa chuỗi `ZZQUESTION9912` (nội dung câu hỏi) bên ngoài chính request `/conversations` phục vụ hỏi-đáp (request hỏi-đáp bản thân nó tất nhiên chứa câu hỏi — chỉ kiểm tra các request KHÁC như `/events`/analytics không chứa).
- KQ3: Không có request/response nào chứa tên tệp đầy đủ `bao-cao-mat-2026.pdf` trong các request sự kiện phân tích (`/events`).
- KQ4: Các request `/events` (nếu quan sát được payload) chỉ chứa các khóa `props` thuộc allow-list đã khai báo (ví dụ `file_size_bucket`, `reason_code`, không có `file_name`/`content`).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-020`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: tab Network với bộ lọc tìm kiếm chuỗi canary cho thấy không có kết quả khớp ở các request không mong muốn (chụp rõ ô tìm kiếm + kết quả "không tìm thấy" hoặc danh sách request đã kiểm tra).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md), liệt kê rõ các request đã kiểm tra trong phần "Ghi chú".
6. Lưu toàn bộ artifact vào `./test_reports/TC-020_khong-lo-noi-dung-qua-network-analytics/`.
7. Nếu không thể quan sát được payload request (ví dụ bị mã hoá/không xem được qua DevTools), báo **BLOCKED** kèm lý do, không suy luận PASS.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-020 (AC-020.1)
- `docs/implement/tasks/T-404_minimal-analytics-events.md` §3.2 (allow-list)
