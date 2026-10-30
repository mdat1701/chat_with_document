# Báo cáo thực thi — TC-002 Màn hình "chưa được cấp quyền" cho người dùng không có quyền

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T22:59:00+07:00 |
| URL đã test | `http://localhost:5173` (qua mock IdP tại `http://127.0.0.1:9999`, tài khoản `noaccess@example.com` — KHÔNG chạy `grant-access`) |
| Môi trường | Như TC-001 (Postgres 17 thật không pgvector + Redis/ClamAV/TEI/IdP giả lập cho phiên này) |
| Kết luận chung | **PASS** (chạy thật qua round-trip OIDC đầy đủ, không phải chỉ xem component tĩnh như lần trước) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Đăng nhập bằng tài khoản chưa cấp quyền → thấy `NoAccessScreen`, không vào được thư viện | Đăng nhập qua IdP thật (tài khoản `noaccess@example.com`, chưa từng `grant-access`) → backend (`app/api/routers/auth.py::auth_callback`) gọi `complete_login()`, nhận `outcome.decision != ALLOWED` → **không tạo session**, redirect `302` tới `/no-access` → hiển thị đúng "Chưa được cấp quyền" | **PASS** | [01_sau-dang-nhap-tai-khoan-chua-cap-quyen.png](./01_sau-dang-nhap-tai-khoan-chua-cap-quyen.png) |
| KQ2 | Thông điệp rõ ràng bằng tiếng Việt, không lộ thông tin kỹ thuật | "Chưa được cấp quyền" / "Tài khoản của bạn chưa được bật quyền truy cập." — không mã lỗi, không stack trace | **PASS** | [01_sau-dang-nhap-tai-khoan-chua-cap-quyen.png](./01_sau-dang-nhap-tai-khoan-chua-cap-quyen.png) |
| KQ3 | Không có cách nào từ màn hình này gọi API trả về dữ liệu tài liệu | `NETWORK_LOG` của lần chạy: không có request nào tới `/api/v1/documents*`; không có cookie `cwd_sid` nào được set (đúng — backend không tạo session khi `decision != ALLOWED`) | **PASS** | — (dựa trên network log ghi lại trong lúc chạy) |

## Ghi chú / Sai lệch

Khác với lần chạy trước (BLOCKED, chỉ xem `NoAccessScreen` render tĩnh qua route trực tiếp), lần này đã chạy **đúng kịch bản thật theo mô tả US-001 AC-001.3/.4**: một tài khoản hợp lệ trên IdP nhưng chưa được cấp quyền trong ứng dụng, đi hết vòng OIDC (authorize → token → verify JWT → `complete_login` từ chối → redirect `/no-access`), không có bước nào giả lập hay bỏ qua ở tầng ứng dụng.

Lưu ý kỹ thuật khi chạy: phải **khởi động lại backend** giữa TC-001 (tài khoản `tester@example.com`, đã `grant-access`) và TC-002 (tài khoản `noaccess@example.com`) — vì `AuthlibOIDCAdapter` cache `discovery`/`jwks` theo `@lru_cache` suốt vòng đời tiến trình; đổi IdP giả lập (keypair RSA mới mỗi lần khởi động) mà không khởi động lại backend sẽ khiến xác minh JWT thất bại với JWKS cũ. Đây là đặc điểm của môi trường thử nghiệm (nhiều IdP giả lập nối tiếp), không áp dụng khi dùng một IdP thật cố định.

**Giới hạn còn lại:** vẫn dùng IdP giả lập (không phải Keycloak/Okta thật) — xác nhận đúng *logic quyết định cấp quyền* phía ứng dụng, chưa xác nhận hành vi với một IdP doanh nghiệp thật.
