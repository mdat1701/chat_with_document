# TC-016 — Trích dẫn hiển thị đúng tên tài liệu nguồn

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-016 |
| User Story / AC | US-014 / AC-014.1, AC-014.2 |
| Task liên quan | T-303, T-306 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit (`test_qa_service.py::test_stream_answer_includes_citations_from_two_documents`, AC-014.2) + component; AC-014.3 (đối chiếu nội dung thật) cần bộ câu hỏi chuẩn + người đánh giá, ngoài phạm vi ca này. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 2 tài liệu tên khác nhau rõ ràng (ví dụ `hop-dong-2026.pdf` và `chinh-sach-bao-hanh.pdf`), cả hai ở trạng thái `ready`.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, đặt một câu hỏi mà câu trả lời trích từ 1 trong 2 tài liệu đã biết rõ.
2. Chờ câu trả lời hoàn tất, quan sát trích dẫn (`[data-testid="citation-chip"]`/`citation-list`).
3. Hover hoặc click vào trích dẫn, quan sát tên tài liệu nguồn hiển thị.
4. Lặp lại với một câu hỏi khác để trích từ tài liệu còn lại, xác nhận tên hiển thị tương ứng đổi đúng theo tài liệu đó.

## Kết quả mong đợi

- KQ1: Tên tài liệu hiển thị trong trích dẫn khớp chính xác với tên tệp đã tải lên (không bị cắt, không nhầm lẫn giữa 2 tài liệu).
- KQ2: Khi câu trả lời trích từ tài liệu khác, tên hiển thị trong trích dẫn thay đổi đúng theo tài liệu đó.
- KQ3: Hover/click vào trích dẫn làm nổi bật đúng đoạn tương ứng trong danh sách, không nhảy nhầm sang mục khác.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-016`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: trích dẫn hiển thị tên tài liệu A, trích dẫn hiển thị tên tài liệu B (câu hỏi khác).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-016_trich-dan-dung-ten-tai-lieu-nguon/`.
7. Nếu không có đủ 2 tài liệu phân biệt được hoặc không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-014 (AC-014.1, .2)
