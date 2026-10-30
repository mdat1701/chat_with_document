# Báo cáo thực thi — TC-018 Hỏi đáp bằng tiếng Anh

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:15:00+07:00 |
| Kết luận chung | **BLOCKED một phần** — xem chi tiết |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL |
|---|---|---|---|
| KQ1 (phát hiện ngôn ngữ + trả lời đúng ngôn ngữ) | Hệ thống trả lời bằng tiếng Anh khi hỏi tiếng Anh | **BLOCKED** — cùng nguyên nhân TC-013 (thiếu pgvector khiến `retrieve()` lỗi trước khi tới bước chọn ngôn ngữ trả lời) | BLOCKED |
| KQ2 (giao diện vẫn tiếng Việt) | Giao diện không đổi ngôn ngữ theo câu hỏi | Xác nhận được qua đọc code — không có logic nào đổi ngôn ngữ UI theo nội dung câu hỏi (khớp `T-403_multilingual-qa.md`) | PASS (chỉ xác nhận tĩnh, không qua UI thật vì câu hỏi tiếng Anh cũng bị chặn ở bước retrieve) |

## Tham chiếu

- Nguyên nhân & traceback đầy đủ: [`../TC-013_dat-cau-hoi-nhan-tra-loi-co-trich-dan/report.md`](../TC-013_dat-cau-hoi-nhan-tra-loi-co-trich-dan/report.md)
- Ghi chú riêng T-403: `lingua` (thư viện phát hiện ngôn ngữ chính) cũng không cài được trong sandbox này (thiếu C++ Build Tools) — ngay cả khi có pgvector, nhánh phát hiện ngôn ngữ chính xác cao vẫn chưa kiểm chứng được, chỉ nhánh heuristic dự phòng chạy được.

**Việc cần làm để chạy lại ca này:** Postgres có pgvector thật + môi trường cài được `lingua` (Python 3.12 theo Dockerfile, có wheel sẵn).
