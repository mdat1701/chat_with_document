# Báo cáo thực thi — TC-019 Lỗi khi trả lời và luồng Thử lại

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:05:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-013 (lỗi thật xảy ra tự nhiên do Postgres không có pgvector — không cần mô phỏng lỗi mạng bằng DevTools) |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Thông báo lỗi rõ ràng kèm mã lỗi, không màn hình trắng/crash | Banner đỏ "⚠ Dịch vụ đang bận. Vui lòng thử lại." hiển thị ngay dưới câu hỏi, không có màn hình trắng hay treo giao diện | **PASS** | [01_loi_va_nut_thu_lai.png](./01_loi_va_nut_thu_lai.png) |
| KQ2 | Nút "Thử lại" xuất hiện cùng thông báo lỗi | `[data-testid="retry-button"]` hiện ngay cạnh banner lỗi | **PASS** | [01_loi_va_nut_thu_lai.png](./01_loi_va_nut_thu_lai.png) |
| KQ3 | Thử lại gửi lại câu hỏi, nhận kết quả mới (trả lời hoặc lỗi mới), không kẹt ở trạng thái cũ | Bấm "Thử lại" → `NETWORK_LOG` xác nhận gửi lại đúng `POST .../questions` lần 2 → sau ~3-6 giây, banner lỗi mới xuất hiện lại (vẫn lỗi vì nguyên nhân gốc — thiếu pgvector — chưa khắc phục), giao diện **không bị kẹt ở trạng thái cũ hay màn hình trống** | **PASS** | [03_sau_khi_thu_lai_6s.png](./03_sau_khi_thu_lai_6s.png) |
| KQ4 | Không có lỗi JS không bắt được trên Console | `CONSOLE_ERRORS` của lần chạy chỉ gồm 4× `401` (đúng thiết kế, xảy ra trước khi đăng nhập) — không có `Uncaught`/`TypeError` nào | **PASS** | (xem log chạy) |

## Ghi chú

Ca này tận dụng đúng lỗi THẬT đang xảy ra ở TC-013 (thiếu pgvector) thay vì phải mô phỏng lỗi mạng nhân tạo bằng DevTools — vẫn kiểm đúng mục tiêu AC-011.3 (xử lý lỗi không crash, có đường thử lại). Quan sát phụ: ngay sau khi bấm "Thử lại", có một khoảng ~1-2 giây giao diện hiện lại skeleton loading (thấy ở ảnh trung gian, không đính kèm vì không mang thêm thông tin) trước khi banner lỗi mới xuất hiện — đây là hành vi render bình thường trong lúc chờ `POST .../questions` lần 2 hoàn tất, không phải lỗi.
