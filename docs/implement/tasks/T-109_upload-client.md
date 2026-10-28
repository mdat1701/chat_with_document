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
| Trạng thái | In progress (hàng đợi 3 đồng thời + tiến trình thật + dialog trùng tên đã có; còn thiếu khớp ảnh thiết kế và test E2E — xem ghi chú) |

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

- [x] Chọn nhiều tệp qua kéo-thả hoặc input `multiple` → mỗi tệp một request `uploadDocument()` riêng (đúng "mỗi tệp một request" của SADD §2.2.3), **giới hạn 3 đồng thời** qua bộ chạy hàng đợi trong `useUploadQueue.ts` (còn lại ở trạng thái `queued`)
- [x] Một tệp lỗi mạng → `UploadItem.status='failed'`, `errorCode='UPLOAD_NETWORK'`, dòng hiện nút Thử lại; các tệp khác trong hàng đợi tiếp tục không bị ảnh hưởng (AC-004.2) — đọc code xác nhận, **chưa có test tự động mô phỏng lỗi mạng XHR**
- [x] Tệp > `max_file_size_bytes` → `validateFiles()` chặn **trước khi gọi `uploadDocument()`**, không tạo dòng nào trong hàng đợi/danh sách (AC-006.2) — `useUploadQueue.addFiles` gọi `validateFiles` trước khi thêm vào `items`
- [ ] Tệp `.pdf` giả nội dung PNG — vẫn không có kiểm tra phía client (chỉ kiểm `type`/đuôi tệp), dựa vào `415`/magic-bytes từ server như trước
- [x] Đạt hạn mức → `DocumentCounter` (Badge `doc-counter`) chuyển cảnh báo, `UploadDropzone` nhận `disabled` + tooltip lý do (`uiText.quotaReached`)
- [x] Trùng tên → `DuplicateFileDialog` mở khi server trả `409 DUPLICATE_NAME`, xử lý tuần tự (chỉ một hộp thoại tại một thời điểm vì hàng đợi tạm dừng khi có `duplicatePrompt`)
- [x] Nút Hủy khi đang tải — `uploadDocument()` dùng `XMLHttpRequest`, trả `{ promise, abort }`; `useUploadQueue.cancelUpload` gọi `abort()` rồi gỡ khỏi hàng đợi, không để lại dòng
- [x] Bàn phím: vùng dropzone có `role="button"`, `tabIndex`, xử lý `Enter`/`Space`, `aria-label` — giữ nguyên, đúng yêu cầu accessibility cơ bản
- [ ] Giao diện khớp ảnh thiết kế — chưa đối chiếu pixel-by-pixel với `html_design/`; đã đổi màu viền hard-code sang biến token (`.ui-upload-dropzone` dùng `--color-border`) nhưng chưa làm bộ ảnh so sánh
- [x] Sự kiện `document_upload_started`/`document_upload_rejected_client` — `useUploadQueue.ts` gọi `track()` đúng điểm: `document_upload_started{file_size_bucket}` khi `beginUpload`, `document_upload_rejected_client{reason_code}` cho từng tệp bị `validateFiles` từ chối (không kèm tên tệp)

## 8. Định nghĩa Hoàn thành

- [~] 6 AC ở §2 — AC-003.1/AC-004.1/AC-004.2/AC-006.2/AC-007.1 có cơ sở trong code (đọc xác nhận); ER-08 (dialog trùng tên) có component thật nhưng chưa test E2E tự động nào chạy qua CI
- [x] Giới hạn hiển thị/kiểm tra lấy từ `GET /config` — `DocumentLibrary` đọc `useAppConfig()` rồi truyền `max_file_size_bytes`/`max_documents` cho `useUploadQueue`/`validateFiles`, và `max_pages` cho dòng gợi ý trong `UploadDropzone`; không còn hard-code `20*1024*1024`/`50` ở `App.tsx`
- [x] Không ghi nội dung tệp vào Web Storage — xác nhận bằng đọc code (hàng đợi chỉ giữ `File` trong state React/RAM)
- [ ] axe-core — hạ tầng đã có (T-106) nhưng chưa viết test axe riêng cho `UploadDropzone`/`DuplicateFileDialog`
- [x] Toàn bộ chuỗi lỗi lấy từ `messages.vi.ts` (`uiText`) — các chuỗi còn lại hard-code là nhãn nút chung ("Xóa", "Hủy") giống quy ước đã có ở các feature khác, không phải lỗi nghiệp vụ

### Ghi chú triển khai thực tế

Phiên này xây lại gần trọn §5 của task: `frontend/src/features/documents/useUploadQueue.ts`
là hàng đợi FIFO giới hạn 3 request đồng thời (bộ chạy là một `useEffect`
theo dõi `items`/`pausedUntil`/`duplicatePrompt`, không dùng `Promise.all`
không giới hạn như bản cũ). `shared/api/client.ts::uploadDocument()` thay
cho `uploadFile()` cũ — dùng `XMLHttpRequest` để có `upload.onprogress`
(thanh tiến trình thật) và `xhr.abort()` (nút Hủy). `UploadDropzone.tsx`
được làm lại thành component **thuần hiển thị**: chỉ gom `File[]` rồi gọi
`onFilesSelected` do `DocumentLibrary` truyền xuống (chính là
`useUploadQueue().addFiles`, nơi gọi `validateFiles()` **trước khi** thêm
vào hàng đợi, đúng AC-006.2) — không còn tự gọi API trực tiếp trong
`UploadDropzone`, giữ đúng ranh giới DR-04 (chỉ `shared/api`/`shared/analytics`
được `fetch`/`EventSource`/`XMLHttpRequest` trực tiếp, kiểm bằng ESLint
boundaries hiện có).

`DuplicateFileDialog.tsx` (mới) bọc `shared/ui/Dialog`; khi `409
DUPLICATE_NAME` trả về, hàng đợi tạm dừng việc bắt đầu tệp mới cho tới khi
người dùng chọn Thay thế (`?on_duplicate=replace`)/Giữ cả hai
(`?on_duplicate=keep_both`)/Hủy (gỡ khỏi hàng đợi) — khớp §4/ER-08. `429
RATE_LIMITED` tạm dừng toàn hàng đợi theo `Retry-After` (ước lượng từ
`retry_after_seconds` trong `params`) rồi tự tiếp tục.

**Còn thiếu/biết trước (giữ "In progress"):** chưa có bộ ảnh so sánh thiết
kế (`html_design/SCR-02_*`) và chưa có test axe-core/E2E riêng cho luồng
tải lên — cả hai cần một vòng QA/kiểm thử trực quan riêng, ngoài phạm vi
một phiên code. Cũng chưa kiểm tra magic-bytes PDF phía client (vẫn dựa
server trả `415`), đúng như spec cho phép ("dựa hoàn toàn vào server" không
còn đúng kể từ khi `validateFiles` chặn theo `type`/đuôi tệp, nhưng chưa
đọc byte đầu tệp phía trình duyệt).

## 9. Tham chiếu

[`../../design/User_Stories.md`](../../design/User_Stories.md) US-003, US-004, US-006, US-007 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.2.3 (`UploadDropzone`, `DuplicateFileDialog`, `DocumentCounter`), §3.4.3, §3.6.1 (sơ đồ tuần tự tải nhiều tệp), §3.7.1 (vòng đời tài liệu) · [`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (API-04/05) · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.2 (sự kiện) · Ảnh: [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png), [`SCR-02_07_rejected-client.png`](../../design/html_design/SCR-02_07_rejected-client.png), [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png), [`SCR-02_10_duplicate-file.png`](../../design/html_design/SCR-02_10_duplicate-file.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
