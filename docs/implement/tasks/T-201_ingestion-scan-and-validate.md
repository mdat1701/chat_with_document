# T-201 — Pipeline ingestion bước 1–2: quét mã độc & kiểm tra cấu trúc PDF

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-003 (Tải một tệp PDF lên), US-005 (Được báo rõ khi tệp không xử lý được) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `ingestion` (chạy ở worker) |
| API liên quan | — (tiêu thụ job từ hàng đợi `ingestion`; trạng thái đẩy ra qua API-06 ở T-204) |
| Vai trò chính | BE |
| Ước lượng | 3d |
| Phụ thuộc | T-006 (khung Celery), T-108 (`POST /documents` đẩy job), D-05 (bổ sung mã lỗi vào SDD §3.4.3) |
| Trạng thái | To do |

## 1. Mục tiêu

Dựng hai bước đầu của pipeline ingestion (SADD §2.2.2): **quét mã độc** và **kiểm tra cấu trúc PDF**, kèm phân loại lỗi chính xác để người dùng biết tệp nào không vào được tập truy vấn và vì sao (BR-002).

Nguyên tắc bắt buộc:
- Trạng thái nguồn sự thật là cột `document.status`, **không** phải trạng thái trong broker.
- Mỗi bước **idempotent**: job chạy lại (retry hoặc `reap_stuck`) cho kết quả giống hệt.
- Lỗi **do nội dung tệp** không retry; lỗi **hạ tầng** retry 3 lần rồi mới kết luận.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-005.1 | *Given* người dùng tải lên tệp hỏng, tệp có mật khẩu, tệp không phải PDF hoặc PDF không có lớp văn bản, *When* quá trình xử lý thất bại, *Then* tệp hiển thị trạng thái "Lỗi" kèm lý do cụ thể theo bảng mã lỗi. |
| AC-005.2 | *Given* một tệp có trạng thái "Lỗi", *When* người dùng đặt câu hỏi, *Then* tệp đó không được dùng làm nguồn và không được trích dẫn. |
| AC-006.3 | *Given* một tệp có số trang lớn hơn 300 (DF-03), *When* hệ thống kiểm tra tệp, *Then* tệp chuyển sang "Lỗi" với lý do "Tệp vượt quá 300 trang". |
| AC-003.1 | *Given* người dùng có ít hơn 50 tài liệu, *When* tải lên một PDF hợp lệ, *Then* tài liệu xuất hiện với trạng thái "Đang xử lý" rồi chuyển "Sẵn sàng". |

## 3. Hợp đồng API / giao diện

Task này không expose HTTP API. Hợp đồng là **chữ ký task Celery** và **hợp đồng trạng thái**:

```python
# app/workers/ingestion.py
@celery_app.task(
    name="ingestion.process",
    queue="ingestion",
    acks_late=True,
    max_retries=3,
    autoretry_for=(InfrastructureError,),   # CHỈ lỗi hạ tầng
    retry_backoff=2, retry_backoff_max=32, retry_jitter=False,  # 2s / 8s / 32s
)
def process_document(document_id: str) -> None: ...
```

Kết quả của task luôn là một trong hai:

```
document.status = 'failed'  + document.error_code ∈ {
    FILE_REJECTED, PDF_ENCRYPTED, PDF_CORRUPTED, TOO_MANY_PAGES, PDF_NO_TEXT, INGESTION_FAILED
}
# hoặc chuyển tiếp sang T-202 (vẫn giữ status='processing')
```

## 4. Thay đổi dữ liệu

Bảng `document` (SADD §3.1.1) — chỉ **cập nhật**, không tạo bảng mới:

| Cột | Ghi ở bước này |
|---|---|
| `status` | `'processing'` → `'failed'` khi lỗi; giữ `'processing'` khi qua được bước 2 |
| `error_code` | Mã lỗi phân loại (xem §6) |
| `page_count` | Ghi khi mở được PDF ở bước 2 (kể cả khi sau đó `TOO_MANY_PAGES`) |

Không đụng tới `chunk`. Worker dùng vai trò DB riêng có `BYPASSRLS` (SADD §3.1.3), truy vấn **luôn lọc tường minh theo `document_id`**.

## 5. Các bước triển khai

1. **Nhận job** `ingestion.process(document_id)` từ hàng đợi `ingestion` (tách riêng khỏi `maintenance`).
2. **Khóa chống chạy trùng:** đọc `document` theo `id`; nếu `status` đã là `ready`/`failed`/`deleting` → thoát sớm (idempotent, không làm lại).
3. **Bước 1 — quét mã độc:**
   - Tải tệp từ object storage theo `blob_key` (`owner/{owner_id}/{document_id}.pdf`) vào thư mục tạm hoặc stream thẳng tới `clamd`.
   - Gọi ClamAV qua `clamd` TCP (`INSTREAM`).
   - Phát hiện mã độc → `status='failed'`, `error_code='FILE_REJECTED'`, **xóa object ngay lập tức** khỏi storage, ghi `audit_log`, dừng pipeline.
   - Lỗi kết nối/timeout tới `clamd` → ném `InfrastructureError` để Celery retry.
4. **Bước 2 — kiểm tra cấu trúc** bằng PyMuPDF:
   - `fitz.open(path)`; bắt exception mở tệp → `PDF_CORRUPTED`.
   - `doc.needs_pass == True` → `PDF_ENCRYPTED`.
   - Ghi `page_count = doc.page_count`; nếu `page_count > max_pages` (DF-03, lấy từ cấu hình, **không** hard-code) → `TOO_MANY_PAGES`.
   - Ba lỗi trên: `status='failed'` + `error_code`, **giữ nguyên tệp trong storage** (khác với mã độc) để debug; dừng pipeline.
5. **Chuyển tiếp:** nếu qua bước 2, gọi tiếp logic trích xuất/chia đoạn của T-202 trong cùng chuỗi task — **không** set `ready` ở task này.
6. **Dọn dẹp:** luôn xóa tệp tạm trong `finally`.
7. **Quan sát (SADD §4.3):** tạo span `ingest.scan`, `ingest.validate`; tăng metric `documents_failed_total{error_code}`; log chỉ chứa `document_id`, `error_code`, `latency_ms` — **tuyệt đối không** log tên tệp hay nội dung (P-03).
8. Sau khi set `failed`, publish sự kiện trạng thái lên Redis pub/sub để T-204 đẩy tới UI.

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `FILE_REJECTED` | ClamAV phát hiện mã độc | `failed`; **xóa object ngay**; không retry; thông báo "Tệp không an toàn và đã bị từ chối" |
| `PDF_ENCRYPTED` | `doc.needs_pass` | `failed`; giữ tệp; không retry; hành động UI: Xóa |
| `PDF_CORRUPTED` | `fitz.open` ném lỗi | `failed`; giữ tệp; không retry; hành động UI: Xóa |
| `TOO_MANY_PAGES` | `page_count > DF-03` | `failed`; giữ tệp; không retry; hành động UI: Xóa |
| `INGESTION_FAILED` | Lỗi hạ tầng sau 3 lần retry (ClamAV, object storage, DB) | `failed`; giữ tệp; hành động UI: **Thử lại** · Xóa |

Trường hợp biên:
- **Job chạy lại sau khi đã `failed`** → thoát sớm ở bước 2, không ghi đè `error_code`.
- **Tài liệu bị xóa khi đang xử lý** (`status='deleting'`) → thoát sớm, không ghi trạng thái.
- **Tệp đã biến mất khỏi storage** (upload gián đoạn) → `INGESTION_FAILED`, không retry vô hạn.
- **ClamAV trả kết quả chậm** với tệp 20 MB → đặt timeout rõ ràng (đề xuất 60s) rồi coi là lỗi hạ tầng.

## 7. Kiểm thử bắt buộc

- [ ] Tệp chứa chuỗi EICAR → `FILE_REJECTED`, object **không còn** trong storage.
- [ ] PDF đặt mật khẩu → `PDF_ENCRYPTED`, object **vẫn còn** trong storage.
- [ ] Tệp PDF bị cắt cụt/hỏng header → `PDF_CORRUPTED`.
- [ ] PDF 301 trang (DF-03 = 300) → `TOO_MANY_PAGES`, `page_count` vẫn được ghi = 301.
- [ ] Giả lập `clamd` timeout → retry đúng 3 lần với khoảng nghỉ 2s/8s/32s, sau đó `INGESTION_FAILED`.
- [ ] Chạy lại job trên tài liệu đã `failed` → không đổi `error_code`, không gọi lại ClamAV (idempotent).
- [ ] Kiểm thử log: không dòng log nào của pipeline chứa `document.name` hoặc nội dung trang (P-03).

## 8. Định nghĩa Hoàn thành

- [ ] AC-005.1, AC-006.3 đạt với bộ tệp lỗi kiểm thử (ít nhất 1 tệp cho mỗi mã lỗi).
- [ ] Mỗi mã lỗi có ít nhất 1 unit test và xuất hiện đúng trong `document.error_code`.
- [ ] Task idempotent — có test chạy lại 2 lần liên tiếp cho cùng kết quả.
- [ ] Span OTel và metric `documents_failed_total{error_code}` phát đúng.
- [ ] Mã lỗi `FILE_REJECTED`, `INGESTION_FAILED` đã được bổ sung vào danh mục SDD §3.4.3 (D-05) hoặc có ticket theo dõi.

## 9. Tham chiếu

- SADD v0.3 §2.2.2 (pipeline ingestion, bảng bước 1–3), §4.3 (quan sát), P-03, P-07
- User Stories v0.4 — US-003, US-005 (bảng thông báo lỗi), US-006 (AC-006.3)
- SDD UI/UX v0.3 §3.4.3 (danh mục mã lỗi hiển thị), §3.7.1 (vòng đời tài liệu)
- PRD v0.2 §0.3 (DF-03 = 300 trang), §4.2 (ER-03 – ER-06)
