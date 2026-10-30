# Báo cáo thực thi — TC-011 Xem danh sách tài liệu

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:38:00+07:00 (chạy lại sau khi sửa lỗi CSS danh sách dài) |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 (49 tài liệu thật trong Postgres cho owner A tại thời điểm chạy) |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Bằng chứng |
|---|---|---|---|---|
| KQ1 | Danh sách hiển thị đủ, đúng số lượng tài liệu của người dùng | 49 phần tử `[data-testid="doc-item"]` có trong DOM (một phần hiển thị trực tiếp, phần còn lại cuộn được trong khung `.document-list` sau khi sửa CSS — xem mục dưới), khớp đúng `GET /api/v1/documents` trả về 49 bản ghi | **PASS** | [01_danh_sach_tai_lieu.png](./01_danh_sach_tai_lieu.png), `list_check.json` |
| KQ2 | Bộ đếm số lượng hiển thị đúng | `doc-counter` hiển thị "49/50" — khớp chính xác số liệu thật từ API | **PASS** | `list_check.json` |

## Lỗi UI thật phát hiện và đã sửa (phát hiện khi xem lại ảnh chụp của TC-009/TC-010)

`.document-list` (`frontend/src/shared/tokens/global.css`) không có `max-height`/`overflow` — với 49-50 tài liệu, `<ul data-testid="doc-list">` cao dần **đẩy luôn cả trang xuống** (ảnh TC-009/010 cao hơn 3700px) thay vì cuộn riêng trong khung thư viện. Đây là lỗi CSS thuần (thiếu style), không phải thiếu phân trang/API — `GET /api/v1/documents` vẫn trả đúng toàn bộ danh sách trong một lần gọi như thiết kế (hạn mức tối đa 50 tài liệu không cần phân trang thật).

**Đã sửa:** thêm `max-height: 60vh; overflow-y: auto;` vào `.document-list`. Xác nhận bằng đo trực tiếp DOM sau khi sửa: `scrollHeight=3341px` (nội dung thật) vs `clientHeight=480px` (= 60vh ở viewport 800px) với `overflowY=auto` — danh sách cuộn riêng bên trong, chiều cao tổng của trang giảm từ hơn 3700px xuống còn `857px`. Xác nhận bằng `tsc`, `eslint`, `prettier`, `vitest` (`DocumentLibrary.test.tsx` 7/7 vẫn pass).

Phân trang/virtual scroll thật chỉ cần thiết nếu hạn mức tài liệu tăng vượt quá ~100 (ghi chú để lại trong code).

## Ghi chú

Chưa đo được AC-009.2 (hiệu năng cuộn danh sách ≤100ms với 50 tài liệu) — ngoài phạm vi công cụ chụp ảnh/kiểm tra DOM đơn giản của các ca này, cần công cụ đo hiệu năng chuyên dụng (Performance API/Lighthouse).
