# Báo cáo thực thi — TC-010 Xóa tài liệu có xác nhận

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:37:00+07:00 (chạy lại sau khi sửa lỗi CSS danh sách dài) |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Bấm "Xóa" mở hộp thoại xác nhận, có tên tài liệu cụ thể | `DeleteConfirmDialog` hiện: "Xóa tài liệu? Bạn sắp xóa "bulk-1.pdf". Thao tác này không thể hoàn tác." — đúng tên tệp, cảnh báo rõ không thể hoàn tác | **PASS** | [01_hop_thoai_xac_nhan.png](./01_hop_thoai_xac_nhan.png) |
| KQ2 | Có cả nút Hủy và nút Xóa (xác nhận), không xóa nhầm khi chỉ bấm 1 lần ở danh sách | Dialog có 2 nút rõ ràng: "Hủy" (trung tính) và "Xóa" (đỏ, nhấn mạnh hành động phá huỷ) | **PASS** | [01_hop_thoai_xac_nhan.png](./01_hop_thoai_xac_nhan.png) |
| KQ3 | Sau khi xác nhận, tài liệu biến mất khỏi danh sách và bị xóa thật phía server | `DELETE /api/v1/documents/<id>` trả `204`; gọi lại `GET /api/v1/documents` xác nhận `bulk-1.pdf` không còn (`stillThere: false`), tổng số giảm đúng 1 (50 → 49) | **PASS** | `delete_check.json` |

## Ghi chú

Không phát hiện sai lệch.

**Chạy lại sau fix CSS (`.document-list` max-height/overflow, xem `TC-011`):** với 50 tài liệu, hộp thoại xác nhận giờ hiển thị gọn trong một màn hình (danh sách cuộn riêng phía sau overlay) thay vì cần cuộn trang dài để thấy hộp thoại như trước — cải thiện trải nghiệm xác nhận xóa khi thư viện đầy. Không thay đổi kết luận PASS/FAIL.
