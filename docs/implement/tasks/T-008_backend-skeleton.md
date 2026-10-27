# T-008 — Khung ứng dụng back-end (FastAPI)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng; nền cho toàn bộ API-01 – API-09) |
| Module (SADD §2.2.1) | `api/`, `core/` |
| API liên quan | `GET /healthz`, `GET /readyz` (nội bộ) |
| Vai trò chính | BE |
| Ước lượng | 1d |
| Phụ thuộc | T-001, T-005 |
| Trạng thái | To do |

## 1. Mục tiêu

Dựng ứng dụng FastAPI chạy được với tiền tố đường dẫn `/api/v1`, cấu hình đọc từ biến môi trường, hai endpoint kiểm tra sức khỏe cho Kubernetes, và một **dependency xác thực dạng stub** để các task Sprint 1 cắm đăng nhập thật vào mà không phải sửa lại cấu trúc router. Khi xong, `curl /healthz` trả 200 và staging (T-004) có thể dựa vào `/readyz` để quyết định pod đã sẵn sàng nhận traffic.

## 2. Tiêu chí chấp nhận

- Ứng dụng khởi động bằng `uvicorn app.api.main:app` và phục vụ mọi route nghiệp vụ dưới tiền tố `/api/v1`.
- `GET /healthz` trả 200 ngay khi tiến trình sống (liveness), **không** kiểm tra phụ thuộc ngoài.
- `GET /readyz` trả 200 chỉ khi kết nối được PostgreSQL, Redis và TEI; trả 503 kèm danh sách thành phần lỗi nếu không.
- Cấu hình DF-01 – DF-10 đọc từ biến môi trường qua Pydantic Settings, **không** hằng số rải rác trong code (nguyên tắc P-06).
- Exception handler toàn cục trả đúng định dạng `{code, params}` của SADD §2.4.2.
- Dependency `get_current_user` tồn tại ở dạng stub và được T-102 thay bằng bản thật mà không đổi chữ ký hàm.

## 3. Hợp đồng / cấu hình cụ thể

```python
# app/api/main.py
app = FastAPI(title="Chat với tài liệu", docs_url=None, redoc_url=None)  # tắt docs công khai ở prod
app.include_router(api_router, prefix="/api/v1")

# Health endpoints — KHÔNG đặt dưới /api/v1 để probe hạ tầng gọi trực tiếp
@app.get("/healthz")   # liveness: chỉ xác nhận tiến trình sống
@app.get("/readyz")    # readiness: kiểm tra PG, Redis, TEI
```

Phản hồi `/readyz` khi có thành phần lỗi:

```json
HTTP 503
{ "status": "not_ready", "checks": { "postgres": "ok", "redis": "ok", "tei": "unreachable" } }
```

Cấu hình (SADD P-06 — giá trị phát ra client qua API-02 ở T-105):

```python
# app/core/config.py  (pydantic-settings)
class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    S3_ENDPOINT: str
    S3_BUCKET: str
    TEI_EMBED_URL: str
    CLAMAV_HOST: str
    CLAMAV_PORT: int = 3310
    # DF-01 – DF-10 (PRD §0.3)
    MAX_FILE_SIZE_BYTES: int = 20_971_520   # DF-01
    MAX_DOCUMENTS: int = 50                 # DF-02
    MAX_PAGES: int = 300                    # DF-03
    RETENTION_DAYS: int = 90                # DF-05
    MAX_QUESTION_LENGTH: int = 2000         # DF-07
    ANSWER_TIMEOUT_MS: int = 60_000         # DF-10
```

Dependency xác thực stub (thay bằng bản thật ở T-102):

```python
# app/api/deps.py
async def get_current_user() -> CurrentUser:
    """STUB Sprint 0: trả user cố định từ biến môi trường DEV_USER_ID.
    T-102 thay bằng: đọc cookie cwd_sid -> tra phiên Redis -> trả CurrentUser.
    Chữ ký hàm KHÔNG được đổi để router Sprint 1 không phải sửa.
    """
```

Timeout cho mọi lời gọi ra ngoài (SADD §4.2.3) — khai báo tập trung trong `core.config`:

```
PostgreSQL truy vấn 5s · TEI embed câu hỏi 3s / batch 30s
LLM viết lại 4s / trả lời 50s · object storage 30s
```

## 4. Thay đổi dữ liệu

Không có. Task dùng schema của T-005 (chỉ mở kết nối, không tạo bảng).

## 5. Các bước triển khai

1. Tạo `app/api/main.py`: khởi tạo FastAPI, gắn `api_router` với tiền tố `/api/v1`, tắt `/docs` và `/redoc` ở môi trường production (bật ở dev qua biến môi trường).
2. Viết `app/core/config.py` dùng `pydantic-settings`, nạp từ `.env`/biến môi trường; thất bại khởi động ngay nếu thiếu biến bắt buộc (fail fast, tránh chạy với cấu hình sai).
3. Tạo engine SQLAlchemy async với pool phù hợp PgBouncer (transaction pooling → tắt prepared statement cache), timeout truy vấn 5s.
4. Tạo client Redis dùng chung (phiên, rate limit, pub/sub) và client HTTP cho TEI với timeout ở Mục 3.
5. Viết `/healthz`: trả `{"status":"ok"}` không chạm phụ thuộc nào.
6. Viết `/readyz`: chạy song song 3 kiểm tra (PG `SELECT 1`, Redis `PING`, TEI gọi endpoint `/health`), tổng timeout ≤ 2s; trả 503 kèm chi tiết như Mục 3.
7. Gắn exception handler toàn cục dùng `DomainError` của T-007; handler cho `RequestValidationError` trả `400 {"code":"QUESTION_INVALID"}` hoặc mã phù hợp thay vì thông báo mặc định của FastAPI.
8. Gắn middleware log request (dùng logger T-007) ghi `route, status, latency_ms, user_hash`.
9. Tạo `app/api/deps.py` với `get_current_user` stub và kiểu `CurrentUser(id, email, roles)`.
10. Thêm `terminationGracePeriodSeconds`/graceful shutdown: khi nhận SIGTERM, ngừng nhận kết nối mới, chờ SSE đang mở tối đa 60s (hoàn thiện khi có SSE thật ở T-204/T-304).
11. Viết test khói: `/healthz` trả 200; `/readyz` trả 503 khi tắt Redis.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| TEI chưa tải xong model khi pod khởi động | `/readyz` trả 503 → Kubernetes chưa gửi traffic; `/healthz` vẫn 200 nên pod **không** bị restart oan |
| Thiếu biến môi trường bắt buộc | Ứng dụng dừng ngay khi khởi động với thông báo rõ tên biến, không chạy ở trạng thái nửa vời |
| Stub auth bị lọt lên staging/production | Bắt buộc stub chỉ hoạt động khi `ENV=local`; ở môi trường khác thì ném lỗi khởi động. Ghi TODO rõ ràng và gắn với T-102 |
| PgBouncer transaction pooling + prepared statement | Tắt statement cache của asyncpg, nếu không sẽ gặp lỗi khó hiểu khi lên staging |
| Request body quá lớn gửi vào endpoint bất kỳ | Giới hạn kích thước ở tầng Ingress (T-004); API vẫn kiểm tra lại ở T-108 |

## 7. Kiểm thử bắt buộc

- [ ] `curl /healthz` trả 200 khi PostgreSQL đang tắt (liveness độc lập với phụ thuộc)
- [ ] `curl /readyz` trả 503 và chỉ đúng thành phần lỗi khi tắt Redis
- [ ] Route nghiệp vụ mẫu nằm đúng dưới `/api/v1`
- [ ] Ném `DomainError("NOT_AUTHORIZED")` từ một route thử → nhận `403 {"code":"NOT_AUTHORIZED"}`
- [ ] Khởi động thiếu `DATABASE_URL` → tiến trình thoát kèm thông báo rõ ràng
- [ ] Stub auth bị từ chối khởi động khi `ENV=staging`

## 8. Định nghĩa Hoàn thành

- [ ] Ứng dụng chạy tại local và trên staging (T-004), probe hoạt động
- [ ] Cấu hình DF nằm tập trung trong `core.config`, không hằng số rải rác
- [ ] Exception handler trả đúng định dạng `{code, params}`
- [ ] `get_current_user` stub có TODO trỏ tới T-102 và chỉ chạy ở môi trường local

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §2.4.2 (danh mục endpoint, quy ước lỗi), §4.2.3 (timeout, tắt êm), §4.4 (triển khai), nguyên tắc P-06
- [PRD v0.2](../../requirements/PRD.md) §0.3 (DF-01 – DF-10)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0 · Task kế tiếp: [T-102](T-102_session-csrf-me.md), [T-105](T-105_config-api-and-rate-limit.md)
