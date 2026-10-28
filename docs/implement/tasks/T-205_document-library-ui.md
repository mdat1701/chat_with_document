# T-205 — Thư viện tài liệu (UI): danh sách, trạng thái, bộ đếm, nhãn hết hạn

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-009 (Xem danh sách tài liệu), US-010 (Thấy trạng thái xử lý), US-021 (Nhãn sắp hết hạn) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | Front-end `features/documents` |
| API liên quan | **API-03** `GET /documents`, **API-06** SSE (T-204) |
| Vai trò chính | FE |
| Ước lượng | 3d |
| Phụ thuộc | T-106 (design system, `shared/api`), T-204 (SSE), T-108 (upload API) |
| Trạng thái | In progress (danh sách + xóa cơ bản chạy được, chưa realtime/thiếu trạng thái trực quan) |

## 1. Mục tiêu

Dựng cột trái của màn hình chính (SCR-02): danh sách tài liệu của người dùng với **trạng thái minh bạch**, bộ đếm hạn mức, nhãn sắp hết hạn, và liên kết trạng thái sang ô câu hỏi.

Nguyên tắc UX bắt buộc: trạng thái **luôn có biểu tượng + chữ**, không chỉ phân biệt bằng màu (IX-07 / WCAG 2.1 AA).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-009.1 | *Given* người dùng có tài liệu, *When* mở màn hình chính, *Then* cột trái hiển thị toàn bộ tài liệu của người dùng, sắp xếp theo thời gian tải lên mới nhất, kèm bộ đếm `đã dùng / tối đa`. |
| AC-009.2 | *Given* danh sách có 50 tài liệu, *When* người dùng cuộn, *Then* cuộn mượt và danh sách hiển thị trong ≤ 100 ms. |
| AC-009.3 | *Given* màn hình rộng < 1024px, *When* nhấn nút "Tài liệu", *Then* thư viện mở dạng ngăn trượt (UX-01). |
| AC-009.4 | *Given* danh sách đang tải lần đầu, *When* chưa có dữ liệu, *Then* hiển thị skeleton. |
| AC-010.2 | *Given* mọi tài liệu đều đang xử lý, *Then* ô câu hỏi bị khóa kèm gợi ý và tự mở khi có ít nhất 1 tài liệu ✅ (ES-02). |
| AC-010.3 | *Given* bất kỳ trạng thái nào, *When* hiển thị, *Then* luôn có biểu tượng **và** chữ, không chỉ màu (IX-07); trình đọc màn hình đọc được trạng thái. |
| AC-021.2 | *Given* một tài liệu còn 7 ngày nữa là hết hạn, *When* mở danh sách, *Then* hiển thị nhãn "Sẽ bị xóa sau 7 ngày". |

## 3. Hợp đồng API / giao diện

**API tiêu thụ:**

```http
GET /documents
→ 200 {
  "items": [{
    "id": "3f1c...", "name": "HopDong_DoiTacA.pdf", "size_bytes": 3250000,
    "page_count": 42, "status": "ready", "error_code": null,
    "uploaded_at": "2026-11-20T08:12:00Z", "expires_at": "2027-02-18T08:12:00Z"
  }],
  "used": 12, "max": 50
}
```

**Component cần dựng (SDD §3.2.3):**

| Component | Props chính | Ghi chú |
|---|---|---|
| `DocumentPanel` | — (container, gọi `useDocuments()`) | Lấy dữ liệu + hợp nhất sự kiện SSE |
| `DocumentCounter` | `used`, `max` | Chuyển màu cảnh báo khi `used === max` |
| `DocumentList` | `documents[]` sắp xếp `uploaded_at` giảm dần | — |
| `DocumentItem` | `document`, `onDelete`, `onRetry` | Một hàng |
| `StatusBadge` | `status`, `errorCode?`, `progress?` | Icon + chữ |
| `ExpiryBadge` | `expiresAt` | Hiện khi còn ≤ 7 ngày |

**Bảng trạng thái bắt buộc (SDD §3.7.1):**

| Trạng thái | Biểu tượng + chữ | Màu (token) | Hành động |
|---|---|---|---|
| Uploading | ⏳ + thanh tiến trình "Đang tải lên 45%" | `--color-info` | Hủy |
| Processing | ⏳ (xoay) "Đang xử lý…" | `--color-info` | — |
| Ready | ✅ "Sẵn sàng" + `size` · `page_count` trang | `--color-success` | Xóa |
| Expiring | ⚠ "Sẽ bị xóa sau N ngày" | `--color-warning` | Xóa |
| Failed | ❌ + thông báo theo `error_code` | `--color-danger` | Thử lại (chỉ `UPLOAD_NETWORK`/`INGESTION_FAILED`) · Xóa |

**Ảnh thiết kế tham chiếu:**
[`SCR-02_03_document-statuses.png`](../../design/html_design/SCR-02_03_document-statuses.png) ·
[`SCR-02_04_processing-only.png`](../../design/html_design/SCR-02_04_processing-only.png) ·
[`SCR-02_05_upload-failed-reasons.png`](../../design/html_design/SCR-02_05_upload-failed-reasons.png) ·
[`SCR-02_11_expiring-badge.png`](../../design/html_design/SCR-02_11_expiring-badge.png) ·
[`SCR-02_26_tablet-drawer.png`](../../design/html_design/SCR-02_26_tablet-drawer.png)

## 4. Thay đổi dữ liệu

Không đổi schema. View model phía UI (SDD §3.4.1):

```ts
type DocumentStatus = 'uploading' | 'processing' | 'ready' | 'failed';

interface DocumentVM {
  id: string; name: string; sizeBytes: number; pageCount?: number;
  status: DocumentStatus; uploadProgress?: number; errorCode?: DocErrorCode;
  uploadedAt: string; expiresAt: string;
}
```

Lưu ý: `expiring` **không** phải giá trị `status` từ API — là trạng thái **dẫn xuất** ở UI từ `status === 'ready' && daysUntil(expiresAt) <= 7`.

## 5. Các bước triển khai

1. `useDocuments()` dùng TanStack Query gọi `GET /documents`; `staleTime` ngắn, cache trong RAM (không lưu `localStorage` — CN-06).
2. Hợp nhất sự kiện SSE (T-204) vào cache: khi nhận `status`, `queryClient.setQueryData` cập nhật đúng item theo `id`; nếu `id` chưa có trong cache → `invalidateQueries` để tải lại.
3. `DocumentList` sắp xếp `uploadedAt` giảm dần (API đã sắp, nhưng item mới upload cục bộ phải chèn đúng chỗ).
4. `StatusBadge`: render icon SVG + chuỗi từ `messages.vi.ts`; thêm `aria-label` đầy đủ để NVDA đọc được cả trạng thái lẫn lý do lỗi.
5. Lỗi hiển thị **một dòng** trên hàng tài liệu, chi tiết dài đưa vào `title`/tooltip (mẫu "tiết lộ dần" — SDD §3.8.2).
6. `ExpiryBadge`: tính `daysLeft = differenceInCalendarDays(expiresAt, now)`; hiện khi `0 <= daysLeft <= 7`; định dạng số theo `vi-VN`.
7. `DocumentCounter`: hiển thị `used/max` ở `PanelHeader`; khi `used === max`, chuyển trạng thái cảnh báo và truyền `disabled` xuống `UploadDropzone` kèm tooltip lý do (T-109 đã dựng dropzone).
8. **Liên kết sang ô câu hỏi:** tính `readyCount = documents.filter(d => d.status === 'ready').length`; truyền xuống `ChatPanel` để khóa/mở composer (ES-01/ES-02/ES-03) — logic trạng thái trống hoàn thiện ở T-208.
9. Skeleton khi `isLoading` lần đầu (AC-009.4); **không** hiện skeleton khi refetch nền.
10. Responsive: từ < 1024px chuyển panel thành ngăn trượt có nút "Tài liệu" + lớp phủ (scrim); hoàn thiện chi tiết ở T-405, task này dựng layout cơ bản và breakpoint.
11. Mọi phần tử tương tác có `data-testid` (CN-10): `doc-item`, `doc-delete`, `doc-retry`, `doc-counter`, `doc-list`.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `DOC_NOT_FOUND` | Thao tác trên tài liệu vừa bị xóa ở tab khác | Hiện "Không tìm thấy tài liệu. Tài liệu có thể đã bị xóa." + làm mới danh sách |
| `SESSION_EXPIRED` | Phiên hết hạn khi refetch | `shared/api` chuyển `/login?returnTo=/` (T-107) |
| Mọi `error_code` tài liệu | `status='failed'` | Hiển thị đúng chuỗi trong `messages.vi.ts` theo SDD §3.4.3 — **không** hiện mã lỗi thô cho người dùng |

Trường hợp biên:
- **Danh sách rỗng** → `EmptyState` ES-01 (chi tiết ở T-208).
- **50 tài liệu** → cuộn mượt; nếu cần, dùng virtualization, nhưng đo trước (AC-009.2 chỉ yêu cầu ≤ 100 ms).
- **Tên tệp rất dài** → cắt bằng ellipsis, full text trong `title`.
- **`page_count` null** (tài liệu đang xử lý/lỗi) → không hiển thị "undefined trang".
- **`daysLeft` âm** (quá hạn nhưng job chưa chạy) → hiển thị "Sẽ bị xóa hôm nay", không hiện số âm.

## 7. Kiểm thử bắt buộc

- [ ] Hiển thị đủ 5 trạng thái, mỗi trạng thái có icon và chữ — hiện chỉ hiện chữ trạng thái thô (`doc.status`), không có icon/màu theo trạng thái
- [ ] 50 tài liệu render ≤ 100ms — chưa đo
- [ ] Nhãn hết hạn tại mốc 7 ngày — chưa có logic này trong `DocumentLibrary.tsx`
- [ ] axe-core — chưa cài (xem T-106)
- [ ] Skeleton khi tải lần đầu — chưa có, chỉ render rỗng rồi danh sách
- [ ] Bộ đếm `used/max` — chưa có UI đếm số tài liệu/hạn mức
- [ ] Responsive 900px — chưa kiểm tra

## 8. Định nghĩa Hoàn thành

- [ ] Khớp ảnh thiết kế — chưa đối chiếu
- [ ] Chuỗi hiển thị lấy từ `messages.vi.ts` — chưa, hard-code trong JSX
- [x] Component là presentational, không gọi API trực tiếp bằng `fetch` thô — gọi qua `apiFetch` của `shared/api` (đúng DR-04), nhưng gọi trực tiếp trong component thay vì qua TanStack Query/hook riêng (DR-03 "component con thuần" chưa tách)
- [x] Không lưu tên tệp/nội dung vào Web Storage — xác nhận bằng đọc code
- [x] Có `data-testid` cho `doc-item`/`doc-delete`/`empty-state`; dùng được bàn phím vì là phần tử `<button>`/`<ul>` chuẩn

### Ghi chú triển khai thực tế

`DocumentLibrary.tsx` là bản tối thiểu: tải danh sách một lần khi mount
(`GET /documents`), hiện trạng thái text thô, xóa bằng `window.confirm()`
gốc trình duyệt rồi gọi lại `DELETE /documents/{id}`. Thiếu so với đặc tả:
icon/màu theo trạng thái, đếm `used/max`, skeleton, nhãn sắp hết hạn,
responsive, và **không tự cập nhật qua SSE** (T-204 đã có backend nhưng
chưa có `sseClient` ở FE — xem ghi chú T-106/T-204).

**Lệch hợp đồng API đáng chú ý:** task này (bảng thuộc tính) tham chiếu
API-03 trả `{items, used, max}`, nhưng `GET /api/v1/documents` thật
(`app/api/routers/documents.py::list_documents`) trả thẳng một **mảng**
`list[dict]`, không bọc trong `{items, used, max}`. FE hiện khớp đúng với
backend thật (`apiFetch<DocumentItem[]>`), nhưng khác với hợp đồng SADD đã
mô tả — cần quyết định giữ nguyên dạng mảng (sửa tài liệu SADD) hay đổi
backend để bọc `{items, used, max}` (phục vụ bộ đếm hạn mức ở UI).

**`window.confirm()` thay cho hộp thoại xác nhận riêng (T-208)** — nghĩa là
kịch bản E2E mẫu ở T-504 dùng `page.getByTestId('confirm-delete')` **sẽ
không tìm thấy phần tử nào** vì không có dialog DOM thật, chỉ có hộp thoại
gốc trình duyệt. Đây là điểm cần đồng bộ khi làm T-208.

## 9. Tham chiếu

- SADD v0.3 §2.4.2 (API-03 trả `{items, used, max}`), §3.1.2 (chỉ mục `(owner_id, uploaded_at DESC)`)
- SDD UI/UX v0.3 §3.2.2 (bố cục SCR-02), §3.2.3 (cây thành phần), §3.7.1 (bảng trạng thái), §3.8.1 (design token)
- User Stories v0.4 — US-009, US-010, US-021
- Ảnh: `docs/design/html_design/SCR-02_03`, `_04`, `_05`, `_11`, `_26`
