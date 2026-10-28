# T-402 — Hiển thị số trang trong thẻ nguồn

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 4 |
| Story | US-015 (P1) |
| Epic | EP-04 — Trích dẫn và kiểm chứng |
| Module (SADD §2.2.1) | `qa` (phía máy chủ), `features/chat` (phía giao diện) |
| API liên quan | API-09 (sự kiện `citations`), API-02 `GET /config` (feature flag) |
| Vai trò chính | FE (chính) + BE |
| Ước lượng | 1 ngày công |
| Phụ thuộc | T-202 (chunk giữ `page_start`/`page_end`), T-306 (CitationChip), **CL-02 / SDD DQ-07** chưa chốt |
| Trạng thái | In progress (hàm định dạng + feature flag qua `useAppConfig()` + unit test đã xong; còn thiếu đối chiếu thủ công AC-015.2 và so khớp ảnh) |

## 1. Mục tiêu

Thẻ nguồn hiện mới chỉ hiện tên tệp (T-306). Task này bổ sung **số trang** để người dùng mở đúng chỗ cần kiểm chứng, theo định dạng `tên tệp · tr. X`.

Vì US-015 là **P1** (được phép hoãn sau Pilot Gate nếu thiếu năng lực), tính năng phải **bật/tắt được bằng feature flag** trong `GET /config` mà không cần build lại front-end.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-015.1 | Câu trả lời có trích dẫn → thẻ nguồn hiển thị theo định dạng `tên tệp · tr. X` |
| AC-015.2 | Người đánh giá mở tệp tại trang được trích dẫn → trang đó **thực sự** chứa thông tin được nêu |
| AC-015.3 | Máy chủ không trả số trang cho một trích dẫn → thẻ **chỉ ghi tên tệp**, tuyệt đối không hiển thị `tr. undefined` |

> Tiêu chí của US-015 là `[Đề xuất]` trong User Stories v0.4 — cần PM xác nhận trước khi đóng story.

## 3. Hợp đồng API / giao diện

Sự kiện `citations` của API-09 (đã có từ T-303/T-304, task này chỉ **tiêu thụ** thêm 2 trường):

```jsonc
// event: citations
{
  "items": [
    { "index": 1, "document_id": "…", "document_name": "HopDong_DoiTacA.pdf",
      "page_start": 12, "page_end": 12 },
    { "index": 2, "document_id": "…", "document_name": "PhuLuc2_2026.pdf",
      "page_start": 3,  "page_end": 4  }
  ]
}
```

Feature flag trong `GET /config` (API-02):

```jsonc
{
  "max_file_size_bytes": 20971520,
  "...": "...",
  "features": { "citation_page_numbers": true }   // US-015 — P1, tắt được
}
```

Quy tắc hiển thị trên `CitationChip`:

| Dữ liệu nhận được | Hiển thị |
|---|---|
| `page_start = 12`, `page_end = 12` | `HopDong_DoiTacA.pdf · tr. 12` |
| `page_start = 12`, `page_end = 13` | `PhuLuc2_2026.pdf · tr. 12–13` `[Đề xuất — chờ chốt DQ-07]` |
| `page_start = null` hoặc thiếu trường | `TaiLieu.pdf` (chỉ tên tệp — AC-015.3) |
| `features.citation_page_numbers = false` | `TaiLieu.pdf` (chỉ tên tệp, dù server có trả số trang) |

## 4. Thay đổi dữ liệu

Không có migration mới. `chunk.page_start` / `chunk.page_end` đã được ghi từ **T-202** khi chia đoạn, nên mọi trích dẫn đều có sẵn số trang. Task này chỉ bảo đảm dữ liệu được **truyền qua** đúng chuỗi: `chunk` → bước kiểm tra trích dẫn (`qa`) → sự kiện `citations` → `CitationVM` → `CitationChip`.

Bổ sung khóa cấu hình `features.citation_page_numbers` (mặc định `true`) vào ConfigMap và schema của `GET /config`.

## 5. Các bước triển khai

1. **BE:** trong bước kiểm tra trích dẫn của `qa`, khi ánh xạ `[S#] → [n]`, lấy kèm `page_start`/`page_end` của chunk tương ứng và đưa vào payload `citations`. Nếu chunk thiếu số trang (dữ liệu cũ) thì gửi `null`, **không** gửi `0`.
2. **BE:** bổ sung `features.citation_page_numbers` vào `GET /config`, đọc từ biến môi trường (P-06).
3. **FE:** mở rộng `CitationVM` trong view model (SDD §3.4.1) để nhận `page_start`/`page_end`.
4. **FE:** viết hàm thuần `formatCitationPage(start, end)` trả về chuỗi hoặc `null`, đặt trong `shared/i18n`/`features/chat/lib` để unit test dễ:
   - `start == null` → `null`
   - `start === end` → `tr. {start}`
   - `start !== end` → `tr. {start}–{end}` (dùng en dash `–`, không phải hyphen)
5. **FE:** `CitationChip` render phần ` · tr. X` **chỉ khi** hàm trên trả chuỗi khác `null` **và** flag bật. Không render dấu `·` trơ trọi khi thiếu số trang.
6. **FE:** đảm bảo chuỗi "tr." nằm trong `messages.vi.ts` (không hard-code trong component).
7. Phát sự kiện `citation_viewed` khi người dùng hover ≥ 500 ms hoặc nhấn vào chip (SDD §3.8.4) — thuộc tính **không** chứa tên tệp (xem T-404).
8. Ghi chú trong code một dòng `TODO(DQ-07)` tại chỗ định dạng khoảng trang, để dễ sửa khi Tech Lead chốt CL-02.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Server trả `page_start = null` | Chip chỉ hiện tên tệp; **không** hiện `tr. undefined`, `tr. null`, hay dấu `·` thừa (AC-015.3) |
| Đoạn trích trải nhiều trang | Hiện `tr. 12–13` theo đề xuất; định dạng chính thức **chờ DQ-07 / CL-02** |
| `page_start > page_end` (dữ liệu hỏng) | Hiển thị theo `page_start`, ghi cảnh báo ở log server (không chứa nội dung) |
| Flag tắt | Giao diện quay về đúng trạng thái Sprint 3 (chỉ tên tệp); không có khoảng trắng/ký tự thừa |
| Câu trả lời `not_found` | Không có thẻ nguồn nào, nên task này không áp dụng (AC-014.4) |
| Câu trả lời `incomplete`/`failed` | Ẩn toàn bộ thẻ nguồn theo IR-01 — số trang cũng bị ẩn theo |

## 7. Kiểm thử bắt buộc

- [x] Unit test `formatCitationPage` 4 nhánh — thêm `frontend/src/features/chat/citations.test.ts` (null, `start===end`, `end` thiếu, `start!==end` dùng en dash) + 3 ca cho `formatCitation` (gồm nhánh tắt flag)
- [x] AC-015.1: chip hiển thị `tên · tr. 12` — `CitationChip.tsx` gọi `formatCitation(documentName, pageStart, pageEnd, showPageNumbers)`
- [x] AC-015.3: `page_start = null` → chỉ tên, không có `undefined` — giữ nguyên logic cũ, có test xác nhận không chứa `"undefined"`/`"·"`
- [x] Tắt `features.citation_page_numbers` → ẩn số trang — nối xong: `ChatPage.tsx` đọc `useAppConfig().config.features.citation_page_numbers`, truyền xuống `AnswerMessage`/`CitationChip` qua prop `showPageNumbers`; test `ChatPage.test.tsx` ("tắt citation_page_numbers") mock `GET /config` trả `features.citation_page_numbers=false` và xác nhận chip không chứa `"tr."`
- [ ] AC-015.2 (đối chiếu thủ công PDF) — cần T-501/bộ câu hỏi chuẩn, chưa làm
- [ ] Đối chiếu ảnh thiết kế — chưa làm

## 8. Định nghĩa Hoàn thành

- [x] AC-015.1/AC-015.3 có test tự động — `citations.test.ts`
- [x] Feature flag hai chiều không cần build lại — đạt: `useAppConfig()` đọc `GET /config` một lần khi khởi động, không cần build lại FE để đổi giá trị `features.citation_page_numbers` phía server
- [x] Chuỗi lấy từ `messages.vi.ts` — `"tr."` chuyển thành `uiText.citationPagePrefix`, `citations.ts::formatCitationPage` import từ đó
- [x] `citation_viewed` không chứa tên tệp — `track("citation_viewed", {citation_index})` trong `CitationChip.tsx`
- [x] Ghi chú `TODO(DQ-07)` tồn tại — có trong `citations.ts::formatCitationPage`
- [ ] Khớp ảnh thiết kế — chưa đối chiếu

### Ghi chú triển khai thực tế

Hoàn thiện nốt phần còn thiếu: `ChatPage.tsx` giờ đọc
`useAppConfig().config.features.citation_page_numbers` và truyền xuống
`CitationChip` qua prop `showPageNumbers` — khi backend đổi giá trị trong
`GET /config` (ví dụ tắt flag để hoãn US-015 sau Pilot Gate), FE phản ánh
đúng ngay lần tải trang kế tiếp mà không cần build lại. `citations.ts`
không còn hard-code `"tr."`, lấy từ `uiText.citationPagePrefix` trong
`messages.vi.ts`. Thêm `citations.test.ts` phủ đủ 4 nhánh của
`formatCitationPage` và 3 nhánh của `formatCitation` (gồm cả khi tắt
flag). Còn thiếu: đối chiếu thủ công PDF (AC-015.2, cần bộ câu hỏi chuẩn ở
T-501) và so khớp ảnh thiết kế.

## 9. Tham chiếu

- [SADD §2.2.2, §3.1.1 — chunk giữ `page_start`/`page_end`](../../requirements/SADD.md)
- [User Stories — US-015 (AC-015.1 – AC-015.3)](../../design/User_Stories.md)
- [SDD UI/UX §3.4.1 `CitationVM`, §3.4.2 IR-01, §3.8.4](../../design/SDD_UI_UX_Blueprint.md) · DQ-07
- Ảnh thiết kế: [`SCR-02_14_answer-with-citations.png`](../../design/html_design/SCR-02_14_answer-with-citations.png)
- [implement_plan.md §5 Sprint 4, §9 CL-02](../implement_plan.md)
