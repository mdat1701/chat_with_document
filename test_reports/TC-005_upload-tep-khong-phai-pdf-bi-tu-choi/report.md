# Báo cáo thực thi — TC-005 Tải lên tệp không phải PDF — bị chặn phía client

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:30:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Tệp `.txt` bị từ chối ngay phía client, không gọi API | `validateFiles()` chặn trước khi gọi `uploadDocument()`; `NETWORK_LOG` xác nhận **không có** `POST /api/v1/documents` nào phát sinh cho lần thử này | **PASS** | [TC005_01_tu_choi_khong_phai_pdf.png](./01_tu_choi_khong_phai_pdf.png) |
| KQ2 | Thông báo lỗi rõ ràng | Banner "Một số tệp không được tải lên" liệt kê "not-a-pdf.txt: Chỉ hỗ trợ tệp PDF." | **PASS** | [TC005_01_tu_choi_khong_phai_pdf.png](./01_tu_choi_khong_phai_pdf.png) |

## Ghi chú

Không phát hiện sai lệch. Khớp đúng mô tả T-109 (kiểm tra `type`/đuôi tệp trước khi vào hàng đợi).
