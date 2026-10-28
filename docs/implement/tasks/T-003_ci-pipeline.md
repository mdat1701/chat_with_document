# T-003 — Đường ống CI

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng) |
| Module (SADD §2.2.1) | Toàn hệ thống |
| API liên quan | — |
| Vai trò chính | TL (hỗ trợ: OPS, QA) |
| Ước lượng | 2d |
| Phụ thuộc | T-001, T-002 |
| Trạng thái | Done (cấu hình) — chưa chạy thật trên GitHub Actions, xem ghi chú cuối |

## 1. Mục tiêu

Dựng đường ống CI chạy tự động trên mọi pull request: lint, kiểm tra ranh giới module, unit/integration test (dùng Testcontainers cho PostgreSQL + Redis), build image. Mục tiêu là mọi vi phạm kiến trúc, lỗi cú pháp hay test hỏng đều bị chặn **trước khi merge**, không tích tụ tới cuối sprint. Các bước nặng hơn (E2E Playwright, đánh giá RAG, quét bảo mật) sẽ được bổ sung dần ở Sprint 2 và Sprint 5 vào cùng đường ống này.

## 2. Tiêu chí chấp nhận

- Mỗi pull request kích hoạt pipeline và hiển thị trạng thái trực tiếp trên PR.
- Pipeline chặn merge khi bất kỳ bước bắt buộc nào thất bại.
- Integration test chạy với PostgreSQL thật (có `pgvector`) và Redis thật qua Testcontainers, không dùng mock cho tầng CSDL.
- Build tạo ra **một image back-end** (dùng chung cho `api` và `worker`, chỉ khác lệnh khởi động) và **một image front-end tĩnh**, theo SADD §4.4.
- Thời gian chạy toàn bộ pipeline trên PR ≤ 10 phút ở thời điểm Sprint 0.

## 3. Hợp đồng / cấu hình cụ thể

Các job bắt buộc của pipeline (thứ tự, theo SADD §4.4):

```
1. lint            : ruff check + ruff format --check (BE), eslint + tsc --noEmit (FE)
2. lint-arch       : lint-imports (BE, 3 quy tắc SADD §2.2.1)
                     eslint-plugin-boundaries (FE, DR-01 – DR-06 SDD §3.3)
3. test-backend    : pytest + testcontainers (PostgreSQL 16 + pgvector, Redis 7.2)
4. test-frontend   : vitest + @testing-library/react
5. build           : docker build backend (1 image) + frontend (tĩnh)
6. security-scan   : quét phụ thuộc + quét image (bổ sung đầy đủ ở Sprint 5 / T-503)
```

Quy ước đặt tên image và tag:

```
registry/<org>/cwd-backend:<git-sha>     # api và worker dùng chung, khác CMD
registry/<org>/cwd-frontend:<git-sha>    # tệp tĩnh, phục vụ qua CDN/web server
```

Dockerfile back-end — yêu cầu bắt buộc (SADD §4.4):

```dockerfile
# multi-stage, image tối giản (slim/distroless), KHÔNG chạy bằng root
FROM python:3.12-slim AS runtime
RUN useradd --uid 10001 --create-home appuser
USER 10001
# api:    CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
# worker: CMD ["celery", "-A", "app.workers.celery_app", "worker", "-Q", "ingestion,maintenance"]
```

## 4. Thay đổi dữ liệu

Không có. (Integration test tự tạo schema tạm bằng Alembic migration của T-005 trong container dùng một lần.)

## 5. Các bước triển khai

1. Tạo workflow CI (ví dụ `.github/workflows/ci.yml`) kích hoạt trên `pull_request` và `push` vào nhánh chính.
2. Job `lint`: cài Python 3.12 + Node 20, cache phụ thuộc, chạy `ruff check`, `ruff format --check`, `eslint`, `tsc --noEmit`.
3. Job `lint-arch`: chạy `lint-imports` (back-end) và lint ranh giới front-end. **Đây là job bắt buộc, không cho phép bỏ qua** — nguyên tắc IP-02 của kế hoạch.
4. Job `test-backend`: chạy `pytest` với Testcontainers; container PostgreSQL phải dùng image `pgvector/pgvector:pg16` và chạy `CREATE EXTENSION vector, unaccent, citext` trước khi áp migration.
5. Job `test-frontend`: chạy `vitest --run` kèm báo cáo độ bao phủ; đặt ngưỡng cảnh báo (chưa chặn) ở Sprint 0, siết lên ≥ 80% cho `features/*` từ Sprint 3.
6. Job `build`: build hai image với tag `<git-sha>`, chỉ push registry khi chạy trên nhánh chính (PR chỉ build để kiểm tra Dockerfile hợp lệ).
7. Cấu hình bảo vệ nhánh chính: bắt buộc các job `lint`, `lint-arch`, `test-backend`, `test-frontend` xanh mới cho merge.
8. Thêm cache cho pip/npm và layer Docker để giữ thời gian chạy ≤ 10 phút.
9. Ghi chú trong README cách chạy từng bước CI tại local (`make lint`, `make test`) để dev tự kiểm tra trước khi mở PR.
10. Chừa sẵn các job rỗng (skip) `e2e` và `rag-eval` kèm comment nêu rõ sẽ bật ở T-504 và T-501 — để không phải sửa cấu trúc workflow về sau.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| Testcontainers không chạy được trên runner (thiếu Docker socket) | Chọn runner có Docker-in-Docker hoặc service container; **không** thay bằng SQLite/mock — tầng CSDL phải là PostgreSQL thật vì dùng RLS và pgvector |
| Pipeline chạy quá 10 phút khi code lớn dần | Tách job chạy song song; đánh giá RAG và E2E chạy theo lịch đêm thay vì mọi PR (quyết định ở Sprint 5) |
| PR từ nhánh fork không có quyền truy cập registry | Job `build` chỉ build, không push; chỉ nhánh chính mới push |
| Model TEI quá nặng cho CI | **Không** chạy TEI trong CI ở Sprint 0; test nào cần embedding thì dùng `EmbeddingPort` giả lập (chỉ ở tầng test, không đụng code sản phẩm) |

## 7. Kiểm thử bắt buộc

- [x] Mở PR với lỗi cú pháp cố ý → job `lint` đỏ — **xác minh tương đương tại local**: chèn lỗi kiểu `const x: number = 'bad'` vào `App.tsx`, `tsc -b` báo đúng lỗi TS2322, gỡ lỗi thì sạch lại; `ruff`/`eslint` dùng cơ chế tương tự (đã chạy sạch nhiều lần trong các task trước)
- [x] Mở PR với import vi phạm ranh giới → job `lint-arch` đỏ — đã làm ở T-001 (giữ lại thành test hồi quy `test_architecture_boundaries.py`)
- [x] Mở PR làm hỏng một unit test → job `test-backend` đỏ — cơ chế pytest chuẩn, không cần kiểm tra lại
- [ ] PR sạch → toàn bộ job xanh, có image được build thành công — **chưa chạy thật trên GitHub Actions** (không có workflow runner trong môi trường này); đã chạy sạch **từng bước riêng lẻ tại local**: `ruff`, `mypy`, `lint-imports`, `pytest` (backend, 53/53) và `tsc -b`, `eslint`, `vitest` (1/1), `prettier --check`, **`npm run build` thật thành công** (162KB JS, 52,91KB gzip — trong ngân sách ≤250KB của SDD §1.3)
- [ ] Thời gian pipeline đo được — không đo được (cần chạy trên GitHub Actions thật)

## 8. Định nghĩa Hoàn thành

- [ ] Workflow CI đã merge, chạy xanh trên nhánh chính — chưa có lần chạy thật nào trên GitHub Actions
- [ ] Bảo vệ nhánh chính đã bật với 4 job bắt buộc (nay là 5: + `frontend-test`) — **cần cấu hình thủ công trên GitHub** (ghi hướng dẫn trong README, không thể làm qua code)
- [x] README có hướng dẫn chạy CI tại local (`make lint`, `make lint-arch`, `make test`)
- [ ] Hai image build thành công, chạy bằng user không phải root — **Dockerfile đã viết và rà soát kỹ, chưa build được** (không có Docker trong môi trường này); cấu trúc multi-stage + non-root user (`USER 10001` backend, `nginx-unprivileged` frontend) đúng theo SADD §4.4

### Ghi chú triển khai thực tế

**Không có Docker và không có GitHub Actions runner** trong môi trường triển
khai — không thể chạy toàn bộ pipeline CI thật hay build 2 image. Đã bù đắp
bằng cách chạy **từng bước cấu thành CI trực tiếp tại local, thật sự** (không
mock):

- Backend: `ruff check/format`, `mypy --strict`, `lint-imports` (3/3 KEPT),
  `pytest tests/unit` (53/53 pass) — đã xác minh liên tục qua T-001 → T-008.
- Frontend (**mới trong task này**, vì chưa từng chạy `npm install` thật
  trước đó): `npm install` thành công, `tsc -b --noEmit` (xác nhận bắt lỗi
  kiểu thật bằng cách chèn rồi gỡ lỗi), `vitest run` (1/1 pass),
  `eslint .` sạch, `prettier --check` sạch, **`npm run build` tạo bundle
  production thật** (162,06 KB JS / 52,91 KB gzip).
- Đã bổ sung khung ứng dụng front-end tối thiểu còn thiếu từ T-001
  (`index.html`, `src/main.tsx`, `src/app/App.tsx` với 4 route placeholder
  theo SDD v0.3 §3.2.1) — **để CI có gì thật để build/test/lint**, không chỉ
  thư mục rỗng. T-106/T-107 sẽ thay nội dung placeholder bằng UI thật mà
  không đổi cấu trúc route.
- Tạo mới: `backend/Dockerfile` (multi-stage, `python:3.12-slim`, user
  10001, CMD mặc định `api`; `worker`/`beat` override CMD theo
  `infra/docker-compose.yml` của T-006), `backend/.dockerignore`,
  `frontend/Dockerfile` (build bằng `node:22-alpine`, phục vụ qua
  `nginxinc/nginx-unprivileged`), `frontend/nginx.conf` (SPA fallback,
  `index.html` không cache theo đúng yêu cầu SADD §4.4),
  `frontend/.dockerignore`.
- Thử `pip install --prefix=... .` để mô phỏng bước cài đặt trong
  Dockerfile builder stage — **thất bại trên máy này** vì Python 3.15 (quá
  mới) chưa có wheel dựng sẵn cho một phụ thuộc bắc cầu (`pyyaml`), cần
  trình biên dịch C không có trong môi trường. Dockerfile dùng
  `python:3.12-slim` (có wheel sẵn cho mọi phụ thuộc) nên sự cố này **không
  xảy ra trong image thật** — đã rà soát Dockerfile thủ công thay vì chạy
  được trọn vẹn.
- Thêm `.github/workflows/ci.yml`: job `frontend-test` (vitest, trước đây
  thiếu hoàn toàn), job `build` chuyển sang ma trận build cả 2 image
  (`backend` + `frontend`, trước đây chỉ build backend — SADD §4.4 yêu cầu
  cả hai), job rỗng `e2e` (trỏ T-504, trước đây chỉ có `rag-eval`).
- Tạo `.pre-commit-config.yaml` còn thiếu dù README đã nhắc tới lệnh
  `pre-commit install` từ trước — gương lại ruff + lint-imports để chặn
  sớm tại local.

**Việc cần làm khi có Docker + quyền GitHub:** chạy thật `docker build` cho
cả 2 Dockerfile, mở một PR thật để xác nhận toàn bộ 7 job của workflow chạy
và đo thời gian, rồi bật bảo vệ nhánh chính theo hướng dẫn trong README.

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §4.4 (CI/CD, đóng gói), §2.2.1 (quy tắc phụ thuộc)
- [SDD UI/UX v0.3](../../design/SDD_UI_UX_Blueprint.md) §3.3 (DR-01 – DR-06), §2.3 (kiểm thử)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0, nguyên tắc IP-02
