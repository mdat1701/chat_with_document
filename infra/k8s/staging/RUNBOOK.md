# Runbook staging (T-004 §5 bước 10)

> Chưa triển khai thật — tài liệu này mô tả quy trình **khi có cluster thật**
> (chờ D-02). Xem "Ghi chú triển khai thực tế" trong
> [`T-004_staging-skeleton.md`](../../../docs/implement/tasks/T-004_staging-skeleton.md).

## Xem log

```bash
kubectl -n cwd-staging logs -f deploy/cwd-api
kubectl -n cwd-staging logs -f deploy/cwd-worker
kubectl -n cwd-staging logs -f deploy/cwd-beat
```

## Rollback về tag trước

```bash
kubectl -n cwd-staging set image deploy/cwd-api api=ghcr.io/ORG/cwd-backend:<tag-truoc>
kubectl -n cwd-staging set image deploy/cwd-worker worker=ghcr.io/ORG/cwd-backend:<tag-truoc>
kubectl -n cwd-staging set image deploy/cwd-beat beat=ghcr.io/ORG/cwd-backend:<tag-truoc>
kubectl -n cwd-staging rollout status deploy/cwd-api
```

Nếu migration của bản mới không tương thích ngược (vi phạm quy ước
expand→migrate→contract, SADD §4.4): **không** tự ý `alembic downgrade` trên
staging có dữ liệu thật — xác nhận với Tech Lead trước.

## Chạy lại migration thủ công

```bash
kubectl -n cwd-staging apply -f infra/k8s/staging/job-migrate.yaml
kubectl -n cwd-staging wait --for=condition=complete job -l job-name --timeout=120s
```

## Triển khai (CI gọi các bước này sau khi nhánh chính xanh — T-003/T-004 §5 bước 8)

```bash
kubectl apply -k infra/k8s/staging           # namespace, config, secret, deployment, ingress
kubectl -n cwd-staging apply -f infra/k8s/staging/job-migrate.yaml
kubectl -n cwd-staging wait --for=condition=complete job -l job-name --timeout=120s
kubectl -n cwd-staging rollout status deploy/cwd-api deploy/cwd-worker deploy/cwd-web
```

## Kiểm chứng SSE sau khi áp Ingress (BẮT BUỘC — T-004 §7)

```bash
curl -N https://staging.example.com/api/v1/documents/events
# Đúng: thấy `: ping` chảy nhỏ giọt mỗi ~15s, không phải chờ rồi nhận 1 cục
```

Nếu `curl -N` không thấy gì chảy cho tới khi kết thúc kết nối: Ingress đang
buffer SSE — kiểm tra lại `proxy-buffering: "off"` và `X-Accel-Buffering: no`
trong `ingress.yaml`. Đây là lỗi cấu hình phổ biến nhất của task này.

## Cảnh báo quan trọng

**Không đưa tài liệu nghiệp vụ thật lên staging** (BRD CON-004). Staging chỉ
dùng dữ liệu giả lập.
