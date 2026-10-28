# T-001 — Khởi tạo monorepo và ranh giới module

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng) |
| Module (SADD §2.2.1) | Toàn hệ thống |
| API liên quan | — |
| Vai trò chính | TL |
| Ước lượng | 1d |
| Phụ thuộc | — |
| Trạng thái | Done |

## 1. Mục tiêu

Dựng khung thư mục cho cả back-end và front-end theo đúng kiến trúc Modular Monolith + Ports & Adapters (SADD ADR-01, §2.2.1), đồng thời cài công cụ kiểm tra ranh giới module tự động. Khi xong, mọi developer `clone` repo về là có cấu trúc chuẩn, và mọi vi phạm ranh giới module sẽ bị chặn ngay tại máy local lẫn CI thay vì phát hiện muộn khi code đã rối.

## 2. Tiêu chí chấp nhận

- Repo có đủ cây thư mục `backend/app/{api,modules,ports,adapters,workers,core}` và `frontend/src/{app,features,shared}`.
- Mỗi module nghiệp vụ trong `backend/app/modules/` có sẵn `__init__.py` và `service.py` rỗng (điểm vào công khai duy nhất của module).
- Chạy `import-linter` trên code mẫu vi phạm thì **thất bại**; trên code đúng thì **thành công**.
- `pyproject.toml` và `package.json` khai báo đủ phiên bản tối thiểu theo SADD Phụ lục A.
- README gốc mô tả cách chạy back-end, front-end và nơi đọc tài liệu thiết kế.

## 3. Hợp đồng / cấu hình cụ thể

Cấu trúc thư mục bắt buộc (SADD §2.2.1):

```
backend/
  app/
    api/              # Router FastAPI, schema I/O, SSE, dependency auth
    modules/
      identity/       # service.py, models.py, repository.py
      documents/
      ingestion/
      retrieval/
      qa/
      analytics/      # chỉ phần ghi sự kiện US-020; báo cáo tuần là post-MVP
      retention/
      feedback/       # thư mục rỗng — post-MVP, không code trong MVP-lite
      evaluation/     # script offline, không chạy trong sản phẩm
    ports/            # LLMPort, EmbeddingPort, RerankPort, BlobStorePort,
                      # QueuePort, MalwareScanPort, EventBusPort
    adapters/         # bedrock_llm, openai_compat_llm, tei_embedding,
                      # s3_blob, celery_queue, redis_bus, clamav
    workers/          # Định nghĩa task Celery (chỉ gọi use case trong modules)
    core/             # config (DF-01–DF-10), logging có lọc nội dung, OTel, ErrorCode
  tests/
  pyproject.toml
frontend/
  src/
    app/              # router, provider (Query, Auth, i18n), error boundary
    features/{auth,documents,chat}/
    shared/{ui,tokens,api,i18n,validation,config}/
  package.json
docs/                 # đã có
```

Cấu hình `importlinter` (đặt trong `pyproject.toml`) — 3 quy tắc phụ thuộc back-end của SADD §2.2.1:

```toml
[tool.importlinter]
root_package = "app"

[[tool.importlinter.contracts]]
name = "modules chi import ports va core"
type = "forbidden"
source_modules = ["app.modules"]
forbidden_modules = ["app.adapters", "app.api"]

[[tool.importlinter.contracts]]
name = "khong phu thuoc vong giua cac module"
type = "independence"
modules = [
  "app.modules.identity", "app.modules.documents", "app.modules.ingestion",
  "app.modules.retrieval", "app.modules.qa", "app.modules.analytics",
  "app.modules.retention",
]
# Ngoai le duy nhat theo SADD §2.2.1: retrieval doc bang chunk do ingestion ghi
# -> khai bao bang ignore_imports khi phat sinh, kem comment giai thich

[[tool.importlinter.contracts]]
name = "api va workers chi la adapter vao"
type = "layers"
layers = ["app.api | app.workers", "app.modules", "app.ports | app.core"]
```

Front-end dùng `eslint-plugin-boundaries` cho 6 quy tắc DR-01 – DR-06 của SDD §3.3 (cài đặt chi tiết ở T-106, task này chỉ tạo khung thư mục và file cấu hình rỗng).

## 4. Thay đổi dữ liệu

Không có.

## 5. Các bước triển khai

1. Tạo cây thư mục như Mục 3; mỗi thư mục Python có `__init__.py`, mỗi module nghiệp vụ có thêm `service.py` rỗng kèm docstring nêu trách nhiệm module (copy từ bảng SADD §2.2.1).
2. Khởi tạo `backend/pyproject.toml`: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, Celery 5.4, `import-linter`, `ruff`, `pytest`, `pytest-asyncio`, `testcontainers`.
3. Khởi tạo `frontend/package.json` bằng Vite + React 18 + TypeScript; thêm TanStack Query, Zustand, React Router, Radix UI, `react-markdown`, `rehype-sanitize`, `vitest`, `@testing-library/react`, `eslint-plugin-boundaries`.
4. Thêm cấu hình `import-linter` ở Mục 3 vào `pyproject.toml`; thêm script `make lint-arch` chạy `lint-imports`.
5. Thêm `ruff` (lint + format) cho back-end và `eslint` + `prettier` cho front-end, cùng cấu hình `.editorconfig` chung.
6. Viết 2 file test mẫu chứng minh ranh giới hoạt động: một file trong `app/modules/documents` import `app.adapters.s3_blob` (phải bị chặn) để chạy thử rồi **xóa đi**, ghi lại kết quả vào PR.
7. Viết `README.md` gốc: cách chạy, cấu trúc thư mục, liên kết tới `docs/requirements/SADD.md` và `docs/implement/implement_plan.md`.
8. Thêm `.gitignore` cho Python, Node, và thư mục dữ liệu local (`.venv`, `node_modules`, `data/`).

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| `retrieval` cần đọc bảng `chunk` do `ingestion` ghi | Được phép (ngoại lệ duy nhất trong SADD §2.2.1), khai báo `ignore_imports` kèm comment, không nới lỏng quy tắc chung |
| Module cần gọi module khác | Chỉ qua `modules/<m>/service.py`, không import trực tiếp `repository.py` hay `models.py` của module khác |
| Dev thêm module mới | Phải bổ sung vào danh sách `independence` trong `pyproject.toml`, nếu không CI sẽ không kiểm tra module đó |

## 7. Kiểm thử bắt buộc

- [x] `lint-imports` chạy xanh trên code khung hiện tại (3 kept, 0 broken)
- [x] Thêm tạm import vi phạm (`modules` → `adapters`) thì `lint-imports` báo đỏ với thông báo chỉ rõ file vi phạm — giữ lại thành `tests/unit/test_architecture_boundaries.py` để không hồi quy
- [x] `ruff check` và `ruff format --check` chạy xanh (back-end). `eslint`/`prettier` front-end **chưa chạy được** — cần `npm install` (không có mạng/Node modules trong môi trường xác minh này); cấu hình đã có, sẽ xác minh ở T-106
- [x] `pytest` chạy được — `mypy app` (strict) cũng sạch, dù không bắt buộc ở bước này

## 8. Định nghĩa Hoàn thành

- [x] Toàn bộ cây thư mục Mục 3 tồn tại trong repo
- [x] `make lint-arch` có trong Makefile (T-003 sẽ đưa vào CI — `ci.yml` đã có sẵn job `boundaries` từ trước, chạy `lint-imports` trực tiếp)
- [x] README gốc mô tả đủ cách chạy và liên kết tài liệu (đã có sẵn, không cần sửa)
- [x] Không có bí mật (secret) nào được commit

### Lệch so với mô tả ban đầu / phát hiện khi triển khai

- `root_package` của import-linter nằm trong `backend/pyproject.toml`, không phải `pyproject.toml` gốc repo — chỉnh đường dẫn tương ứng khi chạy `lint-imports` (CI/Makefile đã `cd backend` trước khi gọi).
- Quy tắc `ignore_imports` cho ngoại lệ `retrieval → ingestion` đã bị **comment tạm** vì `ingestion/models.py` và `retrieval/repository.py` chưa tồn tại (import-linter từ chối `ignore_imports` trỏ tới module không có thật) — **bật lại ở T-203/T-302** khi 2 file đó được tạo.
- Repo đã có sẵn `.github/workflows/ci.yml`, `README.md`, `.github/CODEOWNERS`, `pull_request_template.md` từ trước (không phải do T-001 tạo). Đã sửa 1 chỗ lệch: comment `T-309` (số hiệu task cũ) trong `ci.yml` và ví dụ `T-201` trong PR template → đổi thành `T-501`/`T-108` cho khớp danh mục task hiện tại.
- Thêm `mypy` vào `dev` extras và `tool.mypy` (strict) vì `ci.yml` có job `typecheck` gọi `mypy app` nhưng T-001 gốc không liệt kê — cần để CI không đỏ ngay từ task đầu.
- Thêm `tests/unit`, `tests/integration`, `tests/isolation` (CI chạy tách `-m isolation`) và marker `isolation` trong `pyproject.toml` vì `ci.yml` đã tham chiếu các đường dẫn này.
- Thêm script `format:check`, `typecheck` vào `frontend/package.json` (CI gọi `npm run format:check`/`npm run typecheck` nhưng chưa có).

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §2.2.1 (cấu trúc module, quy tắc phụ thuộc), Phụ lục A (bảng công nghệ), ADR-01, ADR-02
- [SDD UI/UX v0.3](../../design/SDD_UI_UX_Blueprint.md) §3.1 (cấu trúc front-end), §3.3 (DR-01 – DR-06)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0, nguyên tắc IP-02
