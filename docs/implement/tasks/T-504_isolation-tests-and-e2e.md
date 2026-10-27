# T-504 — Kiểm thử cô lập dữ liệu tự động & E2E luồng chính

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | US-002 (cô lập), US-001 → US-014 (luồng chính) |
| Epic | EP-01, EP-02, EP-03, EP-04 |
| Module (SADD §2.2.1) | `identity`, `documents`, `retrieval` + hạ tầng kiểm thử |
| API liên quan | API-01, API-03, API-04, API-06, API-07, API-09 |
| Vai trò chính | QA (chủ trì) · BE (hỗ trợ fixture) · TL (tích hợp CI) |
| Ước lượng | 2d |
| Phụ thuộc | T-104 (RLS), T-108, T-206, T-304, T-306 |
| Trạng thái | To do |

## 1. Mục tiêu

Tạo bộ kiểm thử **tự động, chạy trong CI** để làm bằng chứng cho hai cổng:

- **G-03 — Cô lập dữ liệu:** người dùng không thể xem hoặc truy vấn tài liệu của người khác.
- **G-01 — Luồng cốt lõi:** upload PDF → xử lý → hỏi → câu trả lời có nguồn hoặc `not_found` hoạt động end-to-end.

Yêu cầu then chốt: đây phải là kiểm thử **tự động chạy mỗi PR**, không phải demo thủ công — vì cô lập dữ liệu là thứ dễ vỡ thầm lặng khi refactor.

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-03 | Integration test hai người dùng chạy tự động, xanh trong CI |
| AC-002.1 | A hỏi câu chỉ có đáp án trong tài liệu của B → nhận `not_found`, **không** trích dẫn tài liệu của B |
| AC-002.2 | A mở danh sách tài liệu → chỉ thấy tài liệu của A |
| AC-002.3 | A truy cập trực tiếp `document_id` của B → bị từ chối, trả **404 `DOC_NOT_FOUND`** (không phải 403) |
| G-01 | E2E luồng chính chạy xanh, có video/trace làm bằng chứng |
| AC-003.1, AC-014.1 | Tài liệu chuyển `processing` → `ready`; câu trả lời có ≥ 1 thẻ nguồn |

## 3. Hợp đồng / kịch bản cụ thể

**Integration test cô lập** (pytest + Testcontainers cho PostgreSQL 16 + pgvector và Redis 7):

```python
# tests/integration/test_owner_isolation.py
def test_a_cannot_see_b_documents(client_a, client_b, seed_docs):
    doc_b = seed_docs["b"][0]

    # AC-002.2 — danh sách
    items = client_a.get("/documents").json()["items"]
    assert all(d["id"] != doc_b.id for d in items)

    # AC-002.3 — truy cập trực tiếp: 404, KHÔNG phải 403
    assert client_a.get(f"/documents/{doc_b.id}").status_code == 404
    assert client_a.get(f"/documents/{doc_b.id}").json()["code"] == "DOC_NOT_FOUND"
    assert client_a.delete(f"/documents/{doc_b.id}").status_code == 404

    # AC-002.1 — hỏi nội dung chỉ có trong tài liệu của B
    answer = stream_question(client_a, "Giá trị hợp đồng với đối tác Z là bao nhiêu?")
    assert answer["done"]["type"] == "not_found"
    assert answer["citations"] == []

def test_rls_blocks_even_without_app_layer(db_session_as_app_role):
    # Đặt app.user_id = A rồi query thẳng SQL: không được thấy hàng của B
    db_session_as_app_role.execute("SET LOCAL app.user_id = :a", {"a": USER_A})
    rows = db_session_as_app_role.execute("SELECT id FROM document").fetchall()
    assert all(r.id not in B_DOC_IDS for r in rows)
```

**E2E luồng chính** (Playwright, chạy trên `staging` hoặc docker-compose):

```ts
// e2e/core-flow.spec.ts
test('G-01: upload → ready → hỏi → có nguồn → xóa', async ({ page }) => {
  await loginAs(page, 'user-a');
  await page.getByTestId('upload-dropzone').setInputFiles('fixtures/HopDong_DoiTacA.pdf');
  await expect(page.getByTestId('doc-item').first()).toContainText('Đang xử lý');
  await expect(page.getByTestId('doc-item').first()).toContainText('Sẵn sàng', { timeout: 90_000 });

  await page.getByTestId('question-input').fill('Thời hạn thanh toán là bao lâu?');
  await page.keyboard.press('Enter');
  await expect(page.getByTestId('answer-message')).toBeVisible();
  await expect(page.getByTestId('citation-chip')).toHaveCount(1, { minimum: 1 });

  await page.getByTestId('doc-delete').first().click();
  await page.getByTestId('confirm-delete').click();
  await expect(page.getByTestId('doc-item')).toHaveCount(0);
});
```

## 4. Thay đổi dữ liệu

- Không đổi lược đồ sản phẩm. Thêm **fixture**: 2 tài khoản kiểm thử (A, B) trong `app_user` của môi trường test, mỗi tài khoản 2–3 PDF corpus.
- Dữ liệu test được tạo và dọn sạch trong từng lần chạy (Testcontainers khởi tạo DB mới mỗi lần, không dùng DB chung).

## 5. Các bước triển khai

1. Dựng fixture Testcontainers: PostgreSQL 16 + pgvector + `unaccent`, Redis 7; chạy migration Alembic; seed 2 user và vai trò.
2. Tạo helper `client_as(user)` tự xử lý cookie phiên + `X-CSRF-Token`, để test đọc dễ hiểu.
3. Viết các ca cô lập ở §3, **bao gồm ca gọi thẳng SQL** bằng vai trò ứng dụng để chứng minh RLS chặn ngay cả khi tầng ứng dụng bị bỏ qua (phòng thủ nhiều lớp, ADR-06).
4. Bổ sung ca kiểm tra tiền tố khóa object storage: object của B nằm dưới `owner/{B}/`, A không có đường lấy URL trực tiếp.
5. Viết E2E Playwright cho luồng chính; dùng `data-testid` đã quy định trong SDD (CN-10) thay vì selector theo text để test không vỡ khi đổi chữ.
6. Thêm ca E2E cho nhánh `not_found` (hỏi câu không có đáp án → hiện `NotFoundMessage`, không có thẻ nguồn).
7. Tích hợp CI: integration test chạy **mỗi PR**; E2E chạy mỗi PR vào nhánh chính và nightly. Lưu video + trace của lần chạy thất bại làm artifact.
8. Đặt thời gian chờ hợp lý cho bước `ready` (tới 90 giây) để tránh test rung (flaky) khi TEI chậm.

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| Test rung do thời gian ingestion dao động | Chờ theo **trạng thái** (`Sẵn sàng` xuất hiện) chứ không `sleep` cố định; timeout rộng |
| E2E phụ thuộc LLM thật → chậm và tốn chi phí (R-06) | Cho phép chạy E2E với adapter LLM giả lập (stub trả nội dung cố định có `[S1]`) ở CI mỗi PR; chạy với LLM thật ở nightly |
| Trả 403 thay vì 404 cho tài liệu của người khác | Là **lỗi bảo mật** (tiết lộ sự tồn tại) — test phải khẳng định đúng 404 |
| Môi trường test dùng chung gây nhiễu dữ liệu | Bắt buộc Testcontainers (DB mới mỗi lần), không trỏ vào DB staging dùng chung |
| TEI/ClamAV chưa sẵn sàng trong CI | Dùng container nhẹ hoặc stub cho ClamAV; TEI có thể dùng mô hình nhỏ ở CI nếu cần |

## 7. Kiểm thử bắt buộc

- [ ] Toàn bộ ca cô lập (AC-002.1, AC-002.2, AC-002.3) xanh trong CI
- [ ] Ca gọi thẳng SQL chứng minh RLS chặn độc lập với tầng ứng dụng
- [ ] E2E luồng chính xanh: upload → ready → hỏi → thẻ nguồn → xóa
- [ ] E2E nhánh `not_found`: không có thẻ nguồn nào hiển thị
- [ ] Cố tình tắt một policy RLS trong nhánh thử → test **phải đỏ** (chứng minh test có tác dụng thật)

## 8. Định nghĩa Hoàn thành

- [ ] Integration test cô lập chạy tự động mỗi PR, thời gian chạy chấp nhận được (< 5 phút)
- [ ] E2E luồng chính chạy < 5 phút, có artifact video/trace
- [ ] Báo cáo kết quả chạy mới nhất được đính kèm hồ sơ G-01 và G-03
- [ ] Không có ca test nào bị `skip` hoặc đánh dấu `xfail` khi trình gate
- [ ] QA Lead xác nhận bộ kiểm thử đủ bao phủ cho hai cổng

## 9. Tham chiếu

- [SADD §3.1.3 (cô lập 3 lớp), ADR-06 (RLS), §4.4 (CI/CD)](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-01, G-03](../../requirements/PRD.md)
- [User Stories — US-002 (AC-002.1 – AC-002.3), US-003, US-011, US-014](../../design/User_Stories.md)
- [SDD §2.2 CN-10 (`data-testid`), §3.2.3 (cây thành phần)](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 Sprint 5, §8.1](../implement_plan.md)
