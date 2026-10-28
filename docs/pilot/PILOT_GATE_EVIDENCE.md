# Hồ sơ bằng chứng Pilot Gate

## Trạng thái

Hồ sơ này là khung truy vết. Mỗi gate phải được cập nhật bằng artifact từ
đúng build triển khai pilot và chữ ký của người phụ trách trước khi mở pilot.

| Gate | Bằng chứng | Build/commit | Kết luận | Người ký |
|---|---|---|---|---|
| G-01 Core flow | `T-504` E2E report | Chưa chạy | Pending | QA Lead |
| G-02 Quality | `tools/evaluation/reports/baseline.json` | Chưa chạy | Pending | BA Lead + PM |
| G-03 Isolation | Integration isolation report | Chưa chạy | Pending | QA Lead + ATTT |
| G-04 Privacy/AI | Canary report + ATTT minutes | Chưa chạy | Pending | ATTT |
| G-05 Delete/retention | Retention report | Chưa chạy | Pending | QA Lead |
| G-06 Performance | k6 report | Chưa chạy | Pending | Tech Lead |
| G-07 UAT | `UAT_MINUTES.md` | Chưa chạy | Pending | Business owner |

## Known limitations

Các story post-MVP như hỏi tiếp nối, feedback, báo cáo tuần, chấm điểm và
quản trị nâng cao không được coi là blocker nếu không ảnh hưởng cô lập,
citation, xóa dữ liệu hoặc luồng upload → hỏi.

## Decision

- [ ] Open pilot
- [ ] Hold pilot
- Lý do:
- Điều kiện kèm theo:
