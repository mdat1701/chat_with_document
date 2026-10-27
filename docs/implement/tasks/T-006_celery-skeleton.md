# T-006 — Khung Celery (worker + beat)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng; nền cho US-003, US-005, US-021) |
| Module (SADD §2.2.1) | `workers/`, `adapters/celery_queue`, `ports/QueuePort` |
| API liên quan | — |
| Vai trò chính | BE |
| Ước lượng | 1d |
| Phụ thuộc | T-001, T-002 |
| Trạng thái | To do |

## 1. Mục tiêu

Dựng tiến trình `worker` và `beat` chạy từ cùng codebase với `api`, với **hai hàng đợi tách biệt** `ingestion` và `maintenance` (mẫu bulkhead, SADD §4.2.3). Khi xong, có thể đẩy một task mẫu vào hàng đợi và thấy worker xử lý; đây là nền cho pipeline ingestion (T-201 – T-203) và các job định kỳ (T-207).

## 2. Tiêu chí chấp nhận

- `celery -A app.workers.celery_app worker -Q ingestion,maintenance` khởi động và kết nối Redis thành công.
- `celery -A app.workers.celery_app beat` khởi động, đọc lịch từ cấu hình (lịch thật khai báo ở T-207).
- Task mẫu `ping` đẩy vào `ingestion` được worker nhận và trả kết quả.
- Worker bật `acks_late=True` (job được trả lại hàng đợi nếu pod chết giữa chừng — SADD §4.2.2).
- Task Celery **chỉ** gọi use case trong `modules/`, không chứa logic nghiệp vụ (quy tắc "`workers/` là adapter vào" — SADD §2.2.1).
- Worker dùng vai trò CSDL `cwd_worker` (có `BYPASSRLS`), khác với `api` dùng `cwd_app`.

## 3. Hợp đồng / cấu hình cụ thể

```python
# app/workers/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery("cwd", broker=settings.REDIS_URL, backend=None)

celery_app.conf.update(
    task_acks_late=True,              # SADD §4.2.2 — job tra lai neu pod chet
    worker_prefetch_multiplier=1,     # task nang, khong gom truoc
    task_reject_on_worker_lost=True,
    task_default_queue="maintenance",
    task_routes={
        "ingestion.*": {"queue": "ingestion"},
        "retention.*": {"queue": "maintenance"},
        "blob.*":      {"queue": "maintenance"},
    },
    task_time_limit=15 * 60,          # chặn job treo vĩnh viễn
    task_soft_time_limit=10 * 60,     # khớp ngưỡng reap_stuck (T-207)
    timezone="Asia/Ho_Chi_Minh",
)
```

Khung task (logic thật ở Sprint 2):

```python
# app/workers/ingestion_tasks.py
@celery_app.task(name="ingestion.process", bind=True, max_retries=3)
def process_document(self, document_id: str) -> None:
    # CHỈ gọi use case; không viết logic PDF ở đây
    from app.modules.ingestion.service import process_document_use_case
    process_document_use_case(document_id)
```

Lệnh khởi động hai tiến trình (cùng image, khác CMD — SADD §4.4):

```
api    : uvicorn app.api.main:app --host 0.0.0.0 --port 8000
worker : celery -A app.workers.celery_app worker -Q ingestion,maintenance --concurrency=2
beat   : celery -A app.workers.celery_app beat
```

## 4. Thay đổi dữ liệu

Không có. Worker dùng schema của T-005; chỉ cần cấu hình kết nối bằng vai trò `cwd_worker`.

## 5. Các bước triển khai

1. Tạo `app/workers/celery_app.py` với cấu hình như Mục 3; broker là Redis (DB riêng cho broker, tách khỏi DB dùng cho phiên/rate limit để `maxmemory-policy` khác nhau — SADD §2.3).
2. Định nghĩa `QueuePort` trong `ports/` (`enqueue(task_name, payload)`) và `adapters/celery_queue.py` hiện thực hóa — để `modules/documents` đẩy job mà không import Celery trực tiếp (nguyên tắc P-01).
3. Tạo task mẫu `ingestion.ping` và `maintenance.ping` để kiểm chứng định tuyến hàng đợi.
4. Tạo khung `app/workers/ingestion_tasks.py`, `retention_tasks.py`, `blob_tasks.py` — chỉ khai báo task rỗng gọi use case tương ứng, logic viết ở T-201/T-207.
5. Cấu hình session CSDL riêng cho worker dùng vai trò `cwd_worker`.
6. Thêm `worker` và `beat` vào `docker-compose.yml` của T-002 để chạy đủ bộ tại local.
7. Thêm log có cấu trúc cho vòng đời task (nhận / xong / lỗi) qua logger của T-007 — **không** log nội dung tài liệu, chỉ `document_id`.
8. Cấu hình `terminationGracePeriodSeconds` cho worker trên staging để hoàn tất task hiện tại khi rolling update (SADD §4.2.3).

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| Worker chết giữa lúc xử lý một tài liệu | `acks_late` trả job về hàng đợi; worker khác nhận lại. Vì pipeline idempotent (T-201), chạy lại không tạo dữ liệu trùng |
| Hàng đợi `ingestion` bị dồn 500 tệp (kịch bản onboarding) | Không chặn job `maintenance` nhờ tách hàng đợi; HPA tăng worker lên tối đa 6 bản sao (SADD §4.2.2) |
| Task chạy quá lâu (PDF lỗi lạ) | `soft_time_limit` 10 phút bắn ngoại lệ để task tự dọn; `reap_stuck` (T-207) đặt `INGESTION_FAILED` cho bản ghi tương ứng |
| Dev viết logic nghiệp vụ thẳng trong file task | `import-linter` không bắt được việc này — chặn ở code review; task chỉ được phép gọi `service.py` |
| Redis mất kết nối | Worker retry kết nối; API vẫn nhận upload nhưng job chờ — không mất dữ liệu vì trạng thái nằm ở bảng `document` |

## 7. Kiểm thử bắt buộc

- [ ] Worker khởi động và log rõ đang lắng nghe đúng 2 hàng đợi
- [ ] `ingestion.ping` đẩy vào đúng hàng đợi `ingestion` (kiểm tra bằng `redis-cli LLEN`)
- [ ] Giết worker giữa lúc chạy task dài → task quay lại hàng đợi và được xử lý lại
- [ ] Beat khởi động không lỗi khi danh sách lịch còn rỗng
- [ ] Worker kết nối CSDL bằng vai trò `cwd_worker` (kiểm tra `SELECT current_user`)

## 8. Định nghĩa Hoàn thành

- [ ] `make up` khởi động đủ `api`, `worker`, `beat` tại local
- [ ] `QueuePort` + adapter Celery đã có, `modules/` không import Celery trực tiếp
- [ ] Khung task cho ingestion/retention/blob đã sẵn sàng cho Sprint 2
- [ ] Log vòng đời task không chứa nội dung tài liệu

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §2.2.1 (vai trò `workers/`), §2.2.4 (tác vụ nền), §2.3 (Redis), §4.2.2, §4.2.3 (acks_late, bulkhead, tắt êm)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0 · Task tiếp theo dùng khung này: [T-201](T-201_ingestion-scan-and-validate.md), [T-207](T-207_scheduled-jobs-retention.md)
