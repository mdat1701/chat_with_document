# TC-017 — Trích dẫn có kèm số trang

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-017 |
| User Story / AC | US-015 / AC-015.1 |
| Task liên quan | T-202, T-402 |
| Mức ưu tiên | P1 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | AC-015.1/.3 pass thật ở mức unit (`citations.ts` test); AC-015.2 (đối chiếu thủ công với PDF thật) chưa làm — ca này chính là lần đối chiếu thủ công đó. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có 1 tài liệu PDF nhiều trang (≥3 trang), biết trước nội dung ở trang nào để kiểm tra đối chiếu.
- Cờ tính năng hiển thị số trang trích dẫn đang bật (kiểm tra qua `GET /config`, nếu tắt thì BLOCKED và ghi rõ lý do).

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, đặt câu hỏi mà câu trả lời nằm ở một trang cụ thể đã biết trước của tài liệu.
2. Chờ câu trả lời, quan sát trích dẫn có hiển thị số trang hay không.
3. Mở tệp PDF gốc (ngoài ứng dụng, bằng trình đọc PDF bất kỳ) tới đúng trang được trích dẫn, đối chiếu nội dung.

## Kết quả mong đợi

- KQ1: Trích dẫn hiển thị kèm số trang (ví dụ "trang 3") bên cạnh tên tài liệu.
- KQ2: Số trang hiển thị khớp với trang thực tế chứa nội dung được trích trong PDF gốc (đối chiếu thủ công).

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-017`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: trích dẫn kèm số trang trong ứng dụng, VÀ ảnh chụp trang tương ứng trong PDF gốc để đối chiếu.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-017_trich-dan-co-so-trang/`.
7. Nếu tính năng số trang đang tắt qua cấu hình, hoặc không có tài liệu nhiều trang phù hợp, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-015 (AC-015.1)
