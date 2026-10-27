# T-604 — Runbook vận hành pilot (2 tuần hypercare)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | UAT & Pilot Gate |
| Story | Hỗ trợ vận hành toàn bộ 19 story P0/P1 |
| Epic | Tất cả |
| Module (SADD §2.2.1) | `core` (quan sát), `identity` (CLI cấp quyền), `retention`, `ingestion` |
| API liên quan | `GET /healthz`, `GET /readyz` |
| Vai trò chính | OPS (chính) + TL + QA |
| Ước lượng | 2 ngày công |
| Phụ thuộc | T-007 (log/OTel), T-103 (CLI cấp quyền), T-207 (job định kỳ), T-505 (ngưỡng hiệu năng), T-603 (điều kiện kèm theo của ATTT) |
| Trạng thái | To do |

## 1. Mục tiêu

Viết tài liệu vận hành để người trực **không tham gia phát triển** vẫn xử lý được sự cố thường gặp trong 2 tuần đầu pilot, và để đội biết chính xác khi nào cần leo thang.

Mức sẵn sàng: **giờ làm việc 08:00 – 18:00** theo hướng mặc định của **D-07** (OQ-P03/AQ-07 chưa chốt). Ngoài giờ: ghi nhận, xử lý vào đầu giờ hôm sau.

## 2. Tiêu chí nghiệm thu (kiểm chứng được)

| Mã | Nội dung |
|---|---|
| RB-01 | Một người trực chưa từng code dự án, chỉ đọc runbook, tự tra được log/metric của một câu hỏi lỗi cụ thể qua `trace_id` |
| RB-02 | Mọi cảnh báo ở §5.2 đều có mục xử lý tương ứng trong runbook (không có cảnh báo "mồ côi") |
| RB-03 | Quy trình cấp và **thu hồi** quyền truy cập thực hiện được hoàn toàn bằng CLI, có kiểm chứng hiệu lực ngay ở request kế tiếp (AC-023.2) |
| RB-04 | Runbook được diễn tập ít nhất **một lần** trước khi mở pilot |

## 3. Nội dung runbook (cấu trúc bắt buộc)

```
1. Thông tin chung        — phạm vi pilot, giờ trực, danh bạ leo thang
2. Kiểm tra sức khỏe      — /healthz, /readyz, bảng Grafana
3. Tra cứu sự cố          — từ trace_id / user_hash tới log & trace
4. Danh mục cảnh báo      — mỗi cảnh báo: ý nghĩa, cách kiểm tra, cách xử lý
5. Thao tác thường dùng   — cấp/thu hồi quyền, chạy lại job, xử lý tài liệu kẹt
6. Sự cố thường gặp       — triệu chứng → nguyên nhân → xử lý
7. Giới hạn đã biết       — tính năng post-MVP, điều kiện ATTT kèm theo
8. Leo thang              — khi nào dừng pilot
```

## 4. Công cụ quan sát (SADD §4.3)

| Trụ cột | Công cụ | Dùng để |
|---|---|---|
| Log | JSON có cấu trúc → Promtail → **Loki** | Tra theo `trace_id`, `user_hash`, `route`, `error_code`. **Không** có nội dung tài liệu/câu hỏi (P-03) |
| Metric | Prometheus + **Grafana** | `answer_latency_seconds`, `llm_ttft_seconds`, `retrieval_top_score`, `answers_uncited_total`, `ingestion_queue_depth`, `documents_failed_total{error_code}`, `sse_connections`, `circuit_breaker_state` |
| Trace | OpenTelemetry → **Tempo** | Xem chuỗi span `http.request → retrieval.* → llm.stream → qa.validate_citations` |
| Cảnh báo | Alertmanager → kênh nhóm | Xem §5.2 |

## 5. Các bước triển khai

### 5.1 Viết phần tra cứu sự cố
1. Mô tả cách lấy `trace_id`: người dùng báo lỗi → thông báo lỗi trên UI có `trace_id` (SADD §4.3) → dán vào Tempo/Loki.
2. Viết sẵn 3 truy vấn Loki mẫu: theo `trace_id`, theo `error_code`, theo `user_hash` trong khoảng thời gian.
3. Nhấn mạnh: log **không** chứa nội dung — nếu cần tái hiện, phải nhờ người dùng mô tả lại, **tuyệt đối không** bật log nội dung để debug (vi phạm P-03 và G-04).

### 5.2 Viết danh mục cảnh báo (lấy đúng ngưỡng từ SADD §4.3)

| Cảnh báo | Ý nghĩa | Xử lý đầu tiên |
|---|---|---|
| p90 `answer_latency` **> 15 giây** trong 15 phút | Vượt mục tiêu KR1.2 | Kiểm tra `llm_ttft_seconds` và `circuit_breaker_state`; nếu do LLM chậm → thông báo người dùng, theo dõi; nếu do truy xuất → báo TL |
| Tỷ lệ lỗi trả lời **> 2%** trong 30 phút | Lỗi hệ thống hoặc LLM | Xem `documents_failed_total` và log `error_code`; nếu `SERVICE_BUSY` liên tục → kiểm tra hạn mức nhà cung cấp LLM |
| `answers_uncited_total` **tăng** | Câu trả lời có nội dung nhưng không còn trích dẫn hợp lệ — **rủi ro niềm tin (KR2.3)** | Báo ngay TL + BA; nếu tăng nhanh → cân nhắc tạm dừng pilot |
| Hàng đợi ingestion cũ nhất **> 5 phút** | Worker nghẽn hoặc TEI chậm | Kiểm tra số bản sao worker và `ingestion_queue_depth`; tăng worker nếu cần |
| `circuit_breaker_state` **mở** | Adapter LLM/TEI đang lỗi liên tục | Kiểm tra nhà cung cấp; thông báo người dùng pilot về gián đoạn |
| Dung lượng PostgreSQL **> 75%** | Nguy cơ đầy đĩa | Kiểm tra job `retention.purge_expired` có chạy không; mở rộng dung lượng |
| Chi phí token/ngày vượt ngân sách | Rủi ro R-06 | Báo PM; cân nhắc siết rate limit (10 câu/phút/người) |
| Chứng chỉ TLS hết hạn **< 14 ngày** | Nguy cơ gián đoạn | Gia hạn qua cert-manager |

### 5.3 Viết thao tác thường dùng
1. **Cấp quyền:** `python -m app.cli grant-access --email <email> --role user` → người dùng đăng nhập được ngay ở lần thử kế tiếp (AC-023.1).
2. **Thu hồi quyền:** `python -m app.cli revoke-access --email <email>` → **xóa toàn bộ phiên Redis** của người đó, có hiệu lực ở request kế tiếp (AC-023.2). Dùng khi người tham gia rời nhóm pilot.
3. **Tài liệu kẹt ở `processing`:** job `ingestion.reap_stuck` tự chuyển sang `failed` sau 10 phút; nếu cần xử lý sớm, hướng dẫn người dùng xóa và tải lại.
4. **Chạy lại job retention thủ công** (khi nghi ngờ job lỡ lịch) và cách kiểm tra số bản ghi đã xóa qua log.
5. **Kiểm tra sức khỏe nhanh:** `GET /healthz` (liveness) và `GET /readyz` (kiểm tra PostgreSQL, Redis, TEI).

### 5.4 Viết phần sự cố thường gặp

| Triệu chứng người dùng báo | Nguyên nhân thường gặp | Xử lý |
|---|---|---|
| "Không đăng nhập được" | Chưa được cấp quyền, hoặc `active=false` | Kiểm tra `app_user`; cấp quyền bằng CLI |
| "Tài liệu mãi không Sẵn sàng" | Hàng đợi nghẽn hoặc TEI chậm | Xem `ingestion_queue_depth`; chờ `reap_stuck` nếu quá 10 phút |
| "Tệp báo lỗi không rõ lý do" | PDF scan/mật khẩu/hỏng | Đối chiếu `error_code` (`PDF_NO_TEXT`, `PDF_ENCRYPTED`, `PDF_CORRUPTED`) và giải thích cho người dùng |
| "Hệ thống bảo không tìm thấy dù tài liệu có" | Cổng bằng chứng τ hoặc chất lượng truy xuất | Ghi nhận câu hỏi vào danh sách cải thiện chất lượng (không tự ý sửa τ trong lúc pilot) |
| "Câu trả lời không có nguồn" | Rủi ro KR2.3 | Báo TL/BA ngay; đối chiếu `answers_uncited_total` |
| "Mất câu trả lời giữa chừng" | `ANSWER_INTERRUPTED` do SSE đứt | Hướng dẫn nhấn Thử lại; kiểm tra `sse_connections` và cấu hình timeout proxy |

### 5.5 Diễn tập và bàn giao
1. Tổ chức **một buổi diễn tập 60 phút**: giả lập 3 sự cố (tài liệu kẹt, LLM lỗi, người dùng cần thu hồi quyền), người trực thao tác theo runbook.
2. Sửa runbook theo những chỗ người trực bị vướng.
3. Chốt danh bạ leo thang (TL → PM → ATTT) và kênh liên lạc.

## 6. Trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Nghi ngờ **rò rỉ nội dung** vào log/analytics | **Dừng pilot ngay**, thông báo ATTT, chạy lại canary test (T-404); đây là vi phạm G-04 |
| Nghi ngờ **lộ dữ liệu giữa người dùng** | **Dừng pilot ngay**, chạy kiểm thử cô lập (T-504), thông báo ATTT — vi phạm G-03 |
| Sự cố ngoài giờ trực (D-07 = giờ làm việc) | Ghi nhận, xử lý đầu giờ hôm sau; nếu là sự cố bảo mật thì leo thang ngay bất kể giờ |
| ATTT kèm điều kiện (chỉ tài liệu không nhạy cảm) | Ghi điều kiện ở mục "Giới hạn đã biết"; nhắc lại trong thư gửi người dùng pilot |
| Người dùng yêu cầu tính năng post-MVP | Trả lời theo mục "Giới hạn đã biết" (US-016/018/019/022 là post-MVP), chuyển PM ghi backlog |
| Cần khôi phục dữ liệu | Theo quy trình sao lưu/PITR của SADD §4.2; lưu ý **AR-05**: bản sao lưu có thể giữ tài liệu đã xóa tới 7 ngày (phụ thuộc D-04) |

## 7. Kiểm thử bắt buộc

- [ ] **RB-01:** người trực không thuộc đội phát triển tra được log + trace của một lỗi mẫu chỉ bằng `trace_id`
- [ ] **RB-02:** đối chiếu danh sách cảnh báo trong Alertmanager với mục §5.2 — không cảnh báo nào thiếu hướng dẫn xử lý
- [ ] **RB-03:** chạy thử `grant-access` và `revoke-access` trên staging; xác nhận thu hồi có hiệu lực ở request kế tiếp
- [ ] `GET /healthz` và `GET /readyz` trả đúng khi tắt thử Redis/TEI (readyz phải fail, healthz vẫn ok)
- [ ] **RB-04:** buổi diễn tập đã diễn ra, biên bản ghi các điểm đã sửa trong runbook

## 8. Định nghĩa Hoàn thành

- [ ] Runbook đủ 8 mục ở §3, lưu nơi người trực truy cập được (không nằm trong repo riêng của dev)
- [ ] Mọi ngưỡng cảnh báo trong runbook **khớp** cấu hình Alertmanager thực tế
- [ ] Danh bạ leo thang và lịch trực 2 tuần hypercare đã chốt
- [ ] Mục "Giới hạn đã biết" nêu rõ các tính năng post-MVP và điều kiện của ATTT
- [ ] Đã diễn tập ít nhất một lần trước ngày mở pilot
- [ ] Runbook **không** hướng dẫn bất kỳ thao tác nào làm lộ nội dung tài liệu (giữ P-03 và G-04)

## 9. Tham chiếu

- [SADD §4.2 (sao lưu, AR-05), §4.3 (quan sát, cảnh báo), §4.4 (triển khai), §2.2.4 (job định kỳ)](../../requirements/SADD.md)
- [PRD §5.1 G-04/G-07; DF-10](../../requirements/PRD.md)
- [User Stories — US-023 (AC-023.1, AC-023.2), US-021](../../design/User_Stories.md)
- [implement_plan.md §5 UAT, §6 D-07, §7 R-01/R-05/R-06](../implement_plan.md)
