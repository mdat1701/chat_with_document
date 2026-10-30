# Báo cáo thực thi — TC-012 Trạng thái tài liệu cập nhật realtime

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:55:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Postgres 17 thật + `fakeredis` (TCP) cho Redis |
| Kết luận chung | **BLOCKED** (hạ tầng thử nghiệm không hỗ trợ — xem Ghi chú; đã có bằng chứng cụ thể từ TC-004) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL |
|---|---|---|---|
| KQ1 | Badge trạng thái tự chuyển `processing` → `ready` qua SSE, không cần tải lại trang | Trong TC-004, sau khi xử lý xong một tài liệu thật (`document.status` chuyển đúng sang `ready` trong Postgres), giao diện **vẫn hiển thị "Đang xử lý..."** cho tới khi tải lại trang — SSE không bắn được tới trình duyệt | **BLOCKED** |

## Ghi chú / Sai lệch

**Nguyên nhân xác nhận bằng thực nghiệm độc lập (không suy đoán):** viết một script Python nhỏ kiểm tra trực tiếp `fakeredis` — mở 2 kết nối TCP riêng biệt tới cùng instance `fakeredis`, một `SUBSCRIBE`, một `PUBLISH`. Kết quả: **message không được chuyển tiếp giữa 2 kết nối** (subscriber không nhận được gì). Đây là giới hạn đã biết của `fakeredis` ở chế độ `TcpFakeServer` (dùng cho phiên làm việc này thay Redis thật vì sandbox không có Docker) — không phải lỗi của ứng dụng.

Khi tải lại trang (gọi lại `GET /api/v1/documents` thay vì qua kênh đẩy), giao diện hiển thị đúng trạng thái `ready` — xác nhận tầng binding dữ liệu (component đọc đúng trường `status`) hoạt động chính xác; vấn đề chỉ nằm ở kênh truyền tải thời gian thực của môi trường thử nghiệm.

**Việc cần làm để chạy lại ca này và đạt PASS thật:** dùng Redis thật (Docker/Testcontainers hoặc staging) thay cho `fakeredis`.

## Tham chiếu

- Bằng chứng gốc: [`../TC-004_upload-mot-pdf-hop-le/report.md`](../TC-004_upload-mot-pdf-hop-le/report.md) (mục KQ3)
