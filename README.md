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
