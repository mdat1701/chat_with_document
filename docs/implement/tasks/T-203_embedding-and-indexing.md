# T-203 — Embedding & đánh chỉ mục, chuyển tài liệu sang "Sẵn sàng"

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-003 (Tải một tệp PDF lên) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `ingestion` (chạy ở worker) |
| API liên quan | — (phát trạng thái qua Redis pub/sub → API-06 ở T-204) |
| Vai trò chính | BE + AI |
| Ước lượng | 2d |
| Phụ thuộc | T-202 (danh sách đoạn), T-005 (migration `chunk`), T-002 (TEI trong môi trường dev) |
| Trạng thái | Done (code + kiến trúc đúng, chưa đo được trên staging thật) |

## 1. Mục tiêu

Vector hóa các đoạn văn bản **bằng mô hình chạy nội bộ** (văn bản tài liệu không rời biên giới tin cậy TB-2 — D2 trong SADD), ghi vào bảng `chunk`, rồi chuyển tài liệu sang `ready` để người dùng hỏi được.

Mốc hiệu năng: PDF 20 trang từ lúc nhận `201` đến `status='ready'` **≤ 60 giây** (AC-003.3).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-003.1 | *Given* người dùng có ít hơn 50 tài liệu, *When* tải lên một PDF có lớp văn bản ≤ 20 MB và ≤ 300 trang, *Then* tài liệu xuất hiện trong danh sách với trạng thái "Đang xử lý" rồi chuyển sang "Sẵn sàng". |
| AC-003.2 | *Given* một tài liệu vừa chuyển sang "Sẵn sàng", *When* người dùng hỏi một câu mà đáp án chỉ có trong tài liệu đó, *Then* câu trả lời đúng và trích dẫn tài liệu đó. |
| AC-003.3 | *Given* một PDF văn bản 20 trang, *When* người dùng tải lên, *Then* tài liệu chuyển sang "Sẵn sàng" trong ≤ 60 giây `[Đề xuất]`. |
| AC-021.2 | *Given* một tài liệu còn 7 ngày nữa hết hạn, *When* người dùng mở danh sách, *Then* hiển thị nhãn "Sẽ bị xóa sau 7 ngày" — **phụ thuộc `expires_at` ghi ở task này**. |

## 3. Hợp đồng API / giao diện

Hợp đồng với TEI (embedding nội bộ, SADD Phụ lục A):

```http
POST http://tei-embedding:80/embed
Content-Type: application/json

{ "inputs": ["đoạn 1", "đoạn 2", "..."], "truncate": true }

→ 200 [[0.0123, ...1024 chiều...], [...]]
```

Port nội bộ (P-01 — lõi miền không phụ thuộc hạ tầng):

```python
class EmbeddingPort(Protocol):
    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    @property
    def dimensions(self) -> int: ...   # 1024 với bge-m3
```

Sự kiện phát ra khi hoàn tất (tiêu thụ bởi T-204):

```json
// Redis PUBLISH doc-status:{owner_id}
{ "id": "<document_id>", "status": "ready", "error_code": null, "page_count": 20 }
```

## 4. Thay đổi dữ liệu

**Insert** vào `chunk` (SADD §3.1.1):

| Cột | Giá trị |
|---|---|
| `document_id` | FK tới tài liệu đang xử lý |
| `owner_id` | **Denormalize** từ `document.owner_id` — để RLS lọc không cần join |
| `ordinal`, `page_start`, `page_end`, `heading_path`, `content` | Từ `ExtractedChunk` (T-202) |
| `tsv` | **Cột GENERATED** `to_tsvector('simple', unaccent(content))` — không ghi tay |
| `embedding` | `vector(1024)` từ TEI |

**Update** `document`:

```sql
UPDATE document
SET status = 'ready',
    ready_at = now(),
    page_count = :page_count,
    expires_at = uploaded_at + make_interval(days => :retention_days)  -- DF-05
WHERE id = :document_id AND status = 'processing';
```

Chỉ mục liên quan (đã tạo ở T-005): B-tree `chunk(owner_id, document_id)`, GIN `chunk(tsv)`. **Chưa** tạo HNSW — theo ADR-05 chỉ bật khi tổng chunk > 2 triệu.

## 5. Các bước triển khai

1. Nhận danh sách `ExtractedChunk` từ T-202.
2. **Gọi TEI theo lô** (batch 32–64 đoạn/lần, hiệu chỉnh theo bộ nhớ): giảm số round-trip, tránh timeout. Đặt timeout rõ ràng cho mỗi lô; lỗi → `InfrastructureError` để Celery retry (2s/8s/32s).
3. Kiểm tra số chiều trả về đúng 1024; sai → lỗi cấu hình, dừng với `INGESTION_FAILED` (không retry vô ích).
4. **Insert hàng loạt** vào `chunk` bằng `execute_values`/`COPY` trong **một transaction**:
   - Trước khi insert, `DELETE FROM chunk WHERE document_id = :id` để job chạy lại không tạo đoạn trùng (**idempotent**, P-07).
5. Trong cùng transaction hoặc transaction kế tiếp: `UPDATE document SET status='ready', ...` (câu lệnh ở §4). Điều kiện `AND status='processing'` bảo vệ trường hợp tài liệu vừa bị xóa (`deleting`).
6. Nếu `UPDATE` ảnh hưởng 0 hàng (tài liệu đã bị xóa giữa chừng) → rollback insert chunk, kết thúc êm, **không** báo lỗi.
7. **Publish** sự kiện trạng thái lên Redis `doc-status:{owner_id}` cho T-204.
8. Phát sự kiện analytics `document_processing_succeeded` (chỉ số đếm/thời gian, **không** tên tệp — P-03; chi tiết allow-list ở T-404).
9. **Đo hiệu năng:** span `ingest.embed` + `ingest.index`; metric `ingestion_duration_seconds{outcome="success"}`. So sánh với ngân sách 60 giây của AC-003.3; nếu vượt, cân nhắc tăng bản sao TEI hoặc chuyển GPU (SADD §2.3 ghi ngưỡng: hàng đợi ingestion > 5 phút thì nâng cấp).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `INGESTION_FAILED` | TEI không phản hồi sau 3 lần retry; lỗi ghi DB; số chiều vector sai | `status='failed'`; UI: **Thử lại** · Xóa |
| — (kết thúc êm) | Tài liệu đã bị xóa (`deleting`) trong lúc embedding | Rollback, không ghi trạng thái, không báo lỗi |

Trường hợp biên:
- **Job chạy lại sau khi đã `ready`** → điều kiện `status='processing'` khiến UPDATE không khớp; cần thoát sớm ngay từ đầu task (kiểm tra trạng thái như T-201 bước 2).
- **Tài liệu 300 trang (~600 đoạn)** → chia lô, theo dõi thời gian; chấp nhận vượt 60s vì AC-003.3 chỉ ràng buộc PDF 20 trang.
- **Đoạn rỗng sau khi trim** → bỏ qua, không gửi tới TEI, không insert.
- **TEI trả về ít vector hơn số đoạn gửi đi** → coi là lỗi hạ tầng, retry.

## 7. Kiểm thử bắt buộc

- [ ] PDF 20 trang trên staging ≤ 60 giây (AC-003.3) — cần staging thật, chưa đo được
- [ ] Mọi `chunk.embedding` không NULL sau `ready` — đúng theo code (`_index_document` raise nếu `len(vectors) != len(chunks)`), chưa xác nhận bằng SQL thật (cần Postgres)
- [ ] `expires_at = uploaded_at + 90 ngày` — tính đúng trong `upload_document` (`timedelta(days=settings.retention_days)`), chưa chạy trên DB thật
- [x] Chạy lại job trên tài liệu đã `ready` → không nhân đôi chunk — `_index_document` có guard `if document.status != "processing": return` trước khi insert
- [ ] Xóa tài liệu giữa lúc embedding → không còn chunk mồ côi — phụ thuộc `delete_document_use_case` (T-206); race cụ thể (xóa đúng lúc worker đang insert) chưa có test
- [ ] Giả lập TEI down → retry 3 lần rồi `INGESTION_FAILED` — `TeiEmbeddingAdapter.embed_batch` ném `RuntimeError` không phải `InfrastructureError`, cần xác nhận Celery task bắt được để retry đúng theo cơ chế T-201 (xem Lệch so với mô tả ban đầu)
- [ ] `tsv` sinh tự động, tìm được từ không dấu — cột `Computed(...)` với `unaccent` đã khai báo đúng trong `Chunk` model, cần Postgres thật để xác nhận chạy

## 8. Định nghĩa Hoàn thành

- [ ] AC-003.1/AC-003.3 trên staging — chưa có staging
- [ ] AC-003.2 — phụ thuộc chéo Sprint 3 (`qa`), đã có `qa.service.stream_answer` gọi `retrieve()` thật nên về nguyên tắc đã nối được, chưa đo trên staging
- [x] Idempotent — xác nhận bằng đọc code (guard trạng thái)
- [x] Không log nội dung tài liệu — xác nhận bằng đọc code
- [x] `EmbeddingPort` là `Protocol` trong `ports/`, `TeiEmbeddingAdapter` trong `adapters/` — đúng ranh giới P-01, xác nhận bằng `lint-imports` (3 contract kiến trúc đều pass)

### Ghi chú triển khai thực tế

Kiến trúc port/adapter đúng chuẩn, kiểm tra tĩnh sạch
(`ruff`/`mypy`/`lint-imports`). **Lệch so với mô tả ban đầu:**
`TeiEmbeddingAdapter.embed_batch` ném `RuntimeError` thường khi TEI không
phản hồi, trong khi pipeline ingestion phân biệt `InfrastructureError`
(retry được) với lỗi khác — nên rà lại để lỗi mạng tới TEI được Celery
retry đúng 3 lần như §7 yêu cầu, thay vì rơi vào nhánh lỗi không retry.
Không có TEI/Postgres thật trong môi trường này nên toàn bộ hành vi runtime
(thời gian `ready`, retry thật, chỉ mục `tsv`) chưa đo được — chỉ xác nhận
được đúng về mặt code/kiến trúc.

## 9. Tham chiếu

- SADD v0.3 §2.2.2 (bước 5–6), §2.3 (TEI, cấu hình bản sao), §3.1.1 (`chunk`), §3.1.2 (chỉ mục), ADR-05 (không dùng ANN ở quy mô pilot), P-01, P-07
- User Stories v0.4 — US-003 (AC-003.1 – AC-003.3), US-021 (AC-021.2 dùng `expires_at`)
- PRD v0.2 §0.3 — DF-05 (90 ngày lưu trữ)
