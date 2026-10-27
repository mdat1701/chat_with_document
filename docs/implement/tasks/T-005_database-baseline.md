# T-005 — Nền tảng cơ sở dữ liệu (migration + RLS)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng; nền cho US-001 – US-021) |
| Module (SADD §2.2.1) | `core` (migration dùng chung cho mọi module) |
| API liên quan | — (nền cho API-01, API-03, API-04, API-07, API-09) |
| Vai trò chính | BE (hỗ trợ: TL) |
| Ước lượng | 2d |
| Phụ thuộc | T-002 (PostgreSQL + extension) |
| Trạng thái | To do |

## 1. Mục tiêu

Tạo schema ban đầu bằng Alembic cho 5 bảng cốt lõi (`app_user`, `user_role`, `document`, `chunk`, `answer`) cùng 2 bảng phụ (`analytics_event`, `audit_log`), đầy đủ chỉ mục theo SADD §3.1.2, và **bật** Row-Level Security trên các bảng có dữ liệu theo chủ sở hữu. Task này chỉ bật RLS và tạo vai trò CSDL; **policy RLS thật và việc đặt `app.user_id` thuộc T-104**.

## 2. Tiêu chí chấp nhận

- `alembic upgrade head` chạy sạch trên CSDL trống và tạo đúng 7 bảng.
- Tên cột khớp **chính xác** sơ đồ ER trong SADD §3.1.1 (xem Mục 3) — sai tên cột sẽ kéo theo sửa dây chuyền ở Sprint 1–4.
- `chunk.embedding` là `vector(1024)`; `chunk.tsv` là cột `GENERATED ... STORED`.
- Đủ 7 chỉ mục/ràng buộc theo SADD §3.1.2.
- RLS đã `ENABLE` trên `document`, `chunk`, `answer`, `feedback`; vai trò ứng dụng **không** có `BYPASSRLS`, vai trò worker **có** `BYPASSRLS`.
- `alembic downgrade -1` hoàn tác được migration (có hàm `downgrade` thật, không `pass`).

## 3. Hợp đồng / cấu hình cụ thể

Schema theo SADD §3.1.1 — **dùng đúng tên cột này**:

```sql
app_user(id uuid PK, oidc_subject text UNIQUE, email citext UNIQUE,
         display_name text, active bool NOT NULL DEFAULT false,
         granted_at timestamptz, revoked_at timestamptz)

user_role(user_id uuid FK -> app_user, role text)      -- user|manager|evaluator|admin

document(id uuid PK, owner_id uuid FK -> app_user, name text,
         size_bytes bigint, page_count int, status text, error_code text,
         blob_key text, sha256 char(64),
         uploaded_at timestamptz, ready_at timestamptz, expires_at timestamptz)

chunk(id bigserial PK, document_id uuid FK -> document, owner_id uuid,  -- denormalized
      ordinal int, page_start int, page_end int, heading_path text,
      content text,
      tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', unaccent(content))) STORED,
      embedding vector(1024))

answer(id uuid PK, owner_id uuid FK -> app_user, conversation_id uuid,
       turn_index int, answer_type text, latency_ms int,
       citation_count int, cited_doc_count int,
       prompt_version text, model_id text, created_at timestamptz)
       -- KHÔNG có cột nội dung câu hỏi/câu trả lời (P-03, US-020)

analytics_event(id, name, ts, user_hash, session_id, app_version, props jsonb)  -- phân vùng theo tháng
audit_log(id, ts, actor_id, action, target_type, target_id, outcome)            -- không chứa tên tệp/nội dung
```

Chỉ mục bắt buộc (SADD §3.1.2):

```sql
CREATE INDEX ON document (owner_id, uploaded_at DESC) WHERE status <> 'deleted';
CREATE UNIQUE INDEX ON document (owner_id, lower(name));
CREATE INDEX ON document (expires_at);
CREATE INDEX ON chunk (owner_id, document_id);              -- B-tree
CREATE INDEX ON chunk USING GIN (tsv);
CREATE INDEX ON answer (owner_id, created_at);
-- HNSW cho chunk.embedding: CHƯA tạo (chỉ bật khi tổng chunk > 2 triệu, ADR-05)
```

Vai trò CSDL:

```sql
-- Ứng dụng: KHÔNG có BYPASSRLS (bắt buộc, nếu không RLS mất tác dụng)
CREATE ROLE cwd_app LOGIN;
-- Worker: có BYPASSRLS, chỉ truy vấn theo document_id tường minh
CREATE ROLE cwd_worker LOGIN BYPASSRLS;
```

## 4. Thay đổi dữ liệu

Toàn bộ task này là thay đổi dữ liệu. Một migration khởi tạo duy nhất (`0001_baseline`), chia theo thứ tự: extension → bảng → chỉ mục → vai trò → `ENABLE ROW LEVEL SECURITY`.

## 5. Các bước triển khai

1. Khởi tạo Alembic trong `backend/`, cấu hình `env.py` đọc `DATABASE_URL` từ `core.config`, hỗ trợ async engine (SQLAlchemy 2).
2. Viết model SQLAlchemy cho 5 bảng cốt lõi, đặt trong `modules/<m>/models.py` tương ứng (`app_user`/`user_role` → `identity`; `document`/`chunk` → `documents`; `answer` → `qa`).
3. Dùng `pgvector.sqlalchemy.Vector(1024)` cho `chunk.embedding`.
4. Khai báo `chunk.tsv` là cột generated bằng `server_default`/`Computed` của SQLAlchemy — **không** tự ghi giá trị từ code ứng dụng.
5. Sinh migration `0001_baseline`, sau đó **sửa tay** để bổ sung: chỉ mục có điều kiện (`WHERE status <> 'deleted'`), chỉ mục hàm (`lower(name)`), GIN trên `tsv`, cột generated — Alembic autogenerate thường bỏ sót các dạng này.
6. Thêm câu lệnh `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` cho `document`, `chunk`, `answer`, `feedback` (bảng `feedback` tạo sẵn ở dạng tối thiểu vì post-MVP, nhưng bật RLS ngay để sau này không quên).
7. Tạo hai vai trò CSDL như Mục 3, cấp quyền tối thiểu (`SELECT/INSERT/UPDATE/DELETE` trên bảng nghiệp vụ, không cấp `SUPERUSER`).
8. Viết hàm `downgrade` thật (drop theo thứ tự ngược).
9. Viết test tích hợp (Testcontainers) kiểm tra: migration chạy xong có đủ bảng/chỉ mục; `rolbypassrls` của `cwd_app` là `false`.
10. Ghi vào README quy ước migration **expand → migrate → contract** (SADD §4.4): không đổi tên/xóa cột trong cùng một bản phát hành.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| **Giá trị `document.status` chưa thống nhất trong SADD** — sơ đồ ER ghi `processing\|ready\|failed`, luồng xóa §3.2.3 dùng thêm `deleting`, chỉ mục §3.1.2 lại lọc `status <> 'deleted'` | Triển khai tập giá trị `processing \| ready \| failed \| deleting`, giữ nguyên chỉ mục theo SADD, và **báo lại Tech Lead để chốt rồi cập nhật SADD** — không tự ý đổi chỉ mục. Trạng thái `uploading` chỉ tồn tại phía client (SDD §3.7.1), không lưu DB |
| Quên bỏ `BYPASSRLS` ở vai trò ứng dụng | RLS vô hiệu, lộ dữ liệu chéo người dùng → test ở Mục 7 phải chặn được |
| `unaccent` chưa được cài khi chạy migration | Cột generated `tsv` tạo thất bại; migration phải `CREATE EXTENSION IF NOT EXISTS unaccent` trước |
| Tạo HNSW ngay từ đầu | **Không tạo** — ADR-05 nêu rõ chỉ bật khi tổng chunk > 2 triệu; tạo sớm làm chậm ghi mà không tăng recall ở quy mô pilot |
| Ai đó thêm cột chứa nội dung vào `answer` | Vi phạm P-03/US-020 — chặn ở code review, nêu rõ trong mô tả PR |

## 7. Kiểm thử bắt buộc

- [ ] `alembic upgrade head` rồi `alembic downgrade -1` rồi `upgrade head` lại — không lỗi
- [ ] Truy vấn `pg_indexes` xác nhận đủ 6 chỉ mục ở Mục 3 (HNSW **không** có mặt)
- [ ] `SELECT rolbypassrls FROM pg_roles WHERE rolname='cwd_app'` trả về `false`
- [ ] Insert một `chunk` rồi kiểm tra `tsv` tự sinh và tìm được bằng truy vấn không dấu (`unaccent`)
- [ ] Insert hai `document` cùng `owner_id` và tên khác hoa/thường (`Bao cao.pdf` / `bao cao.pdf`) → bị chặn bởi unique index

## 8. Định nghĩa Hoàn thành

- [ ] Migration đã merge, chạy tự động trên staging (T-004)
- [ ] Tên cột khớp 100% SADD §3.1.1, có test xác nhận
- [ ] RLS đã bật, vai trò CSDL đúng phân quyền
- [ ] Điểm chưa thống nhất về `document.status` đã được báo cho Tech Lead (ghi trong PR)

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §3.1.1 (ER), §3.1.2 (chỉ mục), §3.1.3 (cô lập dữ liệu), §4.4 (quy ước migration), ADR-04, ADR-05, ADR-06
- [SDD UI/UX v0.3](../../design/SDD_UI_UX_Blueprint.md) §3.7.1 (vòng đời tài liệu phía client)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0 · Task liên quan: [T-104](T-104_owner-scoped-db-access.md) (policy RLS)
