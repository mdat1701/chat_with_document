# Báo cáo thực thi — TC-008 Tải tệp vượt kích thước tối đa

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:42:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Tệp vượt `max_file_size_bytes` (20MB) bị chặn phía client | Tệp PDF hợp lệ (đúng magic-bytes) nhưng 21MB bị `validateFiles()` chặn trước khi gọi API — `NETWORK_LOG` không có `POST /api/v1/documents` nào | **PASS** | [01_tu_choi_vuot_kich_thuoc.png](./01_tu_choi_vuot_kich_thuoc.png) |
| KQ2 | Thông báo rõ ràng, có hướng dẫn | "qua-lon.pdf: Tệp vượt quá 20 MB. Hãy nén hoặc tách tệp rồi tải lại." — rõ ràng, có gợi ý hành động cụ thể | **PASS** | [01_tu_choi_vuot_kich_thuoc.png](./01_tu_choi_vuot_kich_thuoc.png) |
| KQ3 | Bộ đếm/danh sách tài liệu không đổi | Vẫn `8/50`, danh sách 8 tài liệu cũ giữ nguyên, không có dòng nào cho `qua-lon.pdf` | **PASS** | [01_tu_choi_vuot_kich_thuoc.png](./01_tu_choi_vuot_kich_thuoc.png) |

## Ghi chú

Phát hiện phụ (không phải lỗi, chỉ là lưu ý thao tác): khi thư viện có nhiều tài liệu (8 dòng), lần tải trang đầu tiên sau đăng nhập cần hơn 1.2 giây để danh sách thật sự render xong (trước đó hiển thị skeleton loading) — phải tăng thời gian chờ hoặc `waitForSelector('[data-testid="doc-item"]')` thay vì `waitForTimeout` cố định ngắn trong kịch bản test, nếu không ảnh chụp sẽ chỉ thấy khung xương thay vì dữ liệu thật. Không ảnh hưởng tới kết luận PASS của ca này.
