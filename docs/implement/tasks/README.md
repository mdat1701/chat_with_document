# Danh mục Task — Chat với tài liệu (MVP-lite)

> Thuộc [implement_plan.md](../implement_plan.md) · 47 task · ~97–108 ngày công lý tưởng
> **Cách dùng:** developer nhận việc mở đúng tệp task của mình. Mỗi tệp tự chứa: mục tiêu, tiêu chí nghiệm thu (AC), hợp đồng API/giao diện, thay đổi schema, các bước triển khai, mã lỗi & trường hợp biên, ca kiểm thử bắt buộc và Definition of Done.

## Quy ước tệp task

| Mục | Nội dung |
|---|---|
| Bảng thuộc tính | Sprint · Story (US-xxx) · Epic · Module (SADD §2.2.1) · API liên quan · Vai trò · Ước lượng · Phụ thuộc · Trạng thái |
| §1 Mục tiêu | Làm gì, vì sao, kết quả nhìn thấy được khi xong |
| §2 Tiêu chí nghiệm thu | Trích đúng mã AC-xxx.y từ [User Stories v0.4](../../design/User_Stories.md) |
| §3 Hợp đồng API / giao diện | Request/response đầy đủ, hoặc component + ảnh thiết kế trong [`html_design/`](../../design/html_design/) |
| §4 Thay đổi dữ liệu | Bảng/cột DB, migration cần viết |
| §5 Các bước triển khai | Danh sách đánh số, đủ cụ thể để code ngay |
| §6 Mã lỗi & trường hợp biên | Theo danh mục [SDD §3.4.3](../../design/SDD_UI_UX_Blueprint.md) |
| §7 Kiểm thử bắt buộc | Checklist ca test cụ thể |
| §8 Definition of Done | Checklist hoàn thành |
| §9 Tham chiếu | Link tới SADD / User Stories / SDD / ảnh thiết kế |

**Trạng thái:** `To do` → `In progress` → `In review` → `Done`. Cập nhật trực tiếp trong bảng thuộc tính của tệp task.

---

## Sprint 0 — Nền tảng (13 ngày công)

| Task | Tên | Story | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-001](T-001_monorepo-setup.md) | Monorepo & ranh giới module | — | TL | 1d | **Done** |
| [T-002](T-002_local-dev-environment.md) | Môi trường dev cục bộ (Docker Compose) | — | OPS | 2d | Done (cấu hình, chưa chạy Docker thật) |
| [T-003](T-003_ci-pipeline.md) | CI pipeline | — | TL | 2d | To do |
| [T-004](T-004_staging-skeleton.md) | Khung staging (D-02) | — | OPS | 2d | To do |
| [T-005](T-005_database-baseline.md) | DB baseline & migration | — | BE | 2d | Done (chưa chạy trên Postgres thật) |
| [T-006](T-006_celery-skeleton.md) | Khung Celery worker + beat | — | BE | 1d | Done |
| [T-007](T-007_logging-and-tracing.md) | Logging có bộ lọc nội dung, OTel, ErrorCode | — | TL | 2d | To do |
| [T-008](T-008_backend-skeleton.md) | Khung FastAPI, healthz/readyz | — | BE | 1d | To do |

## Sprint 1 — Truy cập & bắt đầu tải tài liệu (19 ngày công)

| Task | Tên | Story | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-101](T-101_oidc-login.md) | Đăng nhập OIDC (BFF) | US-001 | BE | 3d | To do |
| [T-102](T-102_session-csrf-me.md) | Phiên, CSRF, `GET /me` | US-001 | BE | 1d | To do |
| [T-103](T-103_access-grant-cli.md) | Cấp quyền qua CLI/config | US-023 | BE | 1d | To do |
| [T-104](T-104_owner-scoped-db-access.md) | Cô lập `owner_id` + RLS | US-002 | BE | 2d | To do |
| [T-105](T-105_config-api-and-rate-limit.md) | `GET /config` & rate limit | US-006, US-007 | BE | 1d | To do |
| [T-106](T-106_frontend-shared-foundation.md) | Nền tảng front-end dùng chung | — | FE | 3d | To do |
| [T-107](T-107_auth-screens.md) | Màn hình đăng nhập & chưa cấp quyền | US-001 | FE | 2d | To do |
| [T-108](T-108_upload-api.md) | `POST /documents` (tải lên) | US-003, 004, 006, 007 | BE | 3d | To do |
| [T-109](T-109_upload-client.md) | Client tải lên | US-003, US-004 | FE | 3d | To do |

## Sprint 2 — Hoàn thiện ingestion & quản lý tài liệu (18 ngày công)

| Task | Tên | Story | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-201](T-201_ingestion-scan-and-validate.md) | Quét mã độc & kiểm tra PDF | US-003, US-005 | BE | 3d | To do |
| [T-202](T-202_extraction-and-chunking.md) | Trích xuất & chia đoạn | US-003 | BE | 2d | To do |
| [T-203](T-203_embedding-and-indexing.md) | Embedding & đánh chỉ mục | US-003 | AI | 2d | To do |
| [T-204](T-204_document-events-sse.md) | Trạng thái tài liệu realtime (SSE) | US-010 | BE | 2d | To do |
| [T-205](T-205_document-library-ui.md) | Thư viện tài liệu (UI) | US-009, 010, 021 | FE | 3d | To do |
| [T-206](T-206_delete-document.md) | Xóa tài liệu | US-008 | BE | 2d | To do |
| [T-207](T-207_scheduled-jobs-retention.md) | Job định kỳ & retention (D-04) | US-021 | BE | 2d | To do |
| [T-208](T-208_empty-states-and-delete-confirm.md) | Trạng thái trống & xác nhận xóa | US-003, 008, 010 | FE | 2d | To do |

## Sprint 3 — Hỏi đáp lõi (19 ngày công)

| Task | Tên | Story | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-301](T-301_llm-port-and-adapters.md) | `LLMPort` & 2 adapter (D-01) | — | TL | 3d | To do |
| [T-302](T-302_retrieval-and-evidence-gate.md) | Truy xuất & cổng bằng chứng | US-011, US-013 | AI | 3d | To do |
| [T-303](T-303_prompt-v1-and-citation-check.md) | Prompt v1 & kiểm tra trích dẫn | US-011, US-014 | AI | 2d | To do |
| [T-304](T-304_question-sse-api.md) | API hỏi đáp SSE | US-011 | BE | 3d | To do |
| [T-305](T-305_chat-composer.md) | Composer & chỉ báo đang trả lời | US-011 | FE | 3d | To do |
| [T-306](T-306_answer-rendering-and-citations.md) | Hiển thị câu trả lời & trích dẫn | US-011, US-014 | FE | 3d | To do |
| [T-307](T-307_not-found-and-error-handling.md) | Không tìm thấy & xử lý lỗi | US-013 | FE | 2d | To do |

## Sprint 4 — Hoàn thiện hỏi đáp & đo lường tối thiểu (10 ngày công)

| Task | Tên | Story | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-401](T-401_multi-document-synthesis.md) | Tổng hợp nhiều tài liệu | US-012 | AI | 2d | To do |
| [T-402](T-402_citation-page-numbers.md) | Số trang trong trích dẫn | US-015 | FE | 1d | To do |
| [T-403](T-403_multilingual-qa.md) | Hỏi đáp đa ngôn ngữ | US-017 | AI | 2d | To do |
| [T-404](T-404_minimal-analytics-events.md) | Sự kiện đo lường tối thiểu | US-020 | BE | 2d | To do |
| [T-405](T-405_ui-polish-and-responsive.md) | Hoàn thiện UI & responsive | — | FE | 3d | To do |

## Sprint 5 — Chất lượng & hoá cứng (14 ngày công)

| Task | Tên | Gate | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-501](T-501_rag-evaluation-harness.md) | Bộ đánh giá RAG offline | G-02 | AI | 3d | To do |
| [T-502](T-502_quality-tuning-round1.md) | Hiệu chỉnh chất lượng vòng 1 | G-02 | AI | 3d | To do |
| [T-503](T-503_security-privacy-hardening.md) | Hoá cứng bảo mật & quyền riêng tư | G-04 | TL | 2d | To do |
| [T-504](T-504_isolation-tests-and-e2e.md) | Kiểm thử cô lập & E2E | G-01, G-03 | QA | 2d | To do |
| [T-505](T-505_performance-smoke-test.md) | Kiểm thử hiệu năng quy mô pilot | G-06 | QA | 2d | To do |
| [T-506](T-506_quality-tuning-round2.md) | Hiệu chỉnh chất lượng vòng 2 | G-02 | AI | 2d | To do |

## UAT & Pilot Gate (2 tuần)

| Task | Tên | Gate | Vai trò | Ước lượng | Trạng thái |
|---|---|---|---|---|---|
| [T-601](T-601_uat-execution.md) | Thực hiện UAT | G-07 | PM · BA | 1 tuần | To do |
| [T-602](T-602_uat-defect-fixing.md) | Khắc phục lỗi chặn từ UAT | G-01 – G-07 | Cả đội | Dự phòng | To do |
| [T-603](T-603_pilot-gate-evidence.md) | Tổng hợp bằng chứng Pilot Gate | Tất cả | TL · QA | 2d | To do |
| [T-604](T-604_pilot-runbook.md) | Runbook vận hành pilot | — | OPS | 2d | To do |

---

## Ma trận Story → Task

| Story | Ưu tiên | Task liên quan |
|---|---|---|
| US-001 Đăng nhập | P0 | T-101, T-102, T-107 |
| US-002 Chỉ thấy tài liệu của mình | P0 | T-104, T-504 |
| US-003 Tải một tệp PDF | P0 | T-108, T-109, T-201, T-202, T-203, T-208 |
| US-004 Tải nhiều tệp | P0 | T-108, T-109 |
| US-005 Báo rõ khi tệp lỗi | P0 | T-201, T-205 |
| US-006 Báo khi vượt giới hạn tệp | P0 | T-105, T-108, T-109 |
| US-007 Báo khi đạt hạn mức | P0 | T-105, T-108 |
| US-008 Xóa tài liệu | P0 | T-206, T-208 |
| US-009 Xem danh sách tài liệu | P1 | T-205 |
| US-010 Trạng thái từng tài liệu | P1 | T-204, T-205, T-208 |
| US-011 Đặt câu hỏi | P0 | T-302, T-303, T-304, T-305, T-306 |
| US-012 Tổng hợp nhiều tài liệu | P0 | T-401 |
| US-013 Báo không tìm thấy | P0 | T-302, T-307 |
| US-014 Tên tài liệu nguồn | P0 | T-303, T-306 |
| US-015 Số trang trích dẫn | P1 | T-202, T-402 |
| US-017 Hỏi tiếng Việt/Anh | P0 | T-403 |
| US-020 Số liệu không chứa nội dung | P0 | T-007, T-404, T-503 |
| US-021 Tự động xóa khi hết hạn | P0 | T-205, T-207 |
| US-023 Cấp quyền (CLI/config) | P1 | T-103 |

> **Ngoài phạm vi:** US-016, US-018, US-019, US-022 và màn hình quản trị của US-023 là post-MVP (BRD §5.4) — không có task trong danh mục này.
