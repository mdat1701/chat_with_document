# T-505 — Kiểm thử hiệu năng tối thiểu ở quy mô pilot

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | Hỗ trợ US-003 (AC-003.3), US-011 (độ trễ trả lời) |
| Epic | EP-02, EP-03 |
| Module (SADD §2.2.1) | Toàn hệ thống: `api`, `worker`, PostgreSQL, Redis, TEI, LLM |
| API liên quan | API-04 (tải lên), API-06 (SSE trạng thái), API-09 (hỏi đáp SSE) |
| Vai trò chính | QA (chủ trì) · OPS (hạ tầng, autoscale) · TL (phân tích ngân sách độ trễ) |
| Ước lượng | 2d |
| Phụ thuộc | T-203, T-304, T-004 (staging) · D-02 (nền tảng triển khai) |
| Trạng thái | To do |

## 1. Mục tiêu

Chứng minh hệ thống đáp ứng **Pilot Gate G-06 — "Hiệu năng tối thiểu"**: tài liệu mẫu và câu hỏi mẫu hoàn thành trong giới hạn DF-03/DF-10 ở quy mô pilot. Đây là **smoke/performance test quy mô nhỏ**, không phải load test production (đã chuyển sang Production Gate sau pilot theo PRD §5.1).

Quy mô thiết kế lấy từ SADD Phụ lục A.2: ~12 người dùng thực tế, 10 người đồng thời, ~240 câu hỏi/ngày, đỉnh 2 câu/giây (burst 5).

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-06 | Có báo cáo smoke/performance test ở quy mô pilot, Tech Lead ký |
| KR1.2 | **p90 thời gian từ lúc gửi câu hỏi đến khi hiển thị đầy đủ câu trả lời ≤ 15 giây** (ngân sách SADD ước tính ~12,8 giây) |
| AC-003.3 | PDF văn bản 20 trang chuyển sang "Sẵn sàng" trong **≤ 60 giây** |
| DF-10 | Không câu hỏi nào vượt 60 giây; quá hạn phải trả `ANSWER_TIMEOUT` đúng cách |
| CN-03 (SDD) | Chỉ báo "Đang tìm…" xuất hiện ≤ 300 ms; TTFT ≤ 3 giây `[Đề xuất]` |
| SADD §2.2.3 | Kịch bản đột biến 500 tệp: worker tự tăng từ 2 lên tối đa 6 bản sao, hàng đợi không treo > 5 phút |

## 3. Hợp đồng / kịch bản cụ thể

**Kịch bản 1 — tải hỏi đáp (`k6/qa_load.js`):**

```js
export const options = {
  scenarios: {
    steady: { executor: 'constant-arrival-rate', rate: 2, timeUnit: '1s',
              duration: '10m', preAllocatedVUs: 10, maxVUs: 15 },      // 2 câu/giây
    burst:  { executor: 'constant-arrival-rate', rate: 5, timeUnit: '1s',
              duration: '1m', startTime: '10m', preAllocatedVUs: 15, maxVUs: 20 },
  },
  thresholds: {
    'answer_complete_ms': ['p(90)<15000'],   // KR1.2
    'ttft_ms':            ['p(90)<3000'],    // [Đề xuất]
    'http_req_failed':    ['rate<0.02'],     // tỷ lệ lỗi < 2%
  },
};
// Mỗi iteration: POST /conversations/{cid}/questions, đọc SSE,
// đo ttft_ms (tới delta đầu tiên) và answer_complete_ms (tới sự kiện done).
```

**Kịch bản 2 — ingestion bình thường:** tải 1 PDF 20 trang, đo từ `201` tới `status=ready` qua SSE → kỳ vọng ≤ 60 giây (AC-003.3).

**Kịch bản 3 — đột biến onboarding (`k6/ingestion_burst.js`):** 10 người × 50 tệp = **500 tệp** tải lên trong thời gian ngắn.

```
Theo dõi trong lúc chạy (Prometheus):
  ingestion_queue_depth              # không tăng vô hạn
  ingestion_duration_seconds{outcome}
  answer_latency_seconds             # đường hỏi đáp KHÔNG bị ảnh hưởng (P-05: tách worker)
  llm_ttft_seconds
  sse_connections
  circuit_breaker_state
  kube_deployment_status_replicas{deployment="cwd-worker"}   # 2 → tối đa 6
```

## 4. Thay đổi dữ liệu

- Không đổi lược đồ. Dùng tài khoản kiểm thử riêng và corpus kiểm thử được phép (BRD DEP-003).
- **Dọn sạch dữ liệu sau khi chạy** (xóa tài liệu test) để không làm nhiễu số liệu và không chiếm dung lượng staging.
- Ghi lại cấu hình hạ tầng tại thời điểm đo (số bản sao api/worker, tài nguyên TEI) vào báo cáo — số đo vô nghĩa nếu thiếu thông tin này.

## 5. Các bước triển khai

1. Chuẩn bị môi trường `staging` có cấu hình **gần giống prod** (cùng số bản sao tối thiểu, cùng loại máy); ghi lại cấu hình.
2. Viết script k6 cho 3 kịch bản ở §3; với SSE, dùng custom metric `Trend` vì k6 không đo sẵn thời gian hoàn tất luồng.
3. Chạy kịch bản 2 trước (đơn giản nhất) để xác nhận AC-003.3 với ít nhất 5 tệp mẫu khác nhau; lấy trung vị và p90.
4. Chạy kịch bản 1 (10 phút steady + 1 phút burst), thu thập `ttft_ms`, `answer_complete_ms`, tỷ lệ lỗi.
5. Đối chiếu với **ngân sách độ trễ** trong SADD §3.2.2 để tìm điểm nghẽn thật (truy xuất vector / rerank / LLM): nếu p90 vượt 15 giây, xác định thành phần nào chiếm nhiều nhất bằng span OTel (`retrieval.vector`, `retrieval.rerank`, `llm.stream`).
6. Chạy kịch bản 3 (500 tệp), theo dõi `ingestion_queue_depth` và số bản sao worker; xác nhận worker tự tăng tới tối đa 6 và tuổi hàng đợi không vượt 5 phút.
7. Trong lúc chạy kịch bản 3, gửi song song vài câu hỏi để chứng minh **đường hỏi đáp không bị nghẽn bởi ingestion** (nguyên tắc P-05, ADR-01).
8. Kiểm tra hành vi quá hạn: giả lập LLM chậm → máy chủ hủy sau 50 giây, client nhận `ANSWER_TIMEOUT` ở 60 giây (DF-10), UI hiện nút Thử lại.
9. Viết báo cáo: cấu hình, biểu đồ, bảng số liệu so với ngưỡng, kết luận đạt/không đạt, khuyến nghị cho Production Gate.

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| Độ trễ phụ thuộc nhà cung cấp LLM (D-01 chưa chốt) | Ghi rõ `model_id` và phương án (A/B) trong báo cáo; nếu đổi phương án sau pilot thì phải đo lại |
| R-06 — chi phí token khi chạy tải | Giới hạn thời lượng kịch bản 1; dùng câu hỏi ngắn; chạy ngoài giờ |
| TEI CPU là nút cổ chai khi 500 tệp | Theo dõi `ingestion_duration_seconds`; nếu vượt, đề xuất nâng lên GPU T4/L4 như SADD §2.3 đã dự phòng |
| Proxy/Ingress cắt kết nối SSE dài | Xác minh `: ping` 15 giây giữ được kết nối suốt câu trả lời 60 giây |
| Số đo dao động giữa các lần chạy | Chạy mỗi kịch bản ≥ 2 lần, báo cáo cả hai; không kết luận từ một lần chạy |
| Staging yếu hơn prod đáng kể | Nêu rõ giới hạn của kết luận trong báo cáo; không ngoại suy quá mức |

## 7. Kiểm thử bắt buộc

- [ ] p90 `answer_complete_ms` ≤ 15.000 ms ở kịch bản steady (KR1.2)
- [ ] p90 `ttft_ms` ≤ 3.000 ms `[Đề xuất]`
- [ ] PDF 20 trang đạt `ready` ≤ 60 giây trên ≥ 5 tệp mẫu (AC-003.3)
- [ ] Tỷ lệ lỗi < 2% trong suốt kịch bản steady và burst
- [ ] Kịch bản 500 tệp: worker tăng tới tối đa 6 bản sao, tuổi hàng đợi < 5 phút, không job nào bị mất
- [ ] Trong lúc ingestion đột biến, p90 độ trễ hỏi đáp vẫn trong ngưỡng
- [ ] Quá hạn 60 giây trả `ANSWER_TIMEOUT` đúng, không treo kết nối

## 8. Định nghĩa Hoàn thành

- [ ] Báo cáo hiệu năng hoàn chỉnh (cấu hình + số liệu + biểu đồ + kết luận) đã nộp
- [ ] Mọi ngưỡng ở §7 đạt, hoặc có phân tích nguyên nhân + kế hoạch xử lý được Tech Lead chấp nhận
- [ ] Script k6 được lưu trong repo để chạy lại trước Production Gate
- [ ] Dữ liệu test đã dọn sạch khỏi `staging`
- [ ] Tech Lead ký bằng chứng cho Pilot Gate G-06

## 9. Tham chiếu

- [SADD §3.2.2 (ngân sách độ trễ), §2.2.4, §2.3, §4.3 (metric), Phụ lục A.2 (ước lượng tải)](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-06; §0.3 DF-03, DF-10](../../requirements/PRD.md)
- [User Stories — US-003 (AC-003.3), US-011](../../design/User_Stories.md)
- [implement_plan.md §5 Sprint 5, §8.1](../implement_plan.md)
