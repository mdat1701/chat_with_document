# Báo cáo thực thi — TC-006 Tải lên tệp giả PDF (sai magic-bytes)

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:30:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Tệp `.pdf` nhưng nội dung không phải PDF thật (ở đây: header PNG) bị chặn | `hasPdfSignature()` (T-109) đọc 5 byte đầu qua `FileReader`, không khớp `%PDF-`, chặn trước khi gọi API — `NETWORK_LOG` xác nhận không có `POST /api/v1/documents` nào phát sinh | **PASS** | [TC006_01_tu_choi_sai_magic_bytes.png](./01_tu_choi_sai_magic_bytes.png) |
| KQ2 | Thông báo lỗi rõ ràng, cùng dạng với tệp sai định dạng thường | "fake.pdf: Chỉ hỗ trợ tệp PDF." — cùng `reasonCode=FILE_NOT_PDF` với TC-005 | **PASS** | [TC006_01_tu_choi_sai_magic_bytes.png](./01_tu_choi_sai_magic_bytes.png) |

## Ghi chú

Xác nhận kiểm tra magic-bytes (T-109, đã thêm ở phiên trước) hoạt động đúng trên trình duyệt thật, không chỉ đúng trong `vitest`/jsdom.
