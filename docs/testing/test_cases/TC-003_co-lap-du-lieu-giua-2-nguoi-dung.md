# TC-003 — Cô lập dữ liệu giữa 2 người dùng

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-003 |
| User Story / AC | US-002 / AC-002.1 |
| Task liên quan | T-104, T-504 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | RLS đã có unit test pass thật; 4 integration test (`test_owner_isolation.py`, gồm 2 ca SQL trực tiếp) viết đúng qua Testcontainers nhưng **chỉ xác nhận skip đúng cách**, chưa chạy thật trên Postgres thật. Ca này là kiểm chứng qua UI thật đầu tiên cho G-03. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).

## Tiền điều kiện

- Hai tài khoản khác nhau, cả hai đã được cấp quyền (`python -m app.cli grant-access --email userA@example.com`, `--email userB@example.com`).
- User A đã tải lên ít nhất 1 tài liệu (ví dụ `tai-lieu-A.pdf`) và tài liệu đã ở trạng thái `ready`.
- User B chưa từng tải tài liệu nào, hoặc đã tải tài liệu khác tên để phân biệt rõ.
- Cần 2 phiên trình duyệt độc lập (ví dụ một cửa sổ thường cho User A, một cửa sổ ẩn danh riêng cho User B) để tránh lẫn cookie phiên.
- Yêu cầu IdP thật đã cấu hình (như TC-001) để đăng nhập 2 tài khoản khác nhau — nếu chưa có, BLOCKED.

## Dữ liệu kiểm thử

- User A: `<email A>`, tài liệu `tai-lieu-A.pdf`.
- User B: `<email B>`.

## Các bước thực hiện

1. Trong cửa sổ 1, đăng nhập bằng User A, tải lên `tai-lieu-A.pdf`, chờ tới trạng thái `ready` trong danh sách (`[data-testid="doc-item"]`). Ghi lại ID/tên tài liệu hiển thị.
2. Trong cửa sổ 2 (phiên độc lập), đăng nhập bằng User B.
3. Quan sát danh sách tài liệu (`[data-testid="doc-list"]`) của User B — xác nhận không thấy `tai-lieu-A.pdf`.
4. Thử mở một cuộc hội thoại hỏi đáp trong khi trỏ tới tài liệu của User A (nếu giao diện cho phép thao tác trực tiếp bằng ID, ví dụ qua URL có chứa ID tài liệu của A) — quan sát phản hồi.
5. Trong cửa sổ 2, thử gọi xóa tài liệu của User A (nếu biết ID, thử thao tác qua API trực tiếp bằng DevTools/Network, hoặc qua giao diện nếu lộ được ID) — quan sát mã phản hồi.

## Kết quả mong đợi

- KQ1: User B không thấy tài liệu của User A trong danh sách của mình.
- KQ2: Thao tác hỏi đáp/truy cập trực tiếp vào tài liệu của User A từ phiên của User B bị từ chối (404/403), không trả về nội dung tài liệu của A.
- KQ3: Thao tác xóa tài liệu của User A từ phiên User B bị từ chối (404/403), tài liệu của A vẫn còn nguyên khi User A kiểm tra lại.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-003`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` cho cả 2 phiên (không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng cho từng phiên ở từng bước quan trọng (danh sách tài liệu của A, danh sách tài liệu của B, phản hồi lỗi khi B cố truy cập/xóa tài liệu của A).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-003_co-lap-du-lieu-giua-2-nguoi-dung/`.
7. Nếu thiếu IdP thật hoặc không chuẩn bị được 2 tài khoản như tiền điều kiện, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-002 (AC-002.1)
- `backend/tests/integration/test_owner_isolation.py`, `backend/app/cli.py`
