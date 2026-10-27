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
| Trạng thái | To do |

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

- [ ] **AC-017.2:** câu hỏi tiếng Anh thuần → câu trả lời tiếng Anh, giao diện vẫn tiếng Việt
- [ ] **AC-017.1:** tải PDF tiếng Anh, hỏi tiếng Việt → câu trả lời tiếng Việt, `citations` trỏ đúng tệp tiếng Anh
- [ ] Hỏi tiếng Việt **không dấu** ("thoi han thanh toan la bao lau") → vẫn truy xuất được đoạn có dấu (nhờ `unaccent`)
- [ ] Unit test bộ phát hiện ngôn ngữ trên ≥ 20 câu mẫu (10 vi, 10 en), độ chính xác 100% trên tập này
- [ ] Câu hỏi 5 ký tự → không ném lỗi, mặc định `vi`, analytics ghi `other`
- [ ] Mock `lingua-py` ném exception → vẫn có câu trả lời, log có cảnh báo
- [ ] Snapshot giao diện khớp [`SCR-02_19_english-question.png`](../../design/html_design/SCR-02_19_english-question.png)

## 8. Định nghĩa Hoàn thành

- [ ] AC-017.1 và AC-017.2 đạt, có ca kiểm thử tự động trong CI
- [ ] AC-017.3 có **bộ câu hỏi chuẩn tách theo ngôn ngữ** đã bàn giao cho T-501 (kết quả đo chốt ở Sprint 5)
- [ ] `prompt_version` mới ghi vào `answer`
- [ ] Thuộc tính `language` có trong `question_submitted`, **không** kèm nội dung câu hỏi (P-03)
- [ ] Toàn bộ chuỗi giao diện vẫn tiếng Việt, không có chuỗi tiếng Anh lọt vào UI (UX-07)
- [ ] Tham số ngôn ngữ hỗ trợ `{vi, en}` nằm trong cấu hình, không hard-code (P-06)

## 9. Tham chiếu

- [SADD §2.2.2 (NFC), §2.2.3 (phát hiện ngôn ngữ), AR-02](../../requirements/SADD.md)
- [PRD — DF-06, §5.2 `question_submitted.language`](../../requirements/PRD.md)
- [User Stories — US-017 (AC-017.1 – AC-017.3)](../../design/User_Stories.md)
- [SDD UI/UX — UX-07 giao diện tiếng Việt](../../design/SDD_UI_UX_Blueprint.md)
- Ảnh thiết kế: [`SCR-02_19_english-question.png`](../../design/html_design/SCR-02_19_english-question.png)
- [implement_plan.md §5 Sprint 4](../implement_plan.md)
