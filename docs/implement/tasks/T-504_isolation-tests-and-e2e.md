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
| Trạng thái | In progress (4 integration test cô lập viết xong gồm 2 ca RLS qua SQL trực tiếp, chưa chạy thật trên Postgres; E2E Playwright chưa chạy được) |

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

- [x] AC-002.2/AC-002.3 viết đúng trong `tests/integration/test_owner_isolation.py` (`test_owner_isolation_contract`) — A không thấy tài liệu của B trong `GET /documents`, `DELETE` trên tài liệu của B → 404; AC-002.1 (hỏi câu chỉ có đáp án ở tài liệu B → `not_found`) chưa có ca riêng (cần `FakeLLM` trả lời có cấu trúc kiểm được, hiện `test_owner_cannot_query_other_owner_document` chỉ kiểm tra status code 201/403/404 lỏng lẻo, không kiểm nội dung câu trả lời)
- [x] Ca gọi SQL trực tiếp chứng minh RLS độc lập tầng ứng dụng — **đã thêm** `test_rls_blocks_even_with_direct_sql_bypassing_app_layer` (chạy thẳng SQL qua vai trò `cwd_app`, không qua FastAPI/ORM, sau `set_config('app.user_id', A, true)`) và `test_rls_fails_closed_without_app_user_id_set` (không đặt `app.user_id` → lỗi, không âm thầm trả toàn bộ bảng, đúng T-104) trong `tests/integration/test_owner_isolation.py`; cùng cơ chế skip-khi-không-Docker như 2 test cũ
- [ ] E2E Playwright (`frontend/e2e/`, `playwright.config.ts`) — có file cấu hình nhưng **chưa thể chạy thật** trong môi trường này (không có trình duyệt/stack đầy đủ) — xem xác nhận riêng của phần FE
- [ ] E2E `not_found` — chưa chạy được, cùng lý do
- [ ] Tắt policy RLS phải làm test đỏ — chưa thử nghiệm (cần chỉnh migration tạm thời rồi chạy lại, chưa làm)

## 8. Định nghĩa Hoàn thành

- [ ] Integration test cô lập chạy tự động mỗi PR — viết đúng, dùng Testcontainers (Postgres 16 + pgvector, Redis 7), **tự `pytest.skip`** khi không có Docker (môi trường này không có Docker nên chưa từng thực thi thật — chỉ xác nhận được bằng cách chạy `pytest tests/integration/test_owner_isolation.py -v` và thấy 2 test `SKIPPED` thay vì `ERROR` như trước khi sửa trong phiên này)
- [ ] E2E < 5 phút có artifact — chưa chạy được
- [ ] Báo cáo đính kèm G-01/G-03 — chưa có (cần chạy thật trước)
- [x] Không test nào `xfail`/`skip` do thiết kế sai — các skip hiện tại đều do thiếu Docker (môi trường), không phải do test tự miễn trừ logic
- [ ] QA Lead xác nhận — ngoài phạm vi review code

### Ghi chú triển khai thực tế

Trong phiên này, file `backend/tests/integration/test_owner_isolation.py`
(đã tồn tại sẵn nhưng **bị lỗi**: tham chiếu fixture `client_a`, `client_b`,
`seeded_documents` không có fixture nào định nghĩa, khiến pytest báo
2 `ERROR` khi thu thập test) đã được sửa bằng cách thêm
`backend/tests/integration/conftest.py` mới — dựng `PostgresContainer`
(`pgvector/pgvector:pg16`) + `RedisContainer` qua `testcontainers`, chạy
`alembic upgrade head` thật (có policy RLS của T-104), tạo 2 người dùng +
tài liệu test bằng SQL trực tiếp, dựng phiên Redis thật khớp định dạng
`SessionData`, và cung cấp 2 `TestClient` độc lập (cookie/CSRF riêng) cho A
và B. Đã xác nhận bằng `pytest -v`: trước đây 2 `ERROR`, sau khi sửa là
2 `SKIPPED` (đúng, vì môi trường này không có Docker) — không còn lỗi giả
do thiếu fixture. Đã xoá thư mục `tests/isolation/` (chỉ chứa 1 placeholder
`@pytest.mark.skip` cho chính task này) vì nay đã có test thật thay thế.

**Đã thêm (phiên sau):** 2 ca RLS qua SQL trực tiếp —
`test_rls_blocks_even_with_direct_sql_bypassing_app_layer` (chạy thẳng
SQL qua vai trò `cwd_app` sau `set_config('app.user_id', A, true)`,
không qua FastAPI/ORM) và `test_rls_fails_closed_without_app_user_id_set`
(không đặt `app.user_id` → kỳ vọng lỗi, đúng hành vi fail-closed của
T-104). Cả hai viết đúng theo cùng khuôn mẫu đã dùng cho 2 test cũ, tự
`pytest.skip` khi không có Docker — xác nhận bằng cách chạy
`pytest tests/integration/test_owner_isolation.py -v` và thấy **4**
test `SKIPPED` (trước đây 2), không có `ERROR`/lỗi cú pháp nào.

**Thành thật về giới hạn xác minh:** khác với các mục đã chuyển "Done"
ở các task khác (nơi phần còn thiếu chỉ là *đo lường*/*chạy trên môi
trường thật* của logic đã xác nhận đúng), 2 test RLS mới này **chưa
từng chạy thật** — chỉ xác nhận được là chúng *thu thập được* và *skip
đúng cách* (không lỗi cú pháp/fixture), không xác nhận được chúng
*pass* khi có Postgres thật. Vì đây là bằng chứng cốt lõi cho Pilot Gate
G-03, giữ "In progress" thay vì "Done" cho tới khi chạy được trên môi
trường có Docker.

**Vẫn còn thiếu, cần Docker + trình duyệt thật:** chạy `pytest
tests/integration` để xác nhận toàn bộ 4 test thật sự pass (không chỉ
skip đúng cách), viết ca AC-002.1 kiểm tra nội dung câu trả lời
`not_found` (hiện bị giới hạn bởi `FakeLLM` luôn trả cùng một chuỗi cố
định không trích dẫn gì — không phân biệt được "cô lập hoạt động đúng"
với "FakeLLM không bao giờ trích dẫn", nên viết thêm cũng không tăng độ
tin cậy thật sự), thử tắt policy RLS để xác nhận test tự viết thật sự đỏ
(mutation test cho chính bộ test), và chạy Playwright E2E (xem xác nhận
riêng của phần front-end).



## 9. Tham chiếu

- [SADD §3.1.3 (cô lập 3 lớp), ADR-06 (RLS), §4.4 (CI/CD)](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-01, G-03](../../requirements/PRD.md)
- [User Stories — US-002 (AC-002.1 – AC-002.3), US-003, US-011, US-014](../../design/User_Stories.md)
- [SDD §2.2 CN-10 (`data-testid`), §3.2.3 (cây thành phần)](../../design/SDD_UI_UX_Blueprint.md)
- [implement_plan.md §5 Sprint 5, §8.1](../implement_plan.md)
