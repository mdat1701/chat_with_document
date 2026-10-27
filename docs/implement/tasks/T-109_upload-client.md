# T-109 — Giao diện tải tài liệu lên

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-003 (tải 1 PDF), US-004 (chọn/kéo thả nhiều PDF) |
| Epic | EP-02 — Quản lý tài liệu |
| Module (SDD §3.1) | `features/documents` |
| API liên quan | API-04/05 `POST /documents`, API-02 `GET /config` |
| Vai trò chính | FE |
| Ước lượng | 3d |
| Phụ thuộc | T-106 (nền tảng FE), T-105 (`GET /config`), T-108 (API tải lên) |
| Trạng thái | To do |

## 1. Mục tiêu

Hiện thực vùng tải lên và hàng đợi tải lên phía trình duyệt: kéo-thả hoặc chọn nhiều tệp, kiểm tra giới hạn **trước khi truyền** để không bắt người dùng chờ vô ích (AC-006.2), tối đa 3 tệp tải đồng thời, hiển thị tiến trình từng tệp và xử lý trùng tên.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-003.1 | Tải PDF hợp lệ → xuất hiện trong danh sách với trạng thái "Đang xử lý" |
| AC-004.1 | Chọn 10 tệp PDF hợp lệ cùng lúc → cả 10 xuất hiện, mỗi tệp có trạng thái riêng |
| AC-004.2 | Trong 10 tệp có 1 tệp lỗi → 9 "Sẵn sàng", 1 "Lỗi"; tệp lỗi **không** ảnh hưởng tệp còn lại |
| AC-006.2 | Tệp > 20 MB → từ chối **trước khi truyền tệp đi**, hiển thị "Tệp vượt quá 20 MB" và **không tạo dòng nào trong danh sách** |
| AC-007.1 | Đạt tối đa 50 tài liệu → thông báo "Đã đạt tối đa 50 tài liệu. Xóa bớt tài liệu để tải thêm." |
| ER-08 | Tệp trùng tên → hộp thoại "Thay thế tệp cũ" / "Giữ cả hai" |

## 3. Giao diện — component và ảnh thiết kế

| Component | Props / trạng thái chính | Ảnh thiết kế |
|---|---|---|
| `UploadDropzone` | `disabled` (khi đạt hạn mức hoặc ngoại tuyến), `onFilesSelected(files)`, `disabledReason` cho tooltip | [`SCR-02_01_empty-first-login.png`](../../design/html_design/SCR-02_01_empty-first-login.png), [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png) |
| `UploadQueue` (hook/store) | `queue: UploadItem[]`, tối đa 3 tệp `in-flight` | [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png) |
| `DocumentItem` (trạng thái uploading) | `progress: 0–100`, nút Hủy | [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png) |
| `RejectedFilesNotice` | Danh sách tệp bị từ chối tại trình duyệt kèm lý do | [`SCR-02_07_rejected-client.png`](../../design/html_design/SCR-02_07_rejected-client.png) |
| `DuplicateFileDialog` | `fileName`, `onReplace`, `onKeepBoth`, `onCancel` | [`SCR-02_10_duplicate-file.png`](../../design/html_design/SCR-02_10_duplicate-file.png) |
| `DocumentCounter` | `used`, `max` (đỏ khi `used >= max`) | [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png) |

```ts
type UploadItem = {
  localId: string;                 // id tạm phía client trước khi có document_id
  file: File;
  status: 'queued' | 'uploading' | 'done' | 'failed' | 'canceled';
  progress: number;                // 0–100
  documentId?: string;             // có sau khi server trả 201
  errorCode?: 'UPLOAD_NETWORK' | 'DUPLICATE_NAME' | 'FILE_TOO_LARGE' | 'QUOTA_EXCEEDED' | 'FILE_NOT_PDF';
};
```

## 4. Thay đổi dữ liệu

Không có thay đổi CSDL. Trạng thái hàng đợi nằm trong Zustand (RAM), **không** ghi vào Web Storage (nội dung tệp là dữ liệu nhạy cảm — CN-06). Sau khi một tệp nhận `201`, dòng tương ứng chuyển sang theo dõi bằng dữ liệu máy chủ (`GET /documents` + SSE ở T-204).

## 5. Các bước triển khai

1. **`UploadDropzone`**
   - Hỗ trợ kéo-thả (`onDragEnter/Over/Leave/Drop`) và click mở hộp chọn tệp (`<input type="file" multiple accept="application/pdf">`).
   - Bàn phím: `Enter` / `Space` khi focus mở hộp chọn tệp (IX-01); vùng có `role="button"`, `tabIndex=0`, `aria-label` mô tả rõ.
   - Hiển thị dòng gợi ý giới hạn lấy **từ `GET /config`**: "PDF có văn bản · tối đa 20 MB · 300 trang mỗi tệp".
   - Dưới 1024px: ẩn kéo-thả, chỉ còn nút chọn tệp (vùng chạm ≥ 44×44px).
   - Khi `disabled` (đạt hạn mức / ngoại tuyến): giảm độ tương phản + **tooltip bắt buộc** nêu lý do (yêu cầu §2.5 của SDD: nút bị vô hiệu luôn có tooltip giải thích).

2. **Kiểm tra phía client trước khi gửi** (`shared/validation.validateFiles`)
   - Thứ tự kiểm tra: phần mở rộng/`type` ≠ PDF → `FILE_NOT_PDF`; `size > max_file_size_bytes` → `FILE_TOO_LARGE`; `used + số tệp hợp lệ > max_documents` → `QUOTA_EXCEEDED` cho phần vượt.
   - Tệp bị từ chối: hiển thị trong `RejectedFilesNotice` **và tuyệt đối không tạo dòng trong `DocumentList`** (AC-006.2) — đây là lỗi hay gặp, cần test riêng.
   - Phát sự kiện `document_upload_rejected_client{reason_code}` cho mỗi tệp bị từ chối (PRD §5.2) — **không** kèm tên tệp.

3. **`UploadQueue`**
   - Hàng đợi FIFO, tối đa **3 request đồng thời**; tệp còn lại ở trạng thái `queued`.
   - Mỗi tệp là **một request `POST /documents` riêng** (khớp thiết kế "mỗi tệp một job ingestion độc lập" của SADD §2.2.3) — không gộp nhiều tệp vào một request.
   - Dùng `XMLHttpRequest` (hoặc `fetch` + `ReadableStream`) để có `upload.onprogress` vẽ thanh tiến trình %.
   - Phát `document_upload_started` khi bắt đầu mỗi tệp.

4. **Xử lý phản hồi từng tệp**

   | Phản hồi | Hành vi UI |
   |---|---|
   | `201` | `UploadItem.status='done'`, gắn `documentId`; dòng chuyển sang "Đang xử lý", từ đây trạng thái do SSE (T-204) điều khiển |
   | `409 DUPLICATE_NAME` | Mở `DuplicateFileDialog`; chọn Thay thế → gửi lại `?on_duplicate=replace`; Giữ cả hai → `?on_duplicate=keep_both`; Hủy → bỏ tệp khỏi hàng đợi |
   | `413` / `415` / `422` | Hiện lỗi tương ứng từ `messages.vi.ts`; **không** giữ dòng rác trong danh sách |
   | Mất mạng / timeout | `status='failed'`, `errorCode='UPLOAD_NETWORK'`, dòng hiển thị "Lỗi — Mất kết nối" kèm nút **Thử lại**; các tệp khác trong hàng đợi **vẫn chạy tiếp** |
   | `429 RATE_LIMITED` | Hiện thông báo kèm thời gian chờ từ `Retry-After`; tạm dừng hàng đợi |

5. **Nút Hủy** cho tệp đang `uploading`: `xhr.abort()`, gỡ khỏi hàng đợi, không để lại dòng nào.

6. **`DocumentCounter`**: cập nhật lạc quan `used + 1` sau mỗi `201`, rồi đối chiếu lại bằng `GET /documents`; chuyển màu cảnh báo khi `used >= max` (ảnh `SCR-02_08`).

7. **Khả năng truy cập**: mỗi dòng tải lên thông báo trạng thái qua `aria-live="polite"`; thanh tiến trình có `role="progressbar"` kèm `aria-valuenow`.

8. **Ngoại tuyến (NE-03)**: khi `navigator.onLine === false`, khóa vùng tải lên và hiện `OfflineBanner` (hoàn thiện ở T-405); hàng đợi tạm dừng, không mất tệp đang chờ.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi (SDD §3.4.3) | Khi nào | Hành vi UI |
|---|---|---|
| `FILE_NOT_PDF` | Client: sai `type`/đuôi · Server: sai magic bytes | "Chỉ hỗ trợ tệp PDF." — không tạo dòng |
| `FILE_TOO_LARGE` | Client: `size > DF-01` (chặn trước khi gửi) | "Tệp vượt quá 20 MB. Hãy nén hoặc tách tệp rồi tải lại." |
| `QUOTA_EXCEEDED` | Client ước lượng vượt DF-02, hoặc server trả 422 | "Đã đạt tối đa 50 tài liệu. Xóa bớt tài liệu để tải thêm." |
| `DUPLICATE_NAME` | Server 409 | Mở `DuplicateFileDialog` |
| `UPLOAD_NETWORK` | Mất kết nối khi đang truyền | Dòng "Lỗi — Mất kết nối" + **Thử lại** · Xóa |
| `RATE_LIMITED` `[D-05]` | Server 429 | Thông báo chờ, tạm dừng hàng đợi |

**Trường hợp biên:**
- Chọn 60 tệp khi chỉ còn 2 chỗ → client chỉ xếp hàng 2 tệp đầu và báo rõ số tệp bị từ chối do hạn mức (không gửi 60 request rồi nhận 58 lỗi).
- Tải lại trang khi đang có tệp `uploading` → các upload đang dở **mất** (không khôi phục được); tệp đã nhận `201` vẫn tiếp tục xử lý ở server và hiện lại đúng trạng thái sau khi `GET /documents` (NE-09).
- Kéo thả thư mục hoặc tệp 0 byte → lọc bỏ ở bước validate, báo lý do rõ ràng.
- Hai tệp **cùng tên** trong một lần chọn → tệp thứ hai sẽ nhận 409 từ server sau khi tệp đầu được tạo; hộp thoại trùng tên xử lý tuần tự, không mở chồng nhiều hộp thoại.

## 7. Kiểm thử bắt buộc

- [ ] Chọn 10 tệp hợp lệ → 10 dòng xuất hiện, tối đa 3 request chạy đồng thời tại mọi thời điểm (kiểm tra bằng network mock) (AC-004.1)
- [ ] Một tệp trong lô gặp lỗi mạng → dòng đó "Lỗi — Mất kết nối" + Thử lại, 9 dòng còn lại hoàn tất bình thường (AC-004.2)
- [ ] Tệp 25 MB → báo lỗi ngay, **không** có request mạng nào được gửi và **không** có dòng nào xuất hiện rồi biến mất (AC-006.2)
- [ ] Tệp `.pdf` giả (nội dung PNG) → bị chặn ở client hoặc nhận 415 và hiển thị đúng thông báo
- [ ] Đạt 50/50 tài liệu → vùng tải lên bị khóa, tooltip giải thích, bộ đếm chuyển màu cảnh báo (AC-007.1)
- [ ] Trùng tên → hộp thoại hiện đúng tên tệp; "Giữ cả hai" tạo tài liệu `… (2).pdf`; "Thay thế" thay bản cũ; `Esc` đóng hộp thoại
- [ ] Nhấn Hủy khi đang tải → request bị abort, dòng biến mất
- [ ] Bàn phím: Tab tới vùng tải lên, `Enter` mở hộp chọn tệp; trình đọc màn hình đọc được tiến trình
- [ ] Giao diện khớp ảnh thiết kế ở 1280px và 1024px; ở 900px dùng được nút chọn tệp
- [ ] Sự kiện `document_upload_started` và `document_upload_rejected_client{reason_code}` phát đúng, **không** chứa tên tệp

## 8. Định nghĩa Hoàn thành

- [ ] 6 AC ở §2 đạt, có test E2E (Playwright) cho AC-004.1, AC-004.2 và AC-006.2
- [ ] Mọi giới hạn hiển thị và kiểm tra đều lấy từ `GET /config`, không hard-code
- [ ] Không có nội dung tệp nào được ghi vào Web Storage/IndexedDB
- [ ] axe-core không lỗi nghiêm trọng trên các trạng thái tải lên
- [ ] Toàn bộ chuỗi lấy từ `messages.vi.ts`

## 9. Tham chiếu

[`../../design/User_Stories.md`](../../design/User_Stories.md) US-003, US-004, US-006, US-007 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.2.3 (`UploadDropzone`, `DuplicateFileDialog`, `DocumentCounter`), §3.4.3, §3.6.1 (sơ đồ tuần tự tải nhiều tệp), §3.7.1 (vòng đời tài liệu) · [`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (API-04/05) · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.2 (sự kiện) · Ảnh: [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png), [`SCR-02_07_rejected-client.png`](../../design/html_design/SCR-02_07_rejected-client.png), [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png), [`SCR-02_10_duplicate-file.png`](../../design/html_design/SCR-02_10_duplicate-file.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
