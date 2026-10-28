# T-004 — Khung môi trường staging

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 0 |
| Story | — (hạ tầng) |
| Module (SADD §2.2.1) | Toàn hệ thống (triển khai SADD §4.4) |
| API liên quan | — |
| Vai trò chính | OPS (hỗ trợ: TL, ATTT) |
| Ước lượng | 2d |
| Phụ thuộc | T-002, T-003, **D-02** (nền tảng triển khai) |
| Trạng thái | Done (manifest) — chưa có cluster thật để áp dụng, xem ghi chú cuối |

## 1. Mục tiêu

Dựng môi trường `staging` chạy được bản build từ nhánh chính, để từ Sprint 2 trở đi đội có nơi chạy E2E, đo hiệu năng và nghiệm thu với PM/BA trên dữ liệu giả lập. Staging cũng là nơi duy nhất có thể **rút ngắn `RETENTION_DAYS`** để kiểm thử job dọn dẹp (T-207) phục vụ Pilot Gate G-05 mà không phải chờ 90 ngày thật.

## 2. Tiêu chí chấp nhận

- Bản build từ nhánh chính được triển khai tự động lên staging sau khi CI xanh (SADD §4.4).
- Staging có đủ `api`, `worker`, PostgreSQL, Redis, object storage, TEI; truy cập qua HTTPS với chứng chỉ hợp lệ do cert-manager cấp.
- Ingress đã cấu hình **đúng cho SSE** (xem Mục 3) — nếu sai, luồng câu trả lời và luồng trạng thái tài liệu sẽ bị treo, phát hiện rất muộn ở Sprint 3.
- Mọi bí mật lấy từ secret manager, **không** có bí mật trong image hay Git.
- Staging dùng dữ liệu giả lập, không có tài liệu nghiệp vụ thật (BRD CON-004).

## 3. Hợp đồng / cấu hình cụ thể

Cấu hình Ingress bắt buộc cho hai đường dẫn SSE (SADD §4.2.4) — **điểm dễ sai nhất của task này**:

```nginx
# /api/v1/conversations/*/questions  và  /api/v1/documents/events
proxy_buffering       off;
proxy_read_timeout    75s;    # câu hỏi (DF-10 = 60s + biên an toàn)
# proxy_read_timeout  3600s;  # riêng /documents/events (kết nối dài)
add_header X-Accel-Buffering no;
```

Tham số triển khai theo SADD §4.2.2 và §4.4:

```yaml
api:
  replicas: 2
  terminationGracePeriodSeconds: 75   # chờ SSE đang mở đóng êm
  strategy: RollingUpdate (maxUnavailable: 0)
worker:
  replicas: 2
  queues: ingestion, maintenance      # tách biệt (bulkhead)
env (staging):
  RETENTION_DAYS: <rút ngắn, ví dụ 1>  # phục vụ kiểm thử G-05 (T-207)
  # các DF khác giữ như production
```

## 4. Thay đổi dữ liệu

Không có schema mới. Staging dùng cùng migration Alembic với local/prod (T-005), chạy tự động khi triển khai theo kiểu **expand → migrate → contract**.

## 5. Các bước triển khai

1. **Chốt D-02 trước khi code**: Kubernetes nội bộ sẵn có, cloud được duyệt, hay VM. Nếu chưa chốt, triển khai theo hướng mặc định của kế hoạch (Kubernetes nội bộ) nhưng giữ mọi cấu hình trong manifest/Helm để chuyển nền tảng không phải viết lại ứng dụng.
2. Tạo namespace `cwd-staging`; khai báo Deployment cho `api` và `worker` **dùng chung một image**, khác `command`.
3. Cài Ingress NGINX + cert-manager, cấp chứng chỉ TLS 1.2+ (ưu tiên 1.3), bật HSTS `max-age=31536000` (SADD §4.1.2).
4. Cấu hình riêng cho hai đường dẫn SSE như Mục 3; **kiểm chứng ngay** bằng `curl -N` để chắc chắn dữ liệu chảy từng phần chứ không bị buffer.
5. Cài External Secrets (hoặc cơ chế tương đương của nền tảng) đọc bí mật từ Vault/secret manager; không đặt bí mật vào ConfigMap.
6. Đưa DF-01 – DF-10 vào ConfigMap (P-06 — cấu hình thay vì hằng số); staging đặt `RETENTION_DAYS` rút ngắn.
7. Cấu hình job chạy migration Alembic trước khi pod mới nhận traffic.
8. Nối CI: sau khi nhánh chính xanh thì tự động triển khai staging (production sẽ cần phê duyệt thủ công — cấu hình sau, ngoài phạm vi Sprint 0).
9. Thêm liveness/readiness probe trỏ tới `/healthz` và `/readyz` (T-008).
10. Viết trang runbook ngắn: cách xem log, cách rollback về tag trước, cách chạy lại migration.

## 6. Rủi ro & trường hợp biên

| Tình huống | Hành vi mong đợi |
|---|---|
| D-02 chưa chốt khi bắt đầu Sprint 0 | Dựng theo hướng mặc định, giữ toàn bộ khác biệt nền tảng trong manifest; ứng dụng không chứa mã phụ thuộc nền tảng |
| Ingress buffer SSE | `curl -N` nhận dữ liệu nhỏ giọt, không nhận một cục khi kết thúc; nếu sai, sửa ngay ở Sprint 0 thay vì chờ Sprint 3 |
| Chứng chỉ TLS hết hạn trong pilot | cert-manager tự gia hạn; cảnh báo khi còn < 14 ngày (SADD §4.3) |
| Rolling update cắt kết nối SSE đang mở | `maxUnavailable=0` + `terminationGracePeriodSeconds=75`; người dùng mất tối đa một câu hỏi đang chạy |
| Có người đưa tài liệu thật lên staging | Vi phạm CON-004 — ghi rõ trong runbook và dán cảnh báo trên màn hình đăng nhập staging |

## 7. Kiểm thử bắt buộc

- [ ] Truy cập URL staging qua HTTPS, chứng chỉ hợp lệ, HSTS có trong response header — **không thể kiểm** (không có cluster/DNS/cert-manager thật)
- [ ] `curl -N .../documents/events` nhận `: ping` định kỳ, không bị buffer — **không thể kiểm**; đã viết đúng 3 Ingress tách riêng theo annotation ingress-nginx chuẩn (`proxy-buffering: off`, `X-Accel-Buffering: no`, timeout riêng 75s/3600s) và ghi rõ cách kiểm chứng + dấu hiệu sai trong `RUNBOOK.md`
- [ ] Triển khai lại khi đang có kết nối SSE mở → đóng êm, không lỗi 502 — **không thể kiểm**; `maxUnavailable: 0` + `terminationGracePeriodSeconds: 75` (api) / `630` (worker) đã khai báo đúng
- [ ] Migration Alembic chạy tự động khi triển khai, pod chỉ nhận traffic sau khi `/readyz` xanh — **không thể kiểm**; `job-migrate.yaml` + `readinessProbe: /readyz` đã khai báo, quy trình áp dụng trước rollout ghi trong `RUNBOOK.md`
- [x] Không tìm thấy bí mật nào trong manifest Git — xác nhận: mọi giá trị nhạy cảm đi qua `ExternalSecret`/Vault (`external-secret.yaml`), `ConfigMap` chỉ chứa giá trị DF-* không nhạy cảm; `grep -riE "password|secret" infra/k8s/staging/*.yaml` chỉ khớp **tên khóa** (`client_secret`, `hash_secret`...), không có giá trị thật

## 8. Định nghĩa Hoàn thành

- [ ] Staging truy cập được, chạy bản build mới nhất — **chưa triển khai thật**, chờ D-02
- [ ] Cấu hình SSE đã kiểm chứng bằng `curl -N` — chưa thể, không có cluster
- [x] `RETENTION_DAYS` rút ngắn trên staging (`1` thay vì `90`), ghi rõ trong `configmap.yaml` và `RUNBOOK.md`
- [x] Runbook rollback đã viết (`RUNBOOK.md`) — **chưa thử rollback thật** (không có cluster)

### Ghi chú triển khai thực tế

**Không có cluster Kubernetes, DNS, hay quyền truy cập cloud nào trong môi
trường triển khai task này** — đây là hạn chế nặng nhất trong tất cả các task
đã làm, vì T-004 về bản chất là triển khai hạ tầng thật, không phải chạy mã.
Đã làm tối đa có thể mà không cần cluster:

1. Viết đầy đủ 10 manifest Kubernetes (`infra/k8s/staging/`): namespace,
   ServiceAccount, ConfigMap, ExternalSecret+SecretStore (Vault), Deployment
   api/worker/beat/frontend + Service, **3 Ingress tách riêng** cho SSE (điểm
   dễ sai nhất của task, xem Mục 3), Job migration, `kustomization.yaml` gom
   lại, và `RUNBOOK.md`.
2. **Xác minh cú pháp YAML thật** cho cả 10 file (`ruamel.yaml.load_all`,
   không chỉ đọc bằng mắt) — phát hiện và tiện thể xác nhận luôn
   `infra/docker-compose.yml` của T-002 (chưa từng kiểm được vì lúc đó không
   cài được `pyyaml`) cũng hợp lệ cú pháp.
3. Rà soát thủ công kỹ theo đúng 2 rủi ro lớn nhất mà task nêu: (a) Ingress
   buffer SSE — giải quyết bằng cách **tách 3 Ingress riêng** vì annotation
   `ingress-nginx` áp dụng cho toàn bộ path trong cùng một Ingress, không thể
   đặt `proxy-read-timeout` khác nhau cho `/documents/events` (3600s) và
   `/conversations/*/questions` (75s) nếu gộp chung — đây là điều SADD không
   nêu rõ nhưng bắt buộc về mặt kỹ thuật; (b) rolling update cắt SSE — xử lý
   bằng `maxUnavailable: 0` + `terminationGracePeriodSeconds` khớp timeout
   nghiệp vụ của từng loại pod.
4. **Không wire job deploy tự động vào CI** (`.github/workflows/ci.yml`) như
   Mục 5 bước 8 gợi ý — vì chưa có `KUBE_CONFIG`/thông tin cluster thật, thêm
   job sẽ chỉ lỗi ồn ào mỗi lần chạy CI mà không có giá trị. Quy trình triển
   khai thủ công đã ghi đầy đủ trong `RUNBOOK.md`, sẵn sàng chuyển thành job
   CI khi D-02 chốt và có `KUBE_CONFIG` thật.

**Giá trị còn để trống/giả định, cần DevOps điền khi D-02 chốt:** domain thật
(`staging.example.com`), địa chỉ Vault server, `cert-manager` ClusterIssuer,
registry image (`ghcr.io/ORG/...`).

## 9. Tham chiếu

- [SADD v0.3](../../requirements/SADD.md) §4.4 (triển khai), §4.2.2 (HA), §4.2.4 (SSE qua proxy), §4.1.2 (mã hóa, bí mật)
- [PRD v0.2](../../requirements/PRD.md) §5.1 G-05 (xóa và retention)
- [implement_plan.md](../implement_plan.md) §5 Sprint 0, quyết định D-02, giả định A-02
