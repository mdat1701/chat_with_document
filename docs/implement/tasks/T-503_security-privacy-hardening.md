# T-503 — Hoá cứng bảo mật & quyền riêng tư (hồ sơ G-04)

| Thuộc tính | Giá trị |
|---|---|
| Sprint | 5 |
| Story | US-020 (số liệu không chứa nội dung), hỗ trợ US-002, BR-019 |
| Epic | EP-05 (đo lường), EP-01 (phân quyền) |
| Module (SADD §2.2.1) | `core` (bộ lọc log), `qa`, `adapters` (LLM), hạ tầng |
| API liên quan | API-01, API-09 (biên dữ liệu gửi LLM), `/healthz` |
| Vai trò chính | TL (chủ trì) · ATTT (phê duyệt) · QA (canary test) · OPS |
| Ước lượng | 2d |
| Phụ thuộc | T-301 (LLM adapter), T-404 (sự kiện analytics), D-01, D-06 |
| Trạng thái | To do |

## 1. Mục tiêu

Chuẩn bị và chứng minh được hồ sơ cho **Pilot Gate G-04 — "Quyền riêng tư và AI"**: luồng xử lý AI, nơi lưu trữ và dữ liệu thử nghiệm được ATTT phê duyệt; log/analytics **không chứa nội dung** tài liệu, câu hỏi hay câu trả lời.

Đây là cổng có **quyền chặn ra mắt** (BRD STK-004), nên mục tiêu không chỉ là "code đúng" mà là **tạo ra bằng chứng kiểm chứng được** để ATTT ký.

## 2. Tiêu chí nghiệm thu liên quan

| Mã | Tiêu chí kiểm chứng được |
|---|---|
| G-04 | Có biên bản rà soát của ATTT + kết quả canary test đính kèm |
| AC-020.1 | Không sự kiện analytics nào chứa nội dung câu hỏi, câu trả lời, tên tệp hay đoạn trích |
| AC-020.2 | ATTT xác nhận **bằng văn bản** rằng log và metric vận hành không chứa nội dung tài liệu |
| BR-019 | AI chỉ xử lý dữ liệu trong ranh giới đã được ATTT phê duyệt |
| P-03 (SADD) | Nội dung không bao giờ xuất hiện trong log, trace, metric hay analytics |
| CN-06 (SDD) | Không có nội dung tài liệu/câu hỏi trong `localStorage` / `IndexedDB` |

## 3. Hợp đồng / kịch bản cụ thể

**Canary test — chuỗi đánh dấu duy nhất** nhúng vào tài liệu kiểm thử rồi truy quét toàn hệ thống:

```bash
CANARY="CWD-CANARY-7f3a9b2e-DO-NOT-LOG"
# 1. Tải lên PDF chứa CANARY, chờ ready, hỏi một câu về nội dung đó

# 2. Truy quét mọi nơi dữ liệu có thể rò rỉ
kubectl logs -l app=cwd-api  --since=1h | grep -c "$CANARY"     # kỳ vọng: 0
kubectl logs -l app=cwd-worker --since=1h | grep -c "$CANARY"   # kỳ vọng: 0
psql -c "SELECT count(*) FROM analytics_event WHERE props::text ILIKE '%$CANARY%'"  -- kỳ vọng: 0
psql -c "SELECT count(*) FROM audit_log      WHERE target_id::text ILIKE '%$CANARY%'" -- kỳ vọng: 0
curl -s $PROM/api/v1/label/__name__/values | grep -c "$CANARY"  # kỳ vọng: 0
# Tempo/Loki: truy vấn theo khoảng thời gian, kỳ vọng 0 kết quả
```

Trình duyệt (DevTools hoặc script Playwright) sau một phiên làm việc đầy đủ:

```js
// Kỳ vọng: không khóa nào chứa nội dung tài liệu/câu hỏi/câu trả lời
Object.entries(localStorage)   // chỉ tùy chọn giao diện
Object.entries(sessionStorage) // chỉ bản nháp câu hỏi (ngoại lệ có kiểm soát, DQ-04)
indexedDB.databases()          // kỳ vọng: rỗng
```

**Biên dữ liệu gửi LLM** cần chứng minh bằng một trace mẫu: payload tới `LLMPort` chỉ gồm system prompt + câu hỏi + **tối đa 8 đoạn trích** (`RERANK_TOP_OUT`), không gửi toàn văn tài liệu.

## 4. Thay đổi dữ liệu

- Không đổi lược đồ. Có thể bổ sung **test tự động** cho bộ lọc log trong `core`.
- Chốt và áp dụng D-06: thời hạn lưu metadata `answer` (đề xuất 180 ngày) và `audit_log` (đề xuất 1 năm) — cấu hình thành job dọn dẹp nếu ATTT yêu cầu.

## 5. Các bước triển khai

1. Vẽ/cập nhật **sơ đồ luồng dữ liệu** theo ranh giới tin cậy TB-1 (trình duyệt) → TB-2 (hạ tầng nội bộ) → TB-3 (LLM bên thứ ba), chỉ rõ dữ liệu nào đi qua biên nào.
2. Chứng minh **embedding chạy nội bộ**: văn bản tài liệu chỉ tới TEI trong TB-2, không rời ra ngoài (ADR-05) — đính kèm cấu hình TEI và bằng chứng network policy.
3. Chứng minh **tối thiểu hoá dữ liệu gửi LLM**: log một trace mẫu (đã che nội dung) cho thấy chỉ câu hỏi + ≤ 8 đoạn trích được gửi; xác nhận phương án LLM đang dùng khớp D-01 (A hay B theo ADR-03).
4. Rà soát bộ lọc log trong `core`: chặn các trường `question`, `answer`, `content`, `text`, `file_name`, `prompt` ở **mọi** logger; bổ sung unit test cho bộ lọc.
5. Rà soát allow-list analytics: khóa không khai báo bị **loại bỏ** và ghi cảnh báo ở môi trường dev (DR-05); kiểm tra máy chủ cũng lọc lại, không tin client.
6. Chạy **canary test** theo kịch bản §3 trên `staging`, lưu toàn bộ output làm bằng chứng.
7. Kiểm tra cấu hình bảo mật phía biên:
   - Cookie phiên: `HttpOnly`, `Secure`, `SameSite=Lax`; không có token trong JS-readable storage (ADR-08).
   - CSP, `X-Content-Type-Options`, `Referrer-Policy`, HSTS trên Ingress.
   - Bucket object storage: chặn truy cập công khai, SSE-KMS bật, khóa theo tiền tố `owner/{owner_id}/`.
   - TLS cho Redis (TLS + ACL) và PostgreSQL; mã hoá đĩa.
8. Xác minh rate limit hoạt động thật: 60 tệp/giờ và 10 câu hỏi/phút → trả `429 RATE_LIMITED`.
9. Quét phụ thuộc (SCA) back-end + front-end và quét image container; xử lý lỗ hổng mức High trở lên.
10. Họp rà soát với ATTT, trình gói bằng chứng, lấy **xác nhận bằng văn bản** (AC-020.2).

## 6. Rủi ro & trường hợp biên

| Rủi ro / tình huống | Xử lý |
|---|---|
| R-01 / AR-01 — ATTT không chấp nhận LLM bên ngoài | Phải phát hiện **sớm**, không để tới cuối Sprint 5; nếu bị từ chối, kích hoạt phương án B (vLLM tự lưu trữ) qua `LLMPort` — mã miền không đổi |
| Nội dung lọt vào trace qua thư viện bên thứ ba (ORM/HTTP client log query) | Kiểm tra cả log của SQLAlchemy và HTTP client; tắt echo SQL ở `prod` |
| Thông báo lỗi của LLM chứa đoạn prompt | Không log nguyên văn lỗi từ nhà cung cấp; chỉ ghi `error_code` và mã trạng thái |
| AR-05 / D-04 — backup còn giữ tài liệu đã xóa tới 7 ngày | Nêu rõ trong hồ sơ ATTT; nếu không được chấp nhận, rút cửa sổ PITR xuống 1 ngày |
| Bản nháp câu hỏi trong `sessionStorage` (DQ-04) | Trình bày như **ngoại lệ có kiểm soát**: xóa khi gửi câu hỏi hoặc đăng xuất; cần ATTT chấp thuận |

## 7. Kiểm thử bắt buộc

- [ ] Canary test: 0 kết quả ở log api, log worker, trace, metric, `analytics_event`, `audit_log`
- [ ] Sau một phiên đầy đủ: `localStorage`/`IndexedDB` không chứa nội dung tài liệu, câu hỏi hay câu trả lời
- [ ] Unit test bộ lọc log: mọi trường nhạy cảm bị loại trước khi ghi
- [ ] Test allow-list analytics: khóa lạ bị loại bỏ, có cảnh báo ở môi trường dev
- [ ] Rate limit trả đúng `429 RATE_LIMITED` ở cả hai ngưỡng
- [ ] Cookie phiên có đủ `HttpOnly; Secure; SameSite=Lax` (kiểm tra tự động trong E2E)
- [ ] Quét SCA và image không còn lỗ hổng High/Critical chưa xử lý

## 8. Định nghĩa Hoàn thành

- [ ] Gói bằng chứng G-04 hoàn chỉnh: sơ đồ luồng dữ liệu, trace mẫu, kết quả canary, bảng kiểm cấu hình bảo mật
- [ ] **Biên bản rà soát có chữ ký/xác nhận của ATTT** (AC-020.2)
- [ ] D-06 (thời hạn lưu metadata) đã được chốt và áp dụng
- [ ] Các kiểm thử ở §7 chạy tự động trong CI (không phải thủ công một lần)
- [ ] Mọi phát hiện mức High trở lên đã được khắc phục hoặc có chấp nhận rủi ro bằng văn bản

## 9. Tham chiếu

- [SADD §1.2 (P-03), §3.1.3 (cô lập), §4.1 (bảo mật), §4.3 (quan sát), §6.1 AR-01/AR-05](../../requirements/SADD.md)
- [PRD §5.1 — Pilot Gate G-04, §5.2 — nguyên tắc quyền riêng tư](../../requirements/PRD.md)
- [User Stories — US-020 (AC-020.1, AC-020.2), US-002](../../design/User_Stories.md)
- [implement_plan.md §5 Sprint 5, §6 D-01/D-04/D-06, §8.1](../implement_plan.md)
