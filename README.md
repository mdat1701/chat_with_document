# Chat với tài liệu (MVP)

Hỏi đáp có trích dẫn trên tài liệu PDF của người dùng. Tài liệu: [yêu cầu](docs/requirements), [thiết kế](docs/design), [kế hoạch và task](docs/implement/implement_plan.md).

## Bắt đầu
```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cd ../frontend && npm ci
pre-commit install
```
## Hạ tầng cục bộ (T-002)

```bash
cp .env.example .env         # sửa giá trị nếu cổng mặc định bị chiếm
make up                      # PostgreSQL+pgvector, Redis, MinIO, ClamAV, TEI
make smoke-infra             # xác nhận cả 5 dịch vụ đã sẵn sàng
```

- Yêu cầu RAM tối thiểu ~6GB rảnh (TEI + ClamAV là hai dịch vụ nặng nhất).
- Lần đầu chạy TEI sẽ tải mô hình `BAAI/bge-m3` (~2GB) — có thể mất vài phút, `docker compose up --wait` sẽ chờ tới khi healthcheck xanh thay vì báo lỗi sớm.
- ClamAV cũng cần vài phút đầu để tải chữ ký virus (`freshclam`) trước khi healthcheck xanh.
- `make down` để tắt, `make reset-db` để xóa sạch dữ liệu Postgres và tạo lại từ đầu, `make logs` để xem log trực tiếp.

## Migration CSDL (T-005)

```bash
cd backend && alembic upgrade head      # áp toàn bộ migration
cd backend && alembic downgrade -1      # lùi một bước
```

Quy ước **expand → migrate → contract** (SADD §4.4): không đổi tên hay xóa cột
trong cùng một bản phát hành. Thêm cột mới ở bản phát hành này (expand), chuyển
dữ liệu/đọc-ghi sang cột mới ở bản sau (migrate), chỉ xóa cột cũ khi không còn
code nào đọc nó (contract, thường cách ít nhất một bản phát hành).

## CI (T-003)

Trước khi mở PR, chạy tại local đúng những gì CI chạy:

```bash
make lint        # ruff + eslint + prettier --check
make lint-arch   # import-linter (back-end) — xem T-106 cho phần front-end
make test        # pytest (trừ test cô lập) + vitest
```

Pipeline đầy đủ (`.github/workflows/ci.yml`): `lint` → `typecheck` → `boundaries`
→ `backend-test` (Testcontainers PostgreSQL+pgvector/Redis thật) →
`frontend-test` (vitest) → `sca`/`sast` (song song) → `build` (image `backend`
+ `frontend`, quét Trivy). `e2e` và `rag-eval` là job rỗng, bật ở T-504/T-501.

**Bảo vệ nhánh chính** (cấu hình thủ công trên GitHub, không nằm trong code):
Settings → Branches → bật "Require status checks to pass" cho `lint`,
`typecheck`, `boundaries`, `backend-test`, `frontend-test` trước khi cho phép
merge vào `main`.
