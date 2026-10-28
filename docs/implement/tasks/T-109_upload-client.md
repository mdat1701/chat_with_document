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
| Trạng thái | In progress (chỉ có dropzone cơ bản, thiếu hàng đợi/tiến trình/dialog trùng tên) |

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

- [x] Chọn nhiều tệp qua kéo-thả hoặc input `multiple` → mỗi tệp một `uploadFile()` riêng (đúng "mỗi tệp một request" của SADD §2.2.3) — nhưng **không giới hạn 3 đồng thời**, tất cả chạy song song cùng lúc qua `Promise.all`
- [ ] Một tệp lỗi mạng → dòng "Lỗi — Mất kết nối" + Thử lại, các tệp khác tiếp tục (AC-004.2) — **chưa có UI trạng thái từng dòng/`UploadItem`**, lỗi hiện chỉ ném `ApiError`, chưa bắt hiển thị
- [ ] Tệp 25 MB → báo lỗi ngay, không gửi request nào (AC-006.2) — **chưa đạt**: `UploadDropzone` gọi `uploadFile()` trực tiếp, không gọi `validateFiles()` trước; file quá khổ vẫn được gửi lên server (server sẽ từ chối đúng, nhưng client không chặn trước như spec yêu cầu)
- [ ] Tệp `.pdf` giả nội dung PNG — không có kiểm tra phía client, dựa hoàn toàn vào 415 từ server
- [ ] Đạt 50/50 tài liệu → khóa vùng tải lên — chưa có `DocumentCounter`/khóa theo hạn mức ở FE
- [ ] Trùng tên → `DuplicateFileDialog` — **chưa có component này**
- [ ] Nút Hủy khi đang tải — chưa có (không dùng `XMLHttpRequest`/`AbortController`, không có thanh tiến trình)
- [x] Bàn phím: vùng dropzone có `role="button"`, `tabIndex`, xử lý `Enter`/`Space`, `aria-label` — đúng yêu cầu accessibility cơ bản
- [ ] Giao diện khớp ảnh thiết kế — chưa đối chiếu, màu viền hard-code (`#b8c5d9`) thay vì design token
- [ ] Sự kiện `document_upload_started`/`document_upload_rejected_client` — hạ tầng `track()` có sẵn (T-404) nhưng **chưa có lời gọi nào** trong `UploadDropzone.tsx`

## 8. Định nghĩa Hoàn thành

- [ ] 6 AC ở §2 — chỉ AC-004.1 (chọn nhiều tệp, mỗi tệp một request) có cơ sở; AC-004.2, AC-006.2, AC-007.1 chưa đạt ở phía client
- [ ] Giới hạn hiển thị/kiểm tra lấy từ `GET /config` — chưa (hard-code "tối đa 20 MB" trong text tĩnh, `App.tsx` hard-code `20*1024*1024`/`50` khi gọi `validateFiles`)
- [x] Không ghi nội dung tệp vào Web Storage — xác nhận bằng đọc code (không có logic lưu trữ)
- [ ] axe-core — chưa cài (xem T-106)
- [ ] Toàn bộ chuỗi lấy từ `messages.vi.ts` — chưa, chuỗi hard-code trong JSX

### Ghi chú triển khai thực tế

`UploadDropzone.tsx` hiện là một **dropzone tối thiểu**: kéo-thả + chọn tệp
+ gọi `uploadFile()` (từ `shared/api/client.ts`) trực tiếp cho mỗi tệp, có
hỗ trợ bàn phím cơ bản. Đây là một phần nhỏ của đặc tả gốc — phần lớn §5
(hàng đợi FIFO giới hạn 3 đồng thời, thanh tiến trình `XMLHttpRequest`,
`DuplicateFileDialog`, nút Hủy/abort, `DocumentCounter`, khóa khi hết hạn
mức, chặn phía client trước khi gửi bằng `validateFiles`) **chưa được xây
dựng**. `shared/validation/files.ts::validateFiles` đã tồn tại như một hàm
thuần nhưng **chưa được gọi** trước khi upload trong `UploadDropzone.tsx` —
nó chỉ được gọi rời rạc trong `App.tsx` cho mục đích khác, không chặn
request thật.

Giữ nguyên trạng thái **"In progress"** ở mức khung sườn ban đầu — cần một
vòng làm việc riêng để hoàn thiện `UploadQueue`, dialog trùng tên, và gọi
`validateFiles` trước khi upload để đạt AC-006.2.

## 9. Tham chiếu

[`../../design/User_Stories.md`](../../design/User_Stories.md) US-003, US-004, US-006, US-007 · [`../../design/SDD_UI_UX_Blueprint.md`](../../design/SDD_UI_UX_Blueprint.md) §3.2.3 (`UploadDropzone`, `DuplicateFileDialog`, `DocumentCounter`), §3.4.3, §3.6.1 (sơ đồ tuần tự tải nhiều tệp), §3.7.1 (vòng đời tài liệu) · [`../../requirements/SADD.md`](../../requirements/SADD.md) §2.4.2 (API-04/05) · [`../../requirements/PRD.md`](../../requirements/PRD.md) §5.2 (sự kiện) · Ảnh: [`SCR-02_02_uploading-multiple.png`](../../design/html_design/SCR-02_02_uploading-multiple.png), [`SCR-02_07_rejected-client.png`](../../design/html_design/SCR-02_07_rejected-client.png), [`SCR-02_08_quota-reached.png`](../../design/html_design/SCR-02_08_quota-reached.png), [`SCR-02_10_duplicate-file.png`](../../design/html_design/SCR-02_10_duplicate-file.png) · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
