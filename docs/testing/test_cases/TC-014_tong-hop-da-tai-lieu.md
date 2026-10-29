# TC-014 — Đặt câu hỏi cần tổng hợp từ nhiều tài liệu

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-014 |
| User Story / AC | US-012 / AC-012.1 |
| Task liên quan | T-401 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit (`test_retrieval_service.py`, `test_qa_service.py` — bằng chứng rải 2 tài liệu); chưa chạy với TEI/rerank thật. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Đã đăng nhập thành công (xem TC-001).
- Có ít nhất 2 tài liệu ở trạng thái `ready`, mỗi tài liệu chứa một phần thông tin khác nhau cần thiết để trả lời đầy đủ 1 câu hỏi (ví dụ tài liệu A nói về giá, tài liệu B nói về điều khoản).

## Dữ liệu kiểm thử

- 2 tài liệu bổ sung thông tin cho nhau.
- Câu hỏi cần cả 2 nguồn mới trả lời đầy đủ được.

## Các bước thực hiện

1. Truy cập `${TEST_BASE_URL}`, đảm bảo cả 2 tài liệu đã sẵn sàng.
2. Đặt câu hỏi cần thông tin từ cả 2 tài liệu.
3. Chờ câu trả lời hoàn tất.
4. Quan sát danh sách trích dẫn (`[data-testid="citation-list"]`).

## Kết quả mong đợi

- KQ1: Câu trả lời đề cập tới nội dung liên quan từ cả 2 tài liệu (không chỉ dựa vào 1 nguồn).
- KQ2: Danh sách trích dẫn có ít nhất 1 trích dẫn trỏ về tài liệu A và ít nhất 1 trích dẫn trỏ về tài liệu B.
- KQ3: Tên tài liệu hiển thị trong trích dẫn chính xác, phân biệt rõ ràng giữa 2 nguồn.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-014`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: câu trả lời đầy đủ, danh sách trích dẫn thể hiện cả 2 tài liệu nguồn.
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-014_tong-hop-da-tai-lieu/`.
7. Nếu không có đủ 2 tài liệu phù hợp hoặc không truy cập được `${TEST_BASE_URL}`, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-012 (AC-012.1)
