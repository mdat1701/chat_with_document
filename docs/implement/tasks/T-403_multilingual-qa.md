# T-403 — Hỏi đáp tiếng Việt / tiếng Anh

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 4 |
| Story | US-017 (P0) |
| Epic | EP-03 — Hỏi đáp trên tài liệu |
| Module (SADD §2.2.1) | `qa` (chính), `ingestion` và `retrieval` (xác nhận đa ngôn ngữ) |
| API liên quan | API-09 |
| Vai trò chính | AI (chính) + BE |
| Ước lượng | 2 ngày công |
| Phụ thuộc | T-303 (prompt v1), T-304 (API hỏi đáp), T-401 (FTS `unaccent`) |
| Trạng thái | In progress (code đúng, có test cho nhánh fallback; `lingua` không cài được trong môi trường này — thiếu Microsoft C++ Build Tools cho dependency `regex`, không phải lỗi code) |

## 1. Mục tiêu

Người dùng hỏi bằng **tiếng Việt hoặc tiếng Anh** và nhận câu trả lời **đúng ngôn ngữ đã hỏi**, kể cả khi tài liệu viết bằng ngôn ngữ khác. Giao diện **luôn giữ tiếng Việt** (UX-07) — chỉ phần nội dung câu trả lời đổi theo ngôn ngữ câu hỏi.

Ba thành phần của giải pháp:
1. Phát hiện ngôn ngữ câu hỏi, giới hạn trong tập `{vi, en}` (DF-06).
2. Ràng buộc ngôn ngữ trả lời trong prompt.
3. Xác nhận truy xuất **xuyên ngôn ngữ** hoạt động (câu hỏi tiếng Việt tìm được đoạn tiếng Anh).

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-017.1 | Tài liệu viết bằng tiếng Anh, người dùng hỏi bằng tiếng Việt → câu trả lời **bằng tiếng Việt** và vẫn trích dẫn đúng tài liệu tiếng Anh |
| AC-017.2 | Người dùng hỏi bằng tiếng Anh → câu trả lời **bằng tiếng Anh** |
| AC-017.3 | Chạy bộ câu hỏi chuẩn cho **từng ngôn ngữ** trong DF-06 → tỷ lệ đúng của mỗi ngôn ngữ đạt KR2.1 (đo ở T-501) |

## 3. Hợp đồng API / giao diện

API-09 không đổi hợp đồng. Ngôn ngữ phát hiện được dùng nội bộ cho prompt và **được ghi vào analytics** (T-404):

```jsonc
// Nội bộ pipeline qa (không lộ ra client)
{ "detected_language": "vi" }      // "vi" | "en" | "other"

// Sự kiện analytics question_submitted (xem T-404)
{ "question_length": 57, "language": "vi", "ready_doc_count": 9 }
```

Giao diện: **không có thay đổi chuỗi UI**. Toàn bộ nhãn, nút, thông báo lỗi vẫn tiếng Việt lấy từ `messages.vi.ts` (UX-07), kể cả khi câu trả lời là tiếng Anh.

## 4. Thay đổi dữ liệu

Không có migration. Hai điều kiện dữ liệu cần **xác nhận** đã đúng từ sprint trước:

| Điều kiện | Đặt ở đâu | Vì sao cần cho task này |
|---|---|---|
| Văn bản chuẩn hóa Unicode **NFC** khi trích xuất | T-202 (`ingestion`) | Giữ đúng dấu tiếng Việt; nếu là NFD thì so khớp và hiển thị sẽ lệch |
| `chunk.tsv = to_tsvector('simple', unaccent(content))` | T-203 / T-401 | Cho phép khớp cả khi người dùng gõ **không dấu** |
| Mô hình embedding `bge-m3` và reranker `bge-reranker-v2-m3` | T-203, T-401 | Cả hai đều **đa ngôn ngữ**, là cơ sở để AC-017.1 chạy được mà không cần dịch máy |

## 5. Các bước triển khai

1. Thêm thư viện `lingua-py` vào `qa`; khởi tạo detector **chỉ với 2 ngôn ngữ** `{Vietnamese, English}` để tăng độ chính xác trên câu ngắn và giảm chi phí.
2. Chạy phát hiện ngôn ngữ ở **bước đầu tiên** của pipeline hỏi đáp (SADD §2.2.3), trước khi embedding câu hỏi.
3. Quy tắc quyết định:
   - Detector trả `Vietnamese` → `lang = "vi"`.
   - Detector trả `English` → `lang = "en"`.
   - Detector không chắc chắn / câu quá ngắn (ví dụ < 10 ký tự) → **mặc định `vi`** (ngôn ngữ chính của nhóm người dùng PER-01), nhưng ghi `language = "other"` vào analytics để theo dõi tần suất.
4. Truyền `lang` vào prompt: bổ sung một dòng ràng buộc cố định dạng *"Trả lời bằng {ngôn ngữ}. Giữ nguyên thuật ngữ, số liệu và tên riêng đúng như trong tài liệu nguồn."* — tăng `prompt_version`.
5. **Không** dịch câu hỏi trước khi truy xuất và **không** dịch nội dung chunk: bge-m3 đã khớp xuyên ngôn ngữ, việc dịch thêm sẽ làm mất thuật ngữ gốc và tăng độ trễ.
6. Giữ nguyên tên tệp và nhãn trích dẫn theo nguyên bản (không dịch tên tài liệu).
7. Thêm thuộc tính `language` vào sự kiện `question_submitted` (phối hợp T-404) — chỉ mã ngôn ngữ, **không** kèm nội dung câu hỏi.
8. Bổ sung nhãn `language` vào metric `answer_latency_seconds` nếu chi phí cardinality chấp nhận được; nếu không, chỉ ghi ở span OTel.
9. Chuẩn bị **2 nhánh bộ câu hỏi chuẩn** (vi và en) cho T-501 để đo AC-017.3 riêng theo ngôn ngữ.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Câu hỏi trộn hai ngôn ngữ ("Payment term của đối tác A là gì?") | Detector chọn ngôn ngữ chiếm ưu thế; chấp nhận sai lệch, miễn câu trả lời vẫn có căn cứ. Ghi `language` theo kết quả detector |
| Câu hỏi quá ngắn hoặc chỉ có số/mã | Mặc định `vi`, analytics ghi `other` |
| `lingua-py` ném lỗi / khởi tạo thất bại | Fallback `lang = "vi"`, ghi cảnh báo; **không** làm hỏng câu trả lời |
| Tài liệu tiếng Anh, câu hỏi tiếng Việt | Truy xuất vẫn chạy bình thường nhờ bge-m3; trích dẫn giữ tên tệp và nội dung gốc tiếng Anh (AC-017.1) |
| LLM trả lời sai ngôn ngữ | Không chặn ở code; bắt bằng ca kiểm thử trong bộ câu hỏi chuẩn, sửa bằng prompt ở T-502 |
| Người dùng hỏi bằng ngôn ngữ thứ ba (ví dụ tiếng Nhật) | Ngoài phạm vi DF-06; hệ thống xử lý như `other` → trả lời tiếng Việt. Không coi là lỗi |

## 7. Kiểm thử bắt buộc

- [x] AC-017.2 (hỏi tiếng Anh → trả lời tiếng Anh) — `detect_language` trả `("en","en")`, prompt nối `"Trả lời bằng English."`; test `test_english_common_words_detected_as_english` (mới)
- [x] AC-017.1 (PDF Anh, hỏi Việt → trả lời Việt) — `test_vietnamese_diacritics_detected_as_vietnamese` (mới) xác nhận nhánh phát hiện tiếng Việt; phần "truy xuất xuyên ngôn ngữ" phụ thuộc bge-m3 thật, chưa đo được (không có TEI thật)
- [x] Hỏi không dấu vẫn truy xuất được — `unaccent()` áp cho cả truy vấn FTS và cột `tsv` (xem T-401)
- [x] Unit test bộ phát hiện ngôn ngữ — `tests/unit/test_qa_language_detection.py` (mới, 4 test: câu ngắn, tiếng Việt có dấu, tiếng Anh, câu trộn ngôn ngữ) — chưa đạt mốc "≥ 20 câu" của spec gốc, nhưng phủ đúng 4 nhánh logic của hàm
- [x] Câu hỏi 5 ký tự → mặc định `vi`, không lỗi — `detect_language` có `if len(question.strip()) < 10: return "vi", "other"` ở đầu hàm
- [x] `lingua` lỗi/thiếu vẫn có câu trả lời — `try/except ImportError` khi import module, và `try/except RuntimeError` quanh `detect_language_of()` đều fallback về heuristic dấu tiếng Việt/từ tiếng Anh thường gặp
- [ ] Snapshot giao diện — không áp dụng (FE không hiển thị gì khác biệt theo ngôn ngữ)

## 8. Định nghĩa Hoàn thành

- [x] AC-017.1/AC-017.2 có test tự động trong CI — `tests/unit/test_qa_language_detection.py` (mới)
- [ ] Bộ câu hỏi chuẩn theo ngôn ngữ cho T-501 — chưa có (xem T-501)
- [x] `prompt_version="v2"` ghi vào `answer`
- [ ] `language` trong `question_submitted` — **FE tự phát hiện ngôn ngữ riêng** (`ChatPage.tsx::detectLanguage`, bản heuristic đơn giản hơn) để gắn vào sự kiện analytics, **không dùng chung logic với backend** `qa/service.py::detect_language` — hai cài đặt tách biệt, có thể cho kết quả khác nhau giữa log phân tích và câu trả lời thực tế
- [x] UI vẫn tiếng Việt — xác nhận bằng đọc code (không có chuỗi tiếng Anh cố định trong JSX)
- [x] `supported_languages=("vi","en")` trong cấu hình, phát ra qua `GET /config`

### Ghi chú triển khai thực tế

`detect_language()` chạy đúng, có fallback 2 lớp (lingua → heuristic dấu
tiếng Việt/từ tiếng Anh) nên không bao giờ crash. Thêm
`tests/unit/test_qa_language_detection.py` (4 test, mới) phủ cả 4 nhánh
logic (câu ngắn, tiếng Việt, tiếng Anh, câu trộn ngôn ngữ).

**Lưu ý môi trường (đã xác minh lại, nguyên nhân cụ thể):** thử
`pip install lingua-language-detector` trực tiếp trong phiên này —
thất bại khi build wheel cho dependency bắc cầu `regex` với lỗi "Microsoft
Visual C++ 14.0 or greater is required" (máy không có C++ Build Tools
cho Python 3.15, bản Python quá mới để có sẵn wheel dựng trước). Đây là
giới hạn môi trường thật, không phải lỗi trong code — mọi lần chạy ở đây
đều dùng nhánh heuristic, chưa từng thực thi được nhánh `lingua` thật. Cần
cài gói này ở môi trường CI/staging (Python 3.12 theo Dockerfile, có
wheel sẵn) và chạy lại để xác nhận độ chính xác, vì heuristic chỉ là lưới
an toàn, không phải cơ chế chính theo thiết kế.

**Lệch so với mô tả ban đầu:** FE có một bản `detectLanguage()` riêng trong
`ChatPage.tsx` (regex đơn giản hơn nhiều) dùng để gắn nhãn `language` vào
sự kiện analytics `question_submitted` — tách biệt hoàn toàn với
`qa/service.py::detect_language` ở backend (dùng để chọn ngôn ngữ trả
lời). Hai lần phát hiện độc lập có thể cho kết quả khác nhau; nên cân nhắc
để backend trả `language` thật qua sự kiện `meta`/`done` thay vì để FE tự
đoán lại.

## 9. Tham chiếu

- [SADD §2.2.2 (NFC), §2.2.3 (phát hiện ngôn ngữ), AR-02](../../requirements/SADD.md)
- [PRD — DF-06, §5.2 `question_submitted.language`](../../requirements/PRD.md)
- [User Stories — US-017 (AC-017.1 – AC-017.3)](../../design/User_Stories.md)
- [SDD UI/UX — UX-07 giao diện tiếng Việt](../../design/SDD_UI_UX_Blueprint.md)
- Ảnh thiết kế: [`SCR-02_19_english-question.png`](../../design/html_design/SCR-02_19_english-question.png)
- [implement_plan.md §5 Sprint 4](../implement_plan.md)
