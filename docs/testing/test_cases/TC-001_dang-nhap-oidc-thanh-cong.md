# TC-001 — Đăng nhập OIDC thành công, vào được ứng dụng

| Trường | Giá trị |
|---|---|
| Mã ca kiểm thử | TC-001 |
| User Story / AC | US-001 / AC-001.1, AC-001.2 |
| Task liên quan | T-101, T-102, T-107 |
| Mức ưu tiên | P0 |
| Loại kiểm thử | System/E2E (giao diện) |
| Trạng thái tự động hoá hiện tại | Chưa có E2E tự động chạy thật; `T-101` đã có 39 unit test qua `FakeOIDCAdapter`/`fakeredis` (pass thật) nhưng chưa từng chạy với IdP thật (D-03 chưa chốt — xem test_plan.md §11). Ca này là lần kiểm chứng UI đầu-cuối đầu tiên. |

## Cấu hình môi trường

- `TEST_BASE_URL`: URL gốc frontend (mặc định `http://localhost:5173`).
- Yêu cầu backend đã cấu hình `OIDC_ISSUER`/`OIDC_CLIENT_ID`/`OIDC_CLIENT_SECRET` trỏ tới một IdP thật (ví dụ Keycloak local) — **đây không phải giá trị mặc định trong `.env.example`** (để trống). Nếu môi trường chạy test chưa cấu hình IdP thật, ca này **không thể thực hiện được** — báo BLOCKED ngay từ bước 1.

## Tiền điều kiện

- Có một IdP OIDC thật đang chạy và đã đăng ký client cho ứng dụng (xem `docs/implement/tasks/T-101_oidc-login.md` phần "Việc cần làm khi D-03 chốt").
- Có một tài khoản người dùng hợp lệ trên IdP đó, và tài khoản này đã được cấp quyền truy cập ứng dụng bằng `python -m app.cli grant-access --email <email> --role user` (xem `backend/app/cli.py`).
- Trình duyệt chưa có cookie phiên nào của ứng dụng (dùng cửa sổ ẩn danh/mới để tránh phiên cũ còn hiệu lực).

## Dữ liệu kiểm thử

- Tài khoản IdP thật: `<email đã được grant-access>` / mật khẩu tương ứng trên IdP.

## Các bước thực hiện

1. Mở trình duyệt ẩn danh, truy cập `${TEST_BASE_URL}`.
2. Quan sát ứng dụng tự động chuyển hướng tới màn hình đăng nhập (`LoginScreen`, nút có `data-testid="login-sso"`).
3. Nhấn nút đăng nhập (`[data-testid="login-sso"]`).
4. Trên trang đăng nhập của IdP, nhập đúng thông tin tài khoản đã chuẩn bị và xác nhận.
5. Chờ IdP chuyển hướng ngược lại ứng dụng.
6. Quan sát ứng dụng hiển thị màn hình chính (thư viện tài liệu), không còn ở màn hình đăng nhập.
7. Mở DevTools → tab Application/Storage → kiểm tra cookie `cwd_sid` tồn tại với cờ `HttpOnly` bật (không đọc được bằng `document.cookie` trong Console).

## Kết quả mong đợi

- KQ1: Truy cập `${TEST_BASE_URL}` khi chưa đăng nhập sẽ được đưa tới màn hình đăng nhập, không vào thẳng được ứng dụng.
- KQ2: Sau khi đăng nhập đúng thông tin trên IdP, người dùng được đưa trở lại ứng dụng và thấy màn hình chính (thư viện tài liệu), không bị kẹt ở màn hình đăng nhập hay báo lỗi.
- KQ3: Cookie phiên (`cwd_sid`) được set với `HttpOnly` — gõ `document.cookie` trong Console của DevTools không trả về giá trị này (không có token nào lộ ra JavaScript).
- KQ4: Không có lỗi nào hiện trên Console trình duyệt liên quan tới luồng đăng nhập.

## Nhiệm vụ của agent thực thi ca kiểm thử này

Khi được giao chạy ca kiểm thử `TC-001`, agent PHẢI:
1. Mở ứng dụng tại `${TEST_BASE_URL}` (giá trị cấu hình ở trên, không hard-code URL khác).
2. Thực hiện tuần tự các bước ở mục "Các bước thực hiện".
3. Chụp màn hình bằng chứng ở từng bước quan trọng (tối thiểu: màn hình đăng nhập ban đầu, trang đăng nhập của IdP, màn hình chính sau khi đăng nhập thành công, và cửa sổ DevTools thể hiện cookie) — lưu `.png` đánh số thứ tự, tên mô tả bước.
4. Đối chiếu từng dòng ở "Kết quả mong đợi" với thực tế quan sát được qua ảnh chụp, chấm PASS/FAIL riêng từng dòng.
5. Viết `report.md` theo đúng mẫu ở [`README.md`](./README.md) của thư mục này.
6. Lưu toàn bộ `report.md` + ảnh chụp vào `./test_reports/TC-001_dang-nhap-oidc-thanh-cong/` (tạo mới nếu chưa có), không ghi vào thư mục của ca khác.
7. Nếu không truy cập được `${TEST_BASE_URL}`, hoặc chưa có IdP thật đã cấu hình (tiền điều kiện không thoả), báo **BLOCKED** kèm lý do cụ thể trong `report.md` — không được kết luận PASS khi chưa thực sự quan sát giao diện.

## Tham chiếu

- [test_plan.md §4.1](../test_plan.md#41-ma-trận-truy-xuất-user-story--ac--task--cấp-độ-kiểm-thử--trạng-thái-hiện-tại)
- User Stories: [User_Stories.md](../../design/User_Stories.md) US-001 (AC-001.1, AC-001.2)
