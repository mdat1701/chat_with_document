# Ca kiểm thử giao diện (System/E2E) — Quy ước chung

Thư mục này chứa các ca kiểm thử giao diện được tách ra từ
[`../test_plan.md`](../test_plan.md) §4.1 (ma trận truy xuất User Story →
AC → Task → Cấp độ kiểm thử → Trạng thái hiện tại), mỗi ca một tệp
`TC-###_slug.md`. Các ca này dành cho một **agent thực thi** (trình duyệt
tự động hoặc người) chạy thủ công/bán tự động trên ứng dụng đang chạy
thật, khác với test tự động trong `backend/tests` hay `frontend/src/**/*.test.tsx`
(vốn đã chạy trong CI).

## 1. Cấu hình URL (không hard-code)

Mọi ca kiểm thử dùng 2 biến cấu hình, agent thực thi phải nhận giá trị
này từ môi trường chạy (biến môi trường hoặc tham số truyền vào), **không
được tự ý hard-code URL khác trong lúc thực thi**:

| Biến | Mặc định | Dùng khi |
|---|---|---|
| `TEST_BASE_URL` | `http://localhost:5173` | URL gốc frontend (Vite dev server, `npm run dev`) — hầu hết các ca |
| `TEST_API_BASE_URL` | `http://localhost:8000` | URL gốc backend (`uvicorn app.api.main:app`) — chỉ các ca cần gọi thẳng API hoặc quan sát tab Network |

Nếu `TEST_BASE_URL` không truy cập được (ứng dụng chưa chạy, hoặc hạ tầng
phụ thuộc — Docker/IdP/LLM — chưa sẵn sàng, xem
[`test_plan.md` §11](../test_plan.md#11-environmental-needs)), ca kiểm
thử phải được báo cáo **BLOCKED**, không được coi là PASS/FAIL.

## 2. Quy ước thư mục/tên tệp ca kiểm thử

- Tên tệp: `TC-###_slug-tieng-viet-khong-dau.md` (ví dụ `TC-004_upload-mot-pdf-hop-le.md`).
- Mỗi tệp là một ca kiểm thử độc lập, có thể giao cho agent chạy riêng lẻ.

## 3. Quy ước artifact — `./test_reports/`

Khi agent thực thi ca `TC-###_slug`, **toàn bộ** sản phẩm của lần chạy đó
(báo cáo + mọi ảnh chụp màn hình) phải được lưu vào đúng một thư mục
riêng, đặt tên **trùng với tên ca kiểm thử** (không phần mở rộng `.md`),
nằm dưới `./test_reports/` ở gốc repo:

```
./test_reports/
  TC-004_upload-mot-pdf-hop-le/
    report.md
    01_trang-thu-vien-rong.png
    02_sau-khi-chon-tep.png
    03_trang-thai-processing.png
    04_trang-thai-ready.png
```

Quy tắc:
- Tạo thư mục nếu chưa có; **không** ghi đè/ghi lẫn vào thư mục của ca
  kiểm thử khác.
- Ảnh chụp đặt tên theo thứ tự thực hiện, 2 chữ số đầu + mô tả ngắn bước
  đó (`01_...png`, `02_...png`, …), định dạng `.png`.
- Báo cáo đặt tên cố định `report.md` trong đúng thư mục ca đó.
- Nếu chạy lại nhiều lần cùng một ca, có thể ghi đè `report.md`/ảnh cũ
  (đây là báo cáo của *lần chạy gần nhất*) — việc giữ lịch sử nhiều lần
  chạy không nằm trong quy ước này.
- Thư mục `test_reports/` không được commit vào Git (đã thêm vào
  `.gitignore` ở gốc repo, chỉ giữ `.gitkeep`) vì đây là sản phẩm phát
  sinh khi chạy test, không phải mã nguồn hay tài liệu thiết kế.

## 4. Mẫu `report.md`

Mỗi `report.md` PHẢI theo đúng cấu trúc sau:

```markdown
# Báo cáo thực thi — TC-### <Tên ca>

| Trường | Giá trị |
|---|---|
| Thời gian chạy | <ISO 8601, ví dụ 2026-10-29T10:15:00+07:00> |
| URL đã test | <giá trị TEST_BASE_URL/TEST_API_BASE_URL thực tế đã dùng> |
| Môi trường | <trình duyệt + phiên bản nếu biết, hệ điều hành, hoặc "không xác định" nếu agent không có quyền truy cập thông tin này> |
| Kết luận chung | PASS / FAIL / BLOCKED |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi (trích từ ca kiểm thử) | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | ... | ... | PASS | [01_....png](./01_....png) |
| KQ2 | ... | ... | FAIL | [03_....png](./03_....png) |

## Ghi chú / Sai lệch

- <mọi khác biệt so với kỳ vọng, lỗi console, response lỗi bất thường từ
  API, hoặc lý do BLOCKED nếu có — để trống nếu không có gì bất thường>
```

**Quy tắc bắt buộc khi viết `report.md`:**
- Chấm PASS/FAIL **riêng từng dòng** "Kết quả mong đợi" của ca kiểm thử,
  không gộp thành một kết luận duy nhất che giấu chi tiết.
- **Không** được kết luận PASS cho một tiêu chí nếu chưa có ảnh chụp màn
  hình thực sự chứng minh đã quan sát đúng trạng thái đó. Suy luận logic
  ("chắc là đúng vì code trông đúng") không thay thế được việc quan sát
  giao diện thật.
- Nếu không vào được `TEST_BASE_URL`, hoặc thiếu tiền điều kiện (tài
  khoản, dữ liệu mẫu, hạ tầng — ví dụ IdP thật cho các ca đăng nhập),
  "Kết luận chung" phải là **BLOCKED** kèm lý do cụ thể trong "Ghi chú" —
  không được suy ra PASS/FAIL khi chưa thực sự chạy được.

## 5. Danh sách ca kiểm thử

| Mã | Tên | User Story | Ưu tiên |
|---|---|---|---|
| [TC-001](TC-001_dang-nhap-oidc-thanh-cong.md) | Đăng nhập OIDC thành công | US-001 | P0 |
| [TC-002](TC-002_man-hinh-chua-cap-quyen.md) | Màn hình "chưa được cấp quyền" | US-001 | P0 |
| [TC-003](TC-003_co-lap-du-lieu-giua-2-nguoi-dung.md) | Cô lập dữ liệu giữa 2 người dùng | US-002 | P0 |
| [TC-004](TC-004_upload-mot-pdf-hop-le.md) | Tải lên 1 PDF hợp lệ | US-003 | P0 |
| [TC-005](TC-005_upload-tep-khong-phai-pdf-bi-tu-choi.md) | Tải lên tệp không phải PDF — bị chặn phía client | US-003/US-005 | P0 |
| [TC-006](TC-006_upload-tep-gia-pdf-bi-tu-choi.md) | Tải lên tệp giả PDF (sai magic-bytes) | US-005 | P0 |
| [TC-007](TC-007_upload-nhieu-tep-dong-thoi.md) | Tải nhiều tệp đồng thời | US-004 | P0 |
| [TC-008](TC-008_upload-tep-vuot-kich-thuoc.md) | Tải tệp vượt kích thước tối đa | US-006 | P0 |
| [TC-009](TC-009_dat-han-muc-tai-lieu.md) | Đạt hạn mức số tài liệu | US-007 | P0 |
| [TC-010](TC-010_xoa-tai-lieu-co-xac-nhan.md) | Xóa tài liệu có xác nhận | US-008 | P0 |
| [TC-011](TC-011_xem-danh-sach-tai-lieu.md) | Xem danh sách tài liệu | US-009 | P1 |
| [TC-012](TC-012_trang-thai-tai-lieu-realtime.md) | Trạng thái tài liệu cập nhật realtime | US-010 | P1 |
| [TC-013](TC-013_dat-cau-hoi-nhan-tra-loi-co-trich-dan.md) | Đặt câu hỏi, nhận trả lời kèm trích dẫn | US-011 | P0 |
| [TC-014](TC-014_tong-hop-da-tai-lieu.md) | Tổng hợp câu trả lời từ nhiều tài liệu | US-012 | P0 |
| [TC-015](TC-015_cau-hoi-khong-co-dap-an.md) | Câu hỏi không có đáp án trong tài liệu | US-013 | P0 |
| [TC-016](TC-016_trich-dan-dung-ten-tai-lieu-nguon.md) | Trích dẫn đúng tên tài liệu nguồn | US-014 | P0 |
| [TC-017](TC-017_trich-dan-co-so-trang.md) | Trích dẫn có kèm số trang | US-015 | P1 |
| [TC-018](TC-018_hoi-dap-tieng-anh.md) | Hỏi đáp bằng tiếng Anh | US-017 | P0 |
| [TC-019](TC-019_loi-tra-loi-va-thu-lai.md) | Lỗi khi trả lời và luồng Thử lại | US-011 | P0 |
| [TC-020](TC-020_khong-lo-noi-dung-qua-network-analytics.md) | Không lộ nội dung qua Network/analytics | US-020 | P0 |
| [TC-021](TC-021_cap-quyen-qua-cli.md) | Cấp quyền qua CLI phản ánh đúng khi đăng nhập | US-023 | P1 |

## 6. Tham chiếu

- [`../test_plan.md`](../test_plan.md) — Kế hoạch kiểm thử tổng thể (IEEE 829)
- [`../../design/User_Stories.md`](../../design/User_Stories.md) — Mô tả đầy đủ AC
- [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) — Màn hình, trạng thái, `data-testid`
- [`../../implement/tasks/README.md`](../../implement/tasks/README.md) — Trạng thái 47 task
