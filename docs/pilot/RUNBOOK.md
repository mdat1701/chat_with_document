# Pilot operations runbook

## 1. Scope and escalation

Giờ trực mặc định 08:00–18:00. Sự cố bảo mật, cô lập dữ liệu hoặc rò rỉ
nội dung phải leo thang ngay tới Tech Lead và ATTT, bất kể giờ.

## 2. Health checks

```powershell
curl.exe https://staging.example/healthz
curl.exe https://staging.example/readyz
```

`healthz` kiểm tra process; `readyz` phải kiểm tra PostgreSQL, Redis và TEI.

## 3. Incident lookup

Tra `trace_id`, `error_code`, `route` hoặc `user_hash` trong Loki/Tempo.
Không bật log câu hỏi, câu trả lời, tên tệp hay nội dung tài liệu.

## 4. Alerts

| Alert | First action |
|---|---|
| Answer p90 > 15s | Kiểm tra TTFT, circuit breaker, retrieval spans |
| Answer errors > 2% | Kiểm tra error code và nhà cung cấp LLM |
| Uncited answers tăng | Dừng pilot nếu tăng nhanh, báo TL/BA |
| Ingestion queue > 5 phút | Kiểm tra worker/TEI và reap-stuck |
| PostgreSQL > 75% | Kiểm tra retention purge và mở rộng dung lượng |

## 5. Common operations

```powershell
python -m app.cli grant-access --email user@example.com --role user
python -m app.cli revoke-access --email user@example.com --yes
python -c "from app.workers.retention_tasks import purge_expired; purge_expired.delay()"
```

Tài liệu stuck quá 10 phút sẽ được chuyển sang failed; hướng dẫn người dùng
tải lại sau khi xác nhận mã lỗi.

## 6. Stop conditions

Dừng pilot ngay khi phát hiện dữ liệu chéo owner, nội dung trong log/analytics,
answer có nội dung nhưng không có citation, hoặc xóa không ngăn được truy xuất.

## 7. Hypercare handover

Trước khi mở pilot phải diễn tập ba sự cố: tài liệu stuck, LLM lỗi và revoke
access. Ghi lại người tham gia, thời gian xử lý và điểm cần sửa.
