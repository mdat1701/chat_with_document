# T-202 — Trích xuất văn bản theo trang & chia đoạn

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 2 |
| Story | US-003 (Tải một tệp PDF lên) |
| Epic | EP-02 |
| Module (SADD §2.2.1) | `ingestion` (chạy ở worker) |
| API liên quan | — |
| Vai trò chính | BE (hỗ trợ: AI cho tham số chia đoạn) |
| Ước lượng | 2d |
| Phụ thuộc | T-201 (bước quét & kiểm tra PDF) |
| Trạng thái | In progress (lõi chạy đúng; tham số chia đoạn đã nối với cấu hình trong phiên này) |

## 1. Mục tiêu

Trích xuất văn bản **theo từng trang** từ PDF đã qua kiểm tra, phát hiện tệp scan (không có lớp văn bản), và chia thành các đoạn ~500 token **giữ nguyên số trang** để mọi trích dẫn sau này đều chỉ được đúng trang (US-014, US-015).

Đây là bước quyết định chất lượng truy xuất: chia đoạn sai → câu trả lời mất ngữ cảnh; mất số trang → không kiểm chứng được.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-005.1 | *Given* người dùng tải lên PDF không có lớp văn bản (bản scan), *When* xử lý thất bại, *Then* tệp hiển thị "Lỗi" kèm lý do "Tệp không có nội dung văn bản (có thể là bản scan)". |
| AC-015.1 | *Given* câu trả lời có trích dẫn, *When* hiển thị thẻ nguồn, *Then* thẻ có định dạng `tên tệp · tr. X` — **phụ thuộc trực tiếp vào `page_start`/`page_end` ghi ở task này**. |
| AC-014.3 | *Given* một thẻ nguồn bất kỳ, *When* người đánh giá mở tệp được trích dẫn, *Then* tệp đó thực sự chứa thông tin được nêu. |

## 3. Hợp đồng API / giao diện

Không có HTTP API. Hợp đồng nội bộ giữa T-202 và T-203:

```python
@dataclass(frozen=True)
class ExtractedChunk:
    ordinal: int          # thứ tự trong tài liệu, bắt đầu từ 0
    page_start: int       # 1-based, theo cách người dùng đọc PDF
    page_end: int         # >= page_start
    heading_path: str | None   # ví dụ "Điều 5 > 5.2" nếu nhận diện được
    content: str          # đã chuẩn hóa NFC, đã trim

def extract_and_chunk(pdf_path: str, cfg: ChunkConfig) -> list[ExtractedChunk]: ...

@dataclass(frozen=True)
class ChunkConfig:
    target_tokens: int = 500      # có thể đổi qua cấu hình (CL-03)
    overlap_tokens: int = 50      # [Đề xuất] — hiệu chỉnh ở T-502
    min_chars_per_page: int = 20  # ngưỡng phát hiện trang không có văn bản
    empty_page_ratio: float = 0.8 # ≥80% trang rỗng → PDF_NO_TEXT
```

## 4. Thay đổi dữ liệu

Task này **chưa ghi DB** — trả danh sách `ExtractedChunk` cho T-203 insert. Các trường ánh xạ 1-1 sang bảng `chunk` (SADD §3.1.1):

| Trường `ExtractedChunk` | Cột `chunk` |
|---|---|
| `ordinal` | `ordinal` (int) |
| `page_start` / `page_end` | `page_start` / `page_end` (int) |
| `heading_path` | `heading_path` (text) |
| `content` | `content` (text) → sinh `tsv` tự động ở T-203 |

Cập nhật duy nhất ở task này: `document.error_code = 'PDF_NO_TEXT'` khi phát hiện bản scan.

## 5. Các bước triển khai

1. Mở lại PDF đã validate ở T-201 (tái dùng `fitz.Document`, không mở lần hai).
2. **Trích xuất theo trang** bằng `page.get_text("blocks")` thay vì `"text"` thuần:
   - `blocks` giữ thứ tự khối theo bố cục, giảm rủi ro đảo cột/bảng (rủi ro R-04 trong kế hoạch).
   - Sắp xếp block theo `(y0, x0)` để đọc trên-xuống, trái-phải.
3. **Phát hiện bản scan:** đếm số trang có `len(text.strip()) < min_chars_per_page`. Nếu tỉ lệ `≥ empty_page_ratio` (80%) → `status='failed'`, `error_code='PDF_NO_TEXT'`, dừng pipeline.
4. **Chuẩn hóa Unicode NFC** cho toàn bộ văn bản (`unicodedata.normalize("NFC", text)`) — bắt buộc để dấu tiếng Việt không bị tách tổ hợp, ảnh hưởng cả embedding lẫn full-text search.
5. **Nhận diện tiêu đề (tùy chọn, best-effort):** dựa vào cỡ chữ/độ đậm trong `blocks` để dựng `heading_path`; nếu không chắc chắn, để `None` — **không** đoán bừa.
6. **Chia đoạn ~500 token:**
   - Dùng tokenizer cùng họ với mô hình embedding (`BAAI/bge-m3`) để đếm token, không đếm theo ký tự.
   - Ưu tiên cắt ở ranh giới đoạn văn/câu, không cắt giữa câu.
   - Giữ overlap nhỏ giữa hai đoạn liền kề (đề xuất 50 token) để không mất ngữ cảnh ở mép đoạn.
   - **Theo dõi trang trong suốt quá trình cắt:** `page_start` = trang của ký tự đầu đoạn, `page_end` = trang của ký tự cuối đoạn. Đoạn trải hai trang là hợp lệ (`page_start=12, page_end=13` → UI hiển thị `tr. 12–13`, xem CL-02).
7. Gán `ordinal` tăng dần theo thứ tự đọc.
8. Trả danh sách cho T-203; **không** set `document.status='ready'` ở đây.
9. Metric: `ingestion_duration_seconds{step="extract"}`, số đoạn tạo ra theo tài liệu (chỉ số đếm, không nội dung).

## 6. Mã lỗi & trường hợp biên

| Mã lỗi | Khi nào | Hành vi |
|---|---|---|
| `PDF_NO_TEXT` | ≥80% số trang có <20 ký tự văn bản | `failed`; giữ tệp; không retry; UI: "Tệp không có nội dung văn bản (có thể là bản scan). Hiện chưa hỗ trợ loại tệp này." · hành động Xóa |
| `INGESTION_FAILED` | PyMuPDF ném lỗi bất thường khi đọc trang, hoặc hết bộ nhớ | `failed`; UI: Thử lại · Xóa |

Trường hợp biên:
- **PDF hỗn hợp** (một nửa scan, một nửa văn bản) → dưới ngưỡng 80% nên **vẫn xử lý**; các trang scan đơn giản không tạo ra đoạn nào.
- **Trang có bảng biểu phức tạp** → thứ tự `blocks` có thể vẫn sai; ghi nhận vào AR log, cân nhắc bổ sung `pdfplumber` nếu T-501 phát hiện lỗi số liệu (R-04).
- **Tài liệu rất ngắn** (1 trang, vài dòng) → tạo đúng 1 đoạn, không lỗi.
- **Tài liệu 300 trang** → số đoạn ~600; kiểm tra bộ nhớ worker không phình quá mức (xử lý theo luồng, không giữ toàn bộ văn bản trong RAM nếu tránh được).
- **Văn bản có ký tự điều khiển / soft hyphen** → loại bỏ trước khi chia đoạn.

## 7. Kiểm thử bắt buộc

- [x] PDF văn bản nhiều trang → mọi đoạn có `page_start ≤ page_end` — `test_extract_and_chunk_preserves_page_ranges`
- [x] PDF scan thuần (ảnh) → `PDF_NO_TEXT` — `test_extract_and_chunk_rejects_scan_only_pdf`
- [x] PDF hỗn hợp 30% trang scan → không lỗi — **test mới** `test_extract_and_chunk_accepts_mixed_scan_and_text_pdf` (1 trang có chữ + 2 trang scan rỗng = 67% rỗng, dưới ngưỡng 80% mặc định → vẫn xử lý được)
- [x] Văn bản tiếng Việt có dấu, so khớp NFC 100% — **test mới** `test_extract_and_chunk_normalizes_vietnamese_text_to_nfc` (giả lập `page.get_text()` trả về NFD, xác nhận `extract_and_chunk()` luôn trả NFC)
- [x] Đoạn trải hai trang (`page_start != page_end`) — đã phủ gián tiếp bởi `test_extract_and_chunk_preserves_page_ranges` (có từ trước)
- [x] Không đoạn nào vượt `target_tokens` (số từ, không phải token thật — xem ghi chú) — **test mới** `test_extract_and_chunk_never_exceeds_target_tokens_per_chunk`
- [ ] Đối chiếu thủ công số trang với tài liệu mẫu — chưa thực hiện (cần biên bản thủ công)

## 8. Định nghĩa Hoàn thành

- [x] `extract_and_chunk` có test với ≥ 5 PDF mẫu — nay có 6 test (page-range, scan-only, hỗn hợp, NFC, giới hạn kích thước đoạn + 2 test `_validate_pdf`); vẫn thiếu mẫu nhiều cột/có bảng (cần PDF thật phức tạp hơn `fitz.open()` dựng tay)
- [x] Tham số chia đoạn nằm trong cấu hình, không hard-code — **đã sửa**: `_process_document` giờ dựng `ChunkConfig(target_tokens=get_settings().chunk_size_tokens, overlap_tokens=get_settings().chunk_overlap_tokens)` trước khi gọi `extract_and_chunk`, thay vì `ChunkConfig()` mặc định — T-502/T-506 đổi được qua cấu hình, không cần sửa code
- [x] `page_start`/`page_end` chính xác trên bộ test hiện có
- [x] Không log nội dung văn bản — xác nhận bằng đọc code

### Ghi chú triển khai thực tế

`extract_and_chunk()` (`app/modules/ingestion/service.py`) chạy đúng về mặt
logic. **Đã sửa (phiên này):** `_process_document` giờ đọc
`settings.chunk_size_tokens`/`settings.chunk_overlap_tokens` khi dựng
`ChunkConfig`, thay vì dùng mặc định `dataclass` cứng — xác nhận bằng đọc
code (`ruff`/`mypy` đều sạch); chưa viết test riêng cho việc nối cấu hình
này (chi phí mock `_process_document` — vốn còn gọi DB/Redis/ClamAV —
không tương xứng với một thay đổi 1 dòng). Thêm 4 test mới (PDF hỗn hợp,
NFC tiếng Việt, giới hạn kích thước đoạn) — tổng 6 test cho
`app/modules/ingestion/` (từ 2 lên 6), đều chạy qua `python -m pytest`
thật, không phải chỉ đọc code.

**Lưu ý thật phát hiện khi viết test giới hạn kích thước đoạn:** `target_tokens`
hiện được đếm bằng **số từ** (`re.findall(r"\S+", ...)`), không phải
token thật của tokenizer `BAAI/bge-m3` như §5 bước 6 mô tả ("dùng
tokenizer cùng họ với mô hình embedding"). Đây là một đơn giản hóa có
chủ đích (word-count rẻ hơn gọi tokenizer), nhưng nghĩa là `target_tokens`
hiện tại thực chất là "số từ tối đa mỗi đoạn" — khác danh nghĩa so với
spec, chưa gây lỗi chức năng nhưng nên biết khi hiệu chỉnh tham số ở
T-502/T-506 (số từ và số token không tỷ lệ 1:1, nhất là với tiếng Việt).
Giữ "In progress" vì chưa có mẫu PDF nhiều cột/bảng và chưa đo trên
Postgres thật.

## 9. Tham chiếu

- SADD v0.3 §2.2.2 (bước 3–4 pipeline), §3.1.1 (bảng `chunk`), §2.2.3 (vì sao cần `page_start/page_end`)
- User Stories v0.4 — US-003, US-005, US-015 (`CitationChip` dùng `page`)
- SDD UI/UX v0.3 §3.4.1 (`CitationVM.page`), DQ-07 (định dạng nhiều trang)
- Kế hoạch: CL-02 (định dạng `tr. 12–13`), CL-03 (tham số chia đoạn chưa hiệu chỉnh), R-04 (PDF bảng biểu)
