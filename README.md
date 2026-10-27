# Chat với tài liệu (MVP)

Hỏi đáp có trích dẫn trên tài liệu PDF của người dùng. Tài liệu: [yêu cầu](docs/requirements), [thiết kế](docs/design), [kế hoạch và task](docs/implement/implement_plan.md).

## Bắt đầu
```bash
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
cd ../frontend && npm ci
pre-commit install
```
Môi trường `local` đầy đủ (PostgreSQL, Redis, MinIO, TEI...) xem `infra/` sau T-002.
