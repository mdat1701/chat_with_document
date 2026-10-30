# Báo cáo thực thi — TC-001 Đăng nhập OIDC thành công, vào được ứng dụng

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T22:55:00+07:00 (lần chạy cuối, sau khi dựng hạ tầng thật + sửa lỗi) |
| URL đã test | `http://localhost:5173` (frontend Vite dev) → proxy → `http://localhost:8000` (backend `uvicorn`, Postgres 17 thật qua winget, mock OIDC IdP cục bộ) |
| Môi trường | Chromium (Playwright 1.64.1, headless, cờ `--unsafely-treat-insecure-origin-as-secure` để chấp nhận cookie `Secure` qua HTTP cục bộ); PostgreSQL 17 thật (không có pgvector), Redis giả lập (`fakeredis` TCP), ClamAV giả lập (giao thức `zINSTREAM`, luôn OK), TEI giả lập (embedding/rerank theo từ khóa), OIDC IdP giả lập (RS256 JWT thật, tự ký) |
| Kết luận chung | **PASS** (lần đầu tiên trong dự án — xác nhận bằng chạy thật, không chỉ đọc code) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Ảnh minh chứng |
|---|---|---|---|---|
| KQ1 | Truy cập `${TEST_BASE_URL}` khi chưa đăng nhập → đưa tới màn hình đăng nhập | `GET /api/v1/me` trả 401, hiển thị đúng màn hình "Chat với tài liệu / Đăng nhập bằng tài khoản công ty để bắt đầu" | **PASS** | [01_truy-cap-ban-dau.png](./01_truy-cap-ban-dau.png) |
| KQ2 | Sau khi đăng nhập đúng trên IdP → quay lại ứng dụng, thấy màn hình chính | Nhấn "Đăng nhập" → chuyển hướng qua mock IdP → IdP phát `id_token` RS256 → backend xác minh chữ ký + claims (`iss`/`aud`/`exp`) qua `AuthlibOIDCAdapter` thật → tạo session → redirect về `/` → **thấy đúng "SCR-02 Thư viện tài liệu"**, tên người dùng "tester" ở góc phải, bộ đếm tài liệu `0/50`, composer hỏi đáp sẵn sàng | **PASS** | [02_man-hinh-chinh-sau-dang-nhap.png](./02_man-hinh-chinh-sau-dang-nhap.png) |
| KQ3 | Cookie `cwd_sid` có `HttpOnly`, không đọc được qua `document.cookie` | `cookie_check.json`: `jsCookie` không chứa `cwd_sid`; cookie jar thật (qua Playwright API, tương đương DevTools) xác nhận `cwd_sid` tồn tại với `httpOnly: true`, `secure: true`, `sameSite: Lax` | **PASS** | [cookie_check.json](./cookie_check.json) |
| KQ4 | Không có lỗi lạ trên Console liên quan luồng đăng nhập | Chỉ còn 4× `401` ở bước tải trang lần đầu (đúng thiết kế — xảy ra trước khi có session), không còn lỗi `503`/`404` nào sau khi đăng nhập | **PASS** | — (xem `NETWORK_LOG` trong log chạy) |

## Ghi chú / Sai lệch

Lần chạy đầu của ca này (xem lịch sử git/ghi chú trước) kết luận **BLOCKED** vì sandbox không có Postgres/Redis/IdP thật. Theo yêu cầu, đã dựng một bộ hạ tầng thật tối thiểu ngay trong phiên này để kiểm chứng thay vì dừng lại ở BLOCKED:

- **PostgreSQL 17 thật** cài qua `winget` (không có pgvector — thiếu C++ Build Tools để biên dịch, người dùng đã quyết định không cài thêm Visual Studio Build Tools). Dùng một migration chạy thử **cục bộ, không commit** thay cột `Vector(1024)` bằng `TEXT` và bỏ qua `CREATE EXTENSION vector` — chỉ để kiểm chứng phần không liên quan tới vector (đăng nhập, danh sách tài liệu rỗng). Mọi tính năng cần vector thật (truy xuất/hỏi đáp có ý nghĩa) **vẫn chưa được kiểm chứng bằng ca này**.
- **Redis**: `fakeredis` chạy ở chế độ TCP server thật trên cổng 6379 (không phải mock trong test Python, mà một tiến trình riêng nói đúng giao thức Redis).
- **ClamAV**: một server giả lập giao thức `zINSTREAM`, luôn trả `OK`.
- **TEI**: một server giả lập `/embed`/`/rerank` (vector túi-từ băm, không phải mô hình thật) — đủ để API không crash, **không đại diện cho chất lượng embedding/rerank thật**.
- **OIDC IdP**: một mock IdP tự ký JWT RS256 thật (không phải giả lập trong code backend — `AuthlibOIDCAdapter` thật của ứng dụng chạy nguyên vẹn, xác minh chữ ký/claims thật qua JWKS) — mô phỏng đúng *giao thức*, nhưng **không xác thực danh tính thật** (mọi `/authorize` đều tự động "đăng nhập" thành công).

**4 lỗi hạ tầng/migration THẬT phát hiện và đã sửa trong mã nguồn chính (không phải chỉ ở bản vá cục bộ) trong lúc dựng môi trường này — tất cả đều chưa từng lộ ra vì chưa ai chạy migration trên Postgres thật:**

1. `migrations/versions/0001_baseline.py`: cột tính toán `tsv` dùng `unaccent(content)` trực tiếp trong `GENERATED ALWAYS ... STORED` — Postgres từ chối vì `unaccent()` của contrib khai báo `STABLE`, không phải `IMMUTABLE` (bắt buộc cho cột generated). **Đã sửa**: thêm hàm bọc `immutable_unaccent()` khai báo `IMMUTABLE` tường minh.
2. `migrations/versions/0001_baseline.py` + `0003_document_name_lifecycle.py`: `op.create_index(..., ["owner_id", "lower(name)"])` hoặc `sa.text("lower(name)")` bị cơ chế `_textual_index_column` của Alembic (bản cài trong môi trường này: Alembic 1.20.1 + SQLAlchemy 2.1.6) render sai thành tên cột theo nghĩa đen `"lower(name)"` thay vì biểu thức SQL — lỗi `column "lower(name)" does not exist`. **Đã sửa**: chuyển cả 2 chỉ mục sang `op.execute()` với SQL thô, bỏ qua hẳn cơ chế dễ vỡ này.
3. `migrations/versions/0001_baseline.py`: `GRANT SELECT, INSERT, UPDATE, DELETE` trên các bảng cho `cwd_app`/`cwd_worker` **không** tự kèm quyền trên các sequence ẩn của cột `BIGSERIAL` (`chunk.id`, `analytics_event.id`, `audit_log.id`) — bất kỳ `INSERT` nào bằng vai trò `cwd_app` thật (không phải `postgres` superuser) đều lỗi `permission denied for sequence ...` ngay ở `nextval()`. **Đã sửa**: thêm `GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cwd_app, cwd_worker`.
4. **(Mức FE, lỗi nghiêm trọng nhất, đúng trọng tâm US-001/AC-001.2 mà ca TC-001 này nhắm tới)**: `frontend/src/features/auth/AuthScreens.tsx` tính `return_to` bằng `window.location.pathname` tại thời điểm bấm nút — nhưng vì route `/` tự động điều hướng người dùng chưa đăng nhập sang `/login` (và `/login` render `LoginScreen` **vô điều kiện**, không kiểm tra trạng thái đăng nhập), nên trường hợp phổ biến nhất (người dùng mới mở app lần đầu) luôn có `window.location.pathname === "/login"` tại lúc bấm nút. Hậu quả: sau khi đăng nhập **thành công thật sự** (OIDC round-trip đúng, session hợp lệ), backend đưa trình duyệt quay lại đúng `/login` theo đúng `return_to` đã gửi — và vì route này không kiểm tra `user`, người dùng **kẹt ở màn hình đăng nhập**, còn thấy banner "Phiên đăng nhập đã hết hạn" gây hiểu lầm (do cờ `cwd_session_started` trong `sessionStorage` vừa được set true bởi chính lần tải `/me` thành công đó). **Đây là lỗi 100% không thể phát hiện bằng đọc code hay test component đơn lẻ (`AuthScreens.test.tsx` cũ chỉ test render tĩnh, không test hành vi bấm nút theo route) — chỉ lộ ra khi chạy thật một vòng OIDC đầu-cuối**, đúng là lý do TC-001 được thiết kế. **Đã sửa**: nếu `pathname === "/login"` thì dùng `"/"` làm `return_to` thay vì gửi lại chính `/login`. Thêm 2 test hồi quy trong `AuthScreens.test.tsx` xác nhận cả hai nhánh (từ `/login` → `return_to=/`, từ route khác → giữ nguyên).

**2 lỗi cấu hình hạ tầng dev đã sửa trước đó (ghi nhận lại, xem lịch sử git):**
5. `frontend/vite.config.ts` thiếu proxy `/auth` → backend.
6. `frontend/vite.config.ts` proxy `/auth` ban đầu dùng `changeOrigin: true`, khiến `request.url_for()` phía backend tính `redirect_uri` theo `Host: localhost:8000` thay vì origin frontend — trình duyệt bị đưa thẳng sang cổng 8000 (không phục vụ SPA) sau khi đăng nhập xong. Đã đổi sang `changeOrigin: false` cho riêng rule `/auth` (giữ nguyên `true` cho `/api`).
7. `infra/k8s/staging/ingress.yaml` thiếu path `/auth` → `cwd-api` — lỗi tương tự (4) sẽ xảy ra trên staging thật nếu không sửa.

Xác nhận toàn bộ thay đổi mã nguồn (migration + FE) bằng `ruff check`, `mypy`, `lint-imports`, `pytest` (175 passed, 13 skipped — không đổi số lượng pass/fail so với trước, chỉ sửa lỗi chưa từng được test nào chạm tới) và `tsc`, `eslint`, `prettier`, `npm run build`, `vitest` (108 passed, tăng từ 106 nhờ 2 test hồi quy mới).

**Giới hạn còn lại của ca này (trung thực, không phóng đại):** môi trường dùng để đạt PASS này là Postgres **không có pgvector thật** + Redis/ClamAV/TEI/IdP đều là **stub tự viết cho phiên làm việc này**, không phải hạ tầng production. PASS ở đây xác nhận đúng **luồng/kiến trúc đăng nhập** (OIDC Authorization Code + PKCE, xác minh JWT thật, session HttpOnly+Secure, RLS binding `app.user_id`) hoạt động đúng khi có đủ hạ tầng — không xác nhận được hành vi với một IdP doanh nghiệp thật (Keycloak/Okta) hay dữ liệu vector thật. Cần chạy lại trên staging/CI thật (Testcontainers + IdP thật, D-03) trước khi coi đây là bằng chứng đầy đủ cho Pilot Gate G-01/G-07.
