# T-002 — Môi trường phát triển cục bộ (Docker Compose)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng) |
| Module (SADD §2.2.1) | Toàn hệ thống (tầng hạ tầng dữ liệu SADD §2.3) |
| API liên quan | — |
| Vai trò chính | OPS (hỗ trợ: TL) |
| Ước lượng | 2d |
| Phụ thuộc | T-001 |
| Trạng thái | Done (cấu hình) — chưa chạy được Docker thật, xem ghi chú cuối |

## 1. Mục tiêu

Cho phép mỗi developer chạy toàn bộ phụ thuộc hạ tầng của hệ thống trên máy cá nhân bằng một lệnh `docker compose up`, không cần kết nối tới staging. Đây là điều kiện bắt buộc để các task Sprint 1–4 (ingestion, embedding, truy xuất vector) phát triển và kiểm thử được tại local. Khi xong, `docker compose ps` hiển thị 5 dịch vụ khỏe mạnh và back-end kết nối được tới cả 5.

## 2. Tiêu chí chấp nhận

- `docker compose up -d` khởi động thành công PostgreSQL 16 + pgvector, Redis 7.2, MinIO, ClamAV, TEI (bge-m3) trên máy không có GPU.
- PostgreSQL đã bật sẵn extension `vector` và `unaccent`.
- MinIO có sẵn bucket riêng tư mặc định cho tài liệu, chặn truy cập công khai.
- TEI trả về vector 1024 chiều khi gọi thử endpoint embed.
- ClamAV nhận được lệnh quét qua TCP (`clamd`) và nhận diện đúng chuỗi thử EICAR.
- Có file `.env.example` liệt kê đầy đủ biến môi trường; `.env` thật không bị commit.

## 3. Hợp đồng / cấu hình cụ thể

`docker-compose.yml` (rút gọn, các giá trị cụ thể do OPS chốt):

```yaml
services:
  postgres:            # SADD §2.3 — CSDL chính
    image: pgvector/pgvector:pg16
    environment: [POSTGRES_DB=cwd, POSTGRES_USER=cwd, POSTGRES_PASSWORD=...]
    ports: ["5432:5432"]
    volumes: ["./data/pg:/var/lib/postgresql/data",
              "./infra/pg-init:/docker-entrypoint-initdb.d"]
    healthcheck: pg_isready -U cwd

  redis:               # broker Celery + pub/sub trạng thái + phiên + rate limit
    image: redis:7.2
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
    ports: ["6379:6379"]

  minio:               # kho tệp S3-compatible (PDF gốc)
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]

  clamav:              # quét mã độc bước 1 của pipeline ingestion
    image: clamav/clamav:stable
    ports: ["3310:3310"]

  tei:                 # embedding noi bo — van ban KHONG roi TB-2
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.5
    command: ["--model-id", "BAAI/bge-m3"]
    ports: ["8080:80"]
```

Biến môi trường tối thiểu trong `.env.example`:

```
DATABASE_URL=postgresql+asyncpg://cwd:...@localhost:5432/cwd
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:9000
S3_BUCKET=cwd-documents
CLAMAV_HOST=localhost
CLAMAV_PORT=3310
TEI_EMBED_URL=http://localhost:8080
# Giá trị mặc định DF-01 – DF-10 (PRD §0.3) — xem T-105
MAX_FILE_SIZE_BYTES=20971520
MAX_DOCUMENTS=50
MAX_PAGES=300
RETENTION_DAYS=90
MAX_QUESTION_LENGTH=2000
ANSWER_TIMEOUT_MS=60000
```

Script khởi tạo PostgreSQL (`infra/pg-init/01-extensions.sql`):

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS citext;   -- cho app_user.email
```

## 4. Thay đổi dữ liệu

Chỉ tạo extension PostgreSQL (`vector`, `unaccent`, `citext`). Bảng và migration thuộc T-005.

## 5. Các bước triển khai

1. Viết `docker-compose.yml` như Mục 3; đặt toàn bộ file hạ tầng trong thư mục `infra/`.
2. Thêm script khởi tạo extension PostgreSQL; kiểm tra bằng `SELECT * FROM pg_extension`.
3. Cấu hình MinIO: tạo bucket `cwd-documents` khi khởi động (dùng dịch vụ phụ `mc` chạy một lần), đặt policy **private**, bật versioning để khớp thiết kế backup SADD §4.2.5.
4. Cấu hình TEI dùng model `BAAI/bge-m3` bản CPU; ghi chú trong README rằng lần chạy đầu sẽ tải model (vài GB) nên cần kiên nhẫn.
5. Thêm healthcheck cho từng dịch vụ để `docker compose up --wait` chỉ trả về khi mọi thứ sẵn sàng.
6. Viết `.env.example` đầy đủ; thêm `.env` vào `.gitignore`.
7. Thêm mục tiêu Makefile: `make up`, `make down`, `make logs`, `make reset-db` (xóa volume và tạo lại).
8. Viết script kiểm tra nhanh `scripts/smoke_infra.py`: kết nối lần lượt PG, Redis, MinIO, ClamAV (gửi chuỗi EICAR), TEI (embed một câu tiếng Việt, kiểm tra độ dài vector = 1024) và in bảng kết quả.
9. Bổ sung hướng dẫn vào README: yêu cầu RAM tối thiểu, cách xử lý khi TEI chậm, cách chạy `smoke_infra`.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| Máy dev không có GPU | TEI chạy bản CPU, chậm hơn nhưng đủ để phát triển; không chặn công việc (nâng GPU chỉ cân nhắc khi hàng đợi ingestion > 5 phút, SADD §2.3) |
| Lần đầu khởi động TEI mất nhiều phút để tải model | Healthcheck chờ, README cảnh báo trước; không coi là lỗi |
| Cổng 5432/6379 đã bị dịch vụ khác chiếm | `.env` cho phép đổi cổng; README ghi rõ cách đổi |
| ClamAV chưa tải xong chữ ký (`freshclam`) | Healthcheck chỉ xanh sau khi chữ ký sẵn sàng; pipeline ingestion không được coi "quét sạch" khi ClamAV chưa sẵn sàng |

## 7. Kiểm thử bắt buộc

- [ ] `docker compose up --wait` trả về thành công trên máy sạch (chưa có volume cũ) — **chưa xác minh**: môi trường triển khai hiện tại không có Docker Engine
- [x] `scripts/smoke_infra.py` — **logic** đã được xác minh bằng 9 test đơn vị giả lập (mock) phản hồi thật của Redis/ClamAV/TEI (`scripts/test_smoke_infra.py`, 9/9 pass); kết nối thật tới hạ tầng chưa chạy được
- [ ] TEI embed câu tiếng Việt có dấu trả về đúng 1024 chiều — chưa xác minh với TEI thật (đã test logic phân tích phản hồi ở trên)
- [ ] ClamAV phát hiện chuỗi thử EICAR là nhiễm — chưa xác minh với ClamAV thật (đã test logic phân tích phản hồi ở trên)
- [ ] `make reset-db` xóa sạch dữ liệu và tạo lại extension thành công — chưa xác minh (cần Docker)

## 8. Định nghĩa Hoàn thành

- [ ] Một developer mới làm theo README chạy được toàn bộ hạ tầng trong ≤ 30 phút — chưa xác minh được trên máy này
- [x] `.env.example` đầy đủ, không có bí mật thật trong repo (chỉ mật khẩu local mặc định, không dùng ở staging/prod)
- [x] Makefile có `up/down/logs/reset-db/smoke-infra`
- [ ] Script smoke test được đưa vào CI ở T-003 (chạy ở chế độ tối thiểu) — để T-003 xử lý

### Ghi chú triển khai thực tế

Môi trường chạy task này (Windows, không cài Docker Desktop) không thể khởi động
`docker compose`. Mọi file cấu hình (`infra/docker-compose.yml`,
`infra/pg-init/01-extensions.sql`, `.env.example`, Makefile targets) đã được viết
đúng theo đặc tả Mục 3 và đã được rà soát thủ công, nhưng **chưa được một lần
`docker compose up` thật nào xác nhận**. Không cài được `pyyaml` để tự động kiểm
tra cú pháp YAML (chưa có wheel cho Python 3.15 tại thời điểm này) — đã rà soát
thủ công thay thế.

Phần duy nhất kiểm thử được mà không cần Docker — **logic phân tích phản hồi**
của `scripts/smoke_infra.py` (cách đọc PONG của Redis, FOUND của ClamAV, mảng
1024 chiều của TEI) — đã viết test giả lập đầy đủ và chạy xanh 9/9.

**Việc cần làm khi có máy có Docker:** chạy `make up`, `make smoke-infra`, xác
nhận đủ 5/5 dịch vụ OK, rồi tick lại các checkbox còn trống ở trên.

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §2.3 (tầng hạ tầng dữ liệu), §4.2.5 (versioning object storage), Phụ lục A
- [PRD v0.2](../../requirements/PRD.md) §0.3 (DF-01 – DF-10)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0, giả định A-02
