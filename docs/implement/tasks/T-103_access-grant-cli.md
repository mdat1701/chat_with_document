# T-103 — Cấp và thu hồi quyền truy cập bằng CLI/config

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 1 |
| Story | US-023 (Cấp quyền truy cập — CLI/config trong MVP-lite) |
| Epic | EP-01 — Truy cập và phân quyền |
| Module (SADD §2.2.1) | `identity` |
| API liên quan | — (không có API quản trị trong MVP-lite; API-10 trở đi là post-MVP) |
| Vai trò chính | BE (người dùng cuối: Admin / vận hành pilot) |
| Ước lượng | 1d |
| Phụ thuộc | T-005 (schema `app_user`, `user_role`), T-101 (cơ chế session Redis) |
| Trạng thái | To do |

## 1. Mục tiêu

Cung cấp công cụ dòng lệnh để người vận hành pilot cấp / thu hồi / liệt kê quyền truy cập **mà không cần xây màn hình quản trị** (BRD §5.0, PRD ASM-P03: "có thể cấp quyền bằng cấu hình/CLI trong giai đoạn pilot"). Thu hồi quyền phải có hiệu lực **ngay ở request kế tiếp**, không chờ phiên hết hạn.

> Màn hình quản trị (trước đây là SCR-06) và API `POST/PATCH /admin/users` là **post-MVP** — không làm trong task này.

## 2. Tiêu chí nghiệm thu liên quan

| Mã AC | Nội dung |
|---|---|
| AC-023.1 | *Given* quản trị viên đã đăng nhập, *When* thêm tài khoản của một người dùng vào danh sách được cấp quyền, *Then* người dùng đó đăng nhập được ngay ở lần thử tiếp theo |
| AC-023.2 | *Given* một người dùng đang có quyền, *When* quản trị viên thu hồi quyền, *Then* người dùng không thực hiện được thao tác nào ở lần yêu cầu tiếp theo |
| AC-023.3 `[Đề xuất]` | Xác nhận trước khi thu hồi — trong MVP-lite áp dụng bằng cờ `--yes` bắt buộc trên CLI thay cho hộp thoại UI |

## 3. Giao diện dòng lệnh

```bash
# Cấp quyền (tạo mới hoặc kích hoạt lại tài khoản đã thu hồi)
python -m app.cli grant-access --email user@company.com --role user

# Thu hồi quyền (bắt buộc --yes để tránh nhầm, thay cho hộp xác nhận UI)
python -m app.cli revoke-access --email user@company.com --yes

# Liệt kê người dùng thử nghiệm
python -m app.cli list-users [--active-only]
#  EMAIL                     ROLES   ACTIVE  GRANTED_AT           LAST_LOGIN
#  minhanh.le@example.com    user    true    2026-11-03 09:12     2026-11-05 14:03

# Nạp hàng loạt từ tệp cấu hình (một email mỗi dòng, hoặc YAML email+role)
python -m app.cli sync-access --file ./config/pilot-users.yaml
```

Mã thoát: `0` thành công · `1` lỗi đầu vào (email sai định dạng, role không hợp lệ) · `2` lỗi hệ thống (không kết nối được DB/Redis).

## 4. Thay đổi dữ liệu

| Bảng / key | Thay đổi |
|---|---|
| `app_user` | `grant-access`: upsert theo `email` → `active=true`, `granted_at=now()`, `revoked_at=null`. `revoke-access`: `active=false`, `revoked_at=now()` (**không xóa bản ghi** — giữ để truy vết) |
| `user_role` | Thêm hàng `(user_id, role)` nếu chưa có; role hợp lệ: `user`, `manager`, `evaluator`, `admin` (MVP-lite thực tế chỉ dùng `user`) |
| `sessions_by_user:{user_id}` + `session:{sid}` (Redis) | `revoke-access`: đọc SET, `DEL` toàn bộ `session:{sid}`, rồi `DEL` chính SET — đảm bảo AC-023.2 |
| `audit_log` | Ghi `access_granted` / `access_revoked` với `actor_id` (người chạy CLI, lấy từ biến môi trường `CWD_CLI_ACTOR` hoặc `system`), `target_type='app_user'` |

## 5. Các bước triển khai

1. Tạo module `app/cli.py` dùng `typer` hoặc `argparse`, đăng ký entrypoint `python -m app.cli`.
2. `grant-access`:
   - Validate email (RFC đơn giản) và role nằm trong tập hợp lệ.
   - Upsert `app_user` theo `citext email` (unique). `oidc_subject` để `null` — sẽ được T-101 điền ở lần đăng nhập đầu tiên.
   - Insert `user_role` nếu chưa tồn tại (idempotent, `ON CONFLICT DO NOTHING`).
   - In ra kết quả rõ ràng: `✓ Đã cấp quyền user@company.com (role=user)`.
3. `revoke-access`:
   - Bắt buộc cờ `--yes`; thiếu thì in cảnh báo kèm email và thoát mã `1` (thay cho hộp xác nhận AC-023.3).
   - Trong **một transaction**: `UPDATE app_user SET active=false, revoked_at=now()`.
   - Sau commit: đọc `sessions_by_user:{user_id}`, xóa từng `session:{sid}`, rồi xóa SET. Thực hiện bằng pipeline Redis để tránh nhiều round-trip.
4. `list-users`: truy vấn join `app_user` + `user_role`, in bảng cột cố định; `--active-only` lọc `active=true`.
5. `sync-access`: đọc YAML `{email, role}`; cấp quyền cho email mới, thu hồi cho email **không còn** trong tệp (in danh sách sẽ thu hồi và hỏi xác nhận trừ khi có `--yes`).
6. Ghi `audit_log` cho mọi lệnh ghi; log mức INFO số bản ghi bị tác động (không ghi email vào log tập trung — chỉ `user_hash`; email chỉ hiển thị trên stdout cho người vận hành).
7. Bọc bằng `Makefile` để người vận hành không cần nhớ cú pháp:
   ```make
   grant-access:   ## make grant-access EMAIL=... [ROLE=user]
   	python -m app.cli grant-access --email $(EMAIL) --role $(or $(ROLE),user)
   ```
8. Viết hướng dẫn ngắn trong `README` vận hành: cách chạy CLI trong pod/container của môi trường staging và prod.

## 6. Mã lỗi & trường hợp biên

| Tình huống | Hành vi |
|---|---|
| Email sai định dạng / role không hợp lệ | Thoát mã `1`, in lỗi rõ ràng, không chạm DB |
| `grant-access` cho email đã tồn tại và `active=true` | Idempotent — in `= Không thay đổi`, thoát `0` |
| `grant-access` cho tài khoản đã bị thu hồi | Kích hoạt lại: `active=true`, `revoked_at=null`, giữ nguyên `oidc_subject` và lịch sử |
| `revoke-access` cho email không tồn tại | Thoát mã `1`, thông báo không tìm thấy (không tạo bản ghi) |
| Người dùng bị thu hồi đang mở SSE (`/documents/events`) | Kết nối SSE hiện tại sẽ lỗi ở lần kiểm tra phiên kế tiếp; UI xử lý như `SESSION_EXPIRED` |
| Redis không sẵn sàng khi thu hồi | **Rollback không được** (DB đã commit) → thoát mã `2` kèm cảnh báo to: "Quyền đã thu hồi trong CSDL nhưng chưa xóa được phiên — chạy lại lệnh khi Redis sẵn sàng". Lệnh phải chạy lại an toàn (idempotent) |

## 7. Kiểm thử bắt buộc

- [ ] `grant-access` cho email mới → `app_user.active=true`; tài khoản đó đăng nhập OIDC thành công ngay lần thử kế tiếp (AC-023.1)
- [ ] `revoke-access --yes` khi người dùng **đang có phiên mở** → request kế tiếp của người đó trả 401, không phải chờ TTL (AC-023.2)
- [ ] `revoke-access` thiếu `--yes` → thoát mã `1`, DB không đổi (AC-023.3)
- [ ] Chạy `grant-access` hai lần liên tiếp → không tạo bản ghi trùng, không lỗi (idempotent)
- [ ] Thu hồi rồi cấp lại → người dùng đăng nhập được, `oidc_subject` cũ được giữ nguyên
- [ ] `list-users` hiển thị đúng trạng thái sau mỗi thao tác
- [ ] Mỗi thao tác ghi đúng một dòng `audit_log`, không chứa nội dung tài liệu

## 8. Định nghĩa Hoàn thành

- [ ] 3 AC của US-023 đạt ở mức CLI (không có UI — đúng phạm vi MVP-lite)
- [ ] Lệnh chạy được trong container của `staging` và `prod` với tài liệu hướng dẫn kèm theo
- [ ] Tất cả lệnh ghi đều idempotent và có `audit_log`
- [ ] Test tích hợp chạy trong CI với Testcontainers (PostgreSQL + Redis)

## 9. Tham chiếu

[`../../requirements/SADD.md`](../../requirements/SADD.md) §2.2.1 (`identity`), §2.4.2 (ghi chú API-10 trở đi là post-MVP), §3.1.1 (`app_user`, `user_role`) · [`../../design/User_Stories.md`](../../design/User_Stories.md) US-023 · [`../../requirements/BRD.md`](../../requirements/BRD.md) §5.0 · [`../implement_plan.md`](../implement_plan.md) §5 Sprint 1
