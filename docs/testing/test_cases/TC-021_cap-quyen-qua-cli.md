# TC-021 — Cấp quyền qua CLI phản ánh đúng khi đăng nhập

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-021 |
| User Story / AC | US-023 / AC-023.1, AC-023.2 |
| Task liên quan | T-103 |
| Mức ưu tiên | P1 |
| Loại kiểm thử | System/E2E (giao diện + CLI) |
| Trạng thái tự động hoá hiện tại | Pass thật ở mức unit (`backend/app/cli.py` + test tương ứng); chưa có E2E thật xác nhận qua UI (liên kết chặt với TC-001/TC-002). |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).
- Cần quyền chạy lệnh `python -m app.cli ...` trên môi trường backend (dòng lệnh, không qua UI) — nếu agent thực thi không có quyền truy cập terminal backend, BLOCKED.
- Cần IdP thật đã cấu hình (như TC-001).

## Tiền điều kiện

- Có 1 tài khoản IdP thật chưa từng được cấp quyền.

## Các bước thực hiện

1. Chạy `python -m app.cli list-users --active-only` — xác nhận email test chưa có trong danh sách.
2. Đăng nhập bằng tài khoản đó qua `${TEST_BASE_URL}` — xác nhận thấy màn hình "Không có quyền" (như TC-002).
3. Từ dòng lệnh backend, chạy `python -m app.cli grant-access --email <email> --role user`.
4. Đăng xuất (nếu còn phiên) và đăng nhập lại cùng tài khoản đó qua `${TEST_BASE_URL}`.
5. Xác nhận lần này vào được thư viện tài liệu.
6. Chạy `python -m app.cli revoke-access --email <email> --yes`.
7. Đăng xuất và thử đăng nhập lại lần nữa.

## Kết quả mong đợi

- KQ1: Trước khi `grant-access`, đăng nhập chỉ dẫn tới màn hình "Không có quyền".
- KQ2: Ngay sau khi chạy `grant-access`, đăng nhập lại (phiên mới) cho phép vào thư viện tài liệu bình thường.
- KQ3: Ngay sau khi chạy `revoke-access`, đăng nhập lại (phiên mới) đưa về màn hình "Không có quyền" trở lại — quyền bị thu hồi có hiệu lực ngay, không cần đợi.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-021`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (không hard-code URL khác) cho các bước đăng nhập; chạy lệnh CLI ở backend cho các bước cấp/thu hồi quyền.
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng: output của từng lệnh CLI, màn hình "Không có quyền" (trước grant), màn hình thư viện tài liệu (sau grant), màn hình "Không có quyền" lại (sau revoke).
4. Đối chiếu từng dòng "Kết quả mong đợi", chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo mẫu ở [`README.md`](./README.md).
6. Lưu toàn bộ artifact vào `./test_reports/TC-021_cap-quyen-qua-cli/`.
7. Nếu không có quyền chạy CLI backend hoặc không có IdP thật, báo **BLOCKED** kèm lý do.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- [User_Stories.md](../../design/User_Stories.md) US-023 (AC-023.1, .2)
- `backend/app/cli.py`
