# Báo cáo thực thi — TC-009 Đạt hạn mức số tài liệu

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:35:00+07:00 (chạy lại sau khi sửa lỗi CSS danh sách dài — xem Ghi chú) |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004. Hạn mức 50/50 đạt được bằng cách chèn thẳng tài liệu `ready` vào Postgres (bỏ qua việc tải thật từng tệp cho nhanh — không ảnh hưởng tới mục tiêu kiểm thử: hành vi UI khi *đã* đạt hạn mức) |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Bộ đếm hiển thị cảnh báo khi đạt hạn mức | Bộ đếm hiển thị "50/50" với màu cam cảnh báo (khác màu trung tính khi chưa đạt) | **PASS** | [01_da_dat_han_muc.png](./01_da_dat_han_muc.png) |
| KQ2 | Vùng tải lên bị vô hiệu hoá kèm lý do | `UploadDropzone` có `aria-disabled="true"` (xác nhận qua `quota_check.json`), giao diện hiển thị mờ | **PASS** | [01_da_dat_han_muc.png](./01_da_dat_han_muc.png), `quota_check.json` |
| KQ3 | Vẫn chặn đúng nếu cố ép chọn tệp qua input ẩn | Chọn tệp hợp lệ qua `input[type=file]` vẫn bị `validateFiles()` chặn (`reasonCode=QUOTA_EXCEEDED`) — `NETWORK_LOG` xác nhận không có `POST /api/v1/documents` nào phát sinh | **PASS** | [02_sau_khi_thu_tai_them.png](./02_sau_khi_thu_tai_them.png) |
| KQ4 | Thông báo lỗi rõ ràng, có hướng dẫn | "vuot-han-muc-...pdf: Đã đạt tối đa số tài liệu. Xóa bớt tài liệu để tải thêm." | **PASS** | [02_sau_khi_thu_tai_them.png](./02_sau_khi_thu_tai_them.png) |

## Ghi chú

Không phát hiện sai lệch. Client-side quota check (`validateFiles`, T-109) hoạt động nhất quán dù ép chọn tệp qua input ẩn (bỏ qua việc dropzone bị `aria-disabled` ở lớp UI) — xác nhận kiểm tra hạn mức nằm ở tầng logic (`useUploadQueue`), không chỉ ở việc khoá nút bấm.

**Chạy lại sau fix CSS (`.document-list` max-height/overflow, xem `TC-011`):** ảnh chụp lần này (`01_da_dat_han_muc.png`, `02_sau_khi_thu_tai_them.png`) cho thấy danh sách 50 tài liệu giờ cuộn gọn trong khung cố định thay vì đẩy cả trang dài hơn 3700px như lần chạy trước — banner cảnh báo hạn mức và nút "Xóa" vẫn hiển thị đầy đủ, không bị khung cuộn che khuất. Không có thay đổi nào về kết luận PASS/FAIL của các KQ, chỉ cải thiện bằng chứng trực quan.
