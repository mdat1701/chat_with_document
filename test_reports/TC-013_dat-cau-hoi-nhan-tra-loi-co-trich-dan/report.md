# Báo cáo thực thi — TC-013 Đặt câu hỏi, nhận trả lời kèm trích dẫn

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:55:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Postgres 17 thật **không có pgvector** (quyết định có chủ đích của phiên làm việc — xem hội thoại trước: từ chối cài Visual Studio Build Tools) |
| Kết luận chung | **BLOCKED** (thiếu pgvector — lý do xác nhận bằng traceback thật, không suy đoán) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL |
|---|---|---|---|
| KQ1-4 (trả lời + trích dẫn) | Nhận câu trả lời streaming kèm trích dẫn | Giao diện báo "⚠ Dịch vụ đang bận. Vui lòng thử lại." | **BLOCKED** |

## Nguyên nhân (xác nhận bằng traceback thật, không suy đoán)

```
sqlalchemy.exc.ProgrammingError: operator does not exist: text <=> unknown
[SQL: SELECT ... $1::INTEGER - (chunk.embedding <=> $2) AS score FROM chunk ...
       ORDER BY chunk.embedding <=> $6 LIMIT $7::INTEGER]
```

Toán tử `<=>` (khoảng cách cosine) là toán tử của kiểu dữ liệu `vector` (pgvector). Vì Postgres trong môi trường này **không có pgvector** (quyết định có chủ đích — xem phần đầu phiên làm việc: biên dịch pgvector cần Visual Studio Build Tools, người dùng chọn không cài), cột `chunk.embedding` trong bản vá cục bộ dùng tạm `TEXT` thay vì `vector(1024)` để ít nhất tạo được schema và test các luồng không liên quan tới vector (đăng nhập, tải tài liệu, cô lập dữ liệu...). Khi `retrieve()` (`app/modules/retrieval/service.py`) chạy truy vấn thật dùng `<=>`, Postgres từ chối vì kiểu `TEXT` không hỗ trợ toán tử này. **Đây đúng là giới hạn đã được báo trước, không phải lỗi mới** — US-011/AC-011.5 (câu trả lời có trích dẫn, retrieval vector thật) **không thể kiểm chứng được nếu không có pgvector thật**.

## 2 lỗi THẬT (không liên quan tới pgvector) phát hiện và đã sửa trong lúc chẩn đoán ca này

Trước khi tìm ra nguyên nhân thật ở trên, lỗi hoàn toàn **vô hình** trong log — phải tự thêm log mới chẩn đoán được. Đây là 2 lỗi quan sát/vận hành thật, độc lập với pgvector, áp dụng cho MỌI lỗi không lường trước trong toàn backend:

1. **`app/api/routers/conversations.py::ask_question`**: khối `except Exception:` (bắt mọi lỗi không lường trước trong luồng trả lời) nuốt im lặng hoàn toàn, không log gì — client chỉ thấy `SERVICE_BUSY`, vận hành không có cách nào biết lỗi thật là gì. Đã thêm `logger.exception(...)` trước khi trả lỗi cho client (vẫn giữ nguyên mã lỗi chung, không lộ chi tiết nội bộ ra ngoài — đúng P-03).
2. **(Nghiêm trọng hơn) `app/core/logging.py::_JsonFormatter`**: dù đã gọi `logger.exception(...)` đúng cách, bộ định dạng log JSON **chưa từng** đọc `record.exc_info` — nghĩa là **MỌI** lời gọi `logger.exception()`/`logger.error(..., exc_info=True)` trong toàn bộ backend (không chỉ chỗ vừa sửa ở trên) chỉ ghi được dòng thông điệp, mất hoàn toàn traceback. Đây là lỗ hổng quan sát hệ thống (observability) có phạm vi ảnh hưởng toàn backend, chưa từng bị phát hiện vì không có tình huống nào trước đây thực sự cần đọc traceback từ log JSON. Đã sửa: thêm `payload["error_trace"] = self.formatException(record.exc_info)` khi có `exc_info` — xác nhận an toàn P-03 vì `formatException` chỉ trả về đường dẫn tệp/dòng/mã nguồn, không chứa giá trị biến (không có nguy cơ lộ nội dung câu hỏi/câu trả lời). Thêm 1 unit test xác nhận traceback thật xuất hiện trong `error_trace`.

Xác nhận bằng `ruff check`, `mypy`, `pytest` (179 passed, 13 skipped, +1 từ test mới).

## Ghi chú

**Việc cần làm để chạy lại ca này và đạt PASS thật:** cần Postgres có pgvector thật (Docker/staging) — không khắc phục được bằng cách khác trong sandbox này theo quyết định đã thống nhất với người dùng.
