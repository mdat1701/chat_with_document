# TC-018 — Hỏi đáp bằng tiếng Anh, giao diện vẫn giữ tiếng Việt

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-018 |
| User Story / AC | US-017 / AC-017.1, AC-017.2 |
| Task liên quan | T-403 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật **chỉ ở nhánh heuristic dự phòng** (`test_qa_language_detection.py`) — `lingua` (nhánh chính) không cài được trong môi trường triển khai (thiếu C++ Build Tools cho Python 3.15, xem test_plan.md §11/§15). Ca này có thể cho kết quả khác khi chạy trên môi trường CI/staging thật (Python 3.12, có `lingua`). |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có 1 tài liệu ở trạng thái `ready`, nội dung có thể trả lời được cả câu hỏi tiếng Anh lẫn tiếng Việt.

## Dữ liệu kiểm thử

- Câu hỏi tiếng Anh, ví dụ: "What is the refund policy mentioned in this document?"

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}` — xác nhận toàn bộ nhãn, nút, thông báo trên giao diện đang hiển thị tiếng Việt.
2. Nhập câu hỏi bằng tiếng Anh vào ô soạn thảo.
3. Gửi câu hỏi và chờ câu trả lời.
4. Quan sát ngôn ngữ của câu trả lời.
5. Quan sát toàn bộ phần còn lại của giao diện (nút, nhãn, thông báo) trong suốt quá trình.

## Kết quả mong đợi

- KQ1: Câu trả lời được trả về bằng tiếng Anh (khớp ngôn ngữ câu hỏi), không bị trộn lẫn hoặc trả lời sai ngôn ngữ.
- KQ2: Toàn bộ giao diện xung quanh (nút gửi, nhãn trường nhập, thông báo hệ thống) vẫn giữ nguyên tiếng Việt, không đổi theo ngôn ngữ câu hỏi.
- KQ3: Không có lỗi phát sinh do phát hiện sai ngôn ngữ (ví dụ câu trả lời trộn lẫn 2 ngôn ngữ một cách bất thường).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-018`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: câu hỏi tiếng Anh đã nhập, câu trả lời tiếng Anh nhận được, cùng với phần giao diện xung quanh vẫn tiếng Việt.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md), ghi rõ trong "Ghi chú/Sai lệch" nếu môi trường đang chạy nhánh heuristic dự phòng (không có `lingua`) vì có thể ảnh hưởng độ chính xác phát hiện ngôn ngữ.
6. Lưu toàn bộ artifact vào `./test_reports/TC-018_hoi-dap-tieng-anh/`.
7. Nếu không có tài liệu sẵn sàng hoặc không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-017 (AC-017.1, .2)
