# Kế hoạch Kiểm thử Tổng thể (Master Test Plan) — Chat với tài liệu (MVP-lite)

> **Tiêu chuẩn:** IEEE 829-2008 (Software Test Documentation), theo khung ở [`testPlan_prompt.md`](testPlan_prompt.md)
> **Đầu vào:** [BRD v0.3](../requirements/BRD.md) · [PRD v0.2](../requirements/PRD.md) · [SADD v0.3](../requirements/SADD.md) · [User Stories v0.4](../design/User_Stories.md) · [SDD UI/UX v0.3](../design/SDD_UI_UX_Blueprint.md) · [implement_plan.md v0.2](../implement/implement_plan.md) · [Danh mục 47 task](../implement/tasks/README.md)
> **Trạng thái dự án tại thời điểm viết tài liệu này:** 31/47 task **Done** (một số kèm ghi chú "chưa đo trên hạ tầng thật"), 10/47 **In progress**, 6/47 **To do**. Backend: `pytest tests/unit tests/integration -q` → **175 passed, 13 skipped**. Frontend: `npm test -- --run` → **106 passed**. Chi tiết xem Mục 4 và Phụ lục A.

---

## 0. Kiểm soát tài liệu

| Trường | Giá trị |
|---|---|
| Document ID | TP-CWD-001 |
| Phiên bản | 1.0 — Bản nháp |
| Ngày | 2026-10-29 |
| Trạng thái | Draft |
| Phân loại | Internal |
| Soạn bởi | QA (hỗ trợ bởi Tech Lead/AI Agent) |
| Phê duyệt bởi | QA Lead, Tech Lead, PM/BA, An toàn thông tin (ATTT) |

---

## 1. Test Plan Identifier

**Tên tài liệu:** Chat với tài liệu (MVP-lite) — Master Test Plan
**Mã:** TP-CWD-001-v1.0
**Phạm vi phiên bản áp dụng:** toàn bộ 47 task của [implement_plan.md](../implement/implement_plan.md) (Sprint 0 → Sprint 5 → UAT/Pilot Gate), 19 user story P0/P1 trong phạm vi MVP-lite (PRD §0.4, §3; implement_plan §2.1).

---

## 2. Introduction

### 2.1 Purpose

Tài liệu này định nghĩa chiến lược kiểm thử tổng thể cho "Chat với tài liệu" MVP-lite, nhằm:

- Xác lập phạm vi, cấp độ và loại kiểm thử cần thiết để đạt **7 Pilot Gate (G-01 → G-07, PRD §5.1)** — Pilot Gate thay thế hoàn toàn "Launch Gate production" cho MVP-lite (PRD lịch sử phiên bản v0.2).
- Ánh xạ từng tiêu chí nghiệm thu (AC-xxx.y) của 19 user story trong phạm vi tới task triển khai và trạng thái kiểm thử thực tế hiện có (không suy diễn, không nói "đã kiểm thử" khi mới chỉ *viết* test).
- Nêu rõ **ranh giới thật** của môi trường phát triển hiện tại (không có Docker, không có IdP/OIDC thật, không có LLM/TEI thật, không có trình duyệt) và điều kiện cần có để đóng các khoảng trống đó trước khi ký Pilot Gate.
- Là tài liệu tham chiếu duy nhất khi QA Lead, Tech Lead, BA/PM và ATTT ký [`PILOT_GATE_EVIDENCE.md`](../pilot/PILOT_GATE_EVIDENCE.md).

### 2.2 Scope

**Trong phạm vi:**
- Kiểm thử chức năng cho 19 user story P0/P1 (US-001–US-015, US-017, US-020, US-021, US-023 — xem Mục 4.1).
- Kiểm thử phi chức năng: hiệu năng tối thiểu quy mô pilot (G-06), bảo mật/quyền riêng tư dữ liệu AI (G-04), cô lập dữ liệu nhiều người dùng (G-03), khả năng tiếp cận (axe-core, WCAG 2.1 AA ở mức component).
- Kiểm thử API (9 endpoint cốt lõi API-01–API-09 + `POST /events`, SADD §2.4.2).
- Kiểm thử tích hợp module ↔ hạ tầng dữ liệu (Postgres+pgvector/RLS, Redis, MinIO, ClamAV, TEI).
- Kiểm thử end-to-end luồng cốt lõi (upload → xử lý → hỏi → trả lời có nguồn/`not_found` → xóa).
- Hồi quy tự động trên mỗi thay đổi (CI: `.github/workflows/ci.yml`).
- UAT với nhóm người dùng thử nghiệm thật (T-601/T-602).
- Tổng hợp bằng chứng và ký Pilot Gate (T-603).

**Ngoài phạm vi (post-MVP theo PRD §1.1, §3.7 EP-06; không viết test cho các mục này):**
- US-016 (hỏi tiếp nối), US-018 (feedback 👍/👎), US-019 (báo cáo tuần), US-022 (công cụ chấm điểm UI), US-024–US-030 (backlog EP-06).
- Màn hình quản trị của US-023 (chỉ CLI/config trong MVP-lite).
- Load test vượt quy mô pilot (10 người dùng đồng thời theo T-505 — không phải load test production quy mô lớn).
- Penetration testing thật bởi bên thứ ba (chỉ có SAST/SCA tự động trong CI + canary test nội bộ — xem Mục 6.1.7).
- OCR / PDF scan (DF-04 loại trừ tường minh).
- Đa vùng / vận hành 24/7 (D-07 chưa chốt, sau Pilot Gate).

### 2.3 Objectives

| Mã | Mục tiêu | Tiêu chí thành công | Truy xuất |
|---|---|---|---|
| OBJ-001 | Xác nhận 19 story P0/P1 đạt AC tương ứng | 100% AC có ca kiểm thử truy xuất được; ca P0 phải **pass thật** trên hạ tầng staging trước khi ký G-01 | US-001…US-023 |
| OBJ-002 | Xác nhận cô lập dữ liệu giữa người dùng | 0 trường hợp người dùng A thấy/truy vấn được tài liệu của B, kể cả bằng SQL trực tiếp | G-03, US-002 |
| OBJ-003 | Xác nhận chất lượng câu trả lời RAG | ≥ 85% đúng có nguồn (KR2.1), 100% câu không đáp án trả `not_found` (KR2.2), 100% câu có nội dung có ≥ 1 trích dẫn (KR2.3) — đo bằng [`tools/evaluation/run_eval.py`](../../tools/evaluation/run_eval.py) trên bộ câu hỏi chuẩn thật | G-02, KR2.1–2.3 |
| OBJ-004 | Xác nhận không rò rỉ nội dung qua log/metric/analytics | Canary string không xuất hiện trong `analytics_event`, log, trace sau một vòng upload→hỏi→xóa thật | G-04, US-020 |
| OBJ-005 | Xác nhận hiệu năng tối thiểu quy mô pilot | p90 `answer_rendered.latency_ms` ≤ 15s (KR1.2/DF-10), tài liệu 20 trang → "Sẵn sàng" ≤ 60s (AC-003.3) ở 10 người dùng đồng thời | G-06, [T-505](../implement/tasks/T-505_performance-smoke-test.md) |
| OBJ-006 | Xác nhận khả năng tiếp cận ở mức component | 0 vi phạm axe-core mức `serious`/`critical` trên 20 component tương tác đã có test | DoD §8.2 implement_plan |
| OBJ-007 | Hoàn tất UAT không còn lỗi chặn | Nhóm người dùng thử nghiệm hoàn thành luồng chính; biên bản UAT không còn mục "Blocker" mở | G-07 |

### 2.4 References

| Tài liệu | Phiên bản | Dùng cho |
|---|---|---|
| [BRD-CWD-001](../requirements/BRD.md) | v0.3 | Mục tiêu kinh doanh, BO/BR gốc |
| [PRD-CWD-001](../requirements/PRD.md) | v0.2 | DF-01–DF-10, 30 user story + AC, Pilot Gate G-01–G-07 (§5.1), sự kiện analytics (§5.2), danh mục mã lỗi hiển thị |
| [SADD-CWD-001](../requirements/SADD.md) | v0.3 | Modular monolith (§2.2.1), 9 module, port/adapter, pipeline ingestion (§2.2.2)/hỏi đáp (§2.2.3), API-01–API-09 (§2.4.2), mô hình dữ liệu + RLS (§3.1), ADR (Phụ lục C) |
| [SDD UI/UX v0.3](../design/SDD_UI_UX_Blueprint.md) | v0.3 | Cây thành phần, mã lỗi hiển thị (§3.4.3), phím tắt (§3.5.2), máy trạng thái (§3.7) |
| [User Stories v0.4](../design/User_Stories.md) | v0.4 | AC chi tiết từng story, 29 ảnh thiết kế |
| [implement_plan.md](../implement/implement_plan.md) | v0.2 | WBS 47 task, D-01–D-07, R-01–R-07, ánh xạ Pilot Gate §8.1 |
| [Danh mục 47 task](../implement/tasks/README.md) | — | **Nguồn sự thật** cho trạng thái triển khai/kiểm thử hiện tại của từng task |
| [`docs/pilot/*.md`](../pilot/) | — | Khung UAT, runbook, bằng chứng Pilot Gate — tái sử dụng, không nhân bản |
| IEEE 829-2008 | 2008 | Khung cấu trúc tài liệu này |

---

## 3. Test Items

### 3.1 Thành phần phần mềm cần kiểm thử

| Mã | Thành phần | Công nghệ | Nguồn |
|---|---|---|---|
| SI-001 | Back-end API + worker (modular monolith) | Python 3.12, FastAPI, SQLAlchemy 2 async, Celery 5 | `backend/app/{api,modules,ports,adapters,workers,core}` |
| SI-002 | 9 module nghiệp vụ | `identity`, `documents`, `ingestion`, `retrieval`, `qa`, `analytics`, `retention`, `feedback`*, `evaluation`* (*post-MVP/ngoài sản phẩm) | SADD §2.2.1 |
| SI-003 | Front-end SPA | React + TypeScript + Vite + TanStack Query | `frontend/src` |
| SI-004 | Migration cơ sở dữ liệu | Alembic, PostgreSQL 16 + pgvector 0.8 | `backend/migrations/` |
| SI-005 | Tác vụ nền | Celery worker + beat (`retention.purge_expired`, `ingestion.reap_stuck`, `blob.reconcile_orphans`) | `backend/app/workers/` |
| SI-006 | Ảnh Docker triển khai | `api`, `worker`, `beat`, `web` + hạ tầng dữ liệu (Postgres+pgvector, Redis, MinIO, ClamAV, TEI) | `infra/docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| SI-007 | Script đánh giá/hiệu năng/bảo mật ngoài sản phẩm | `tools/evaluation/`, `k6/`, `tools/security/` | T-501, T-505, T-503 |
| SI-008 | Cấu hình CI | GitHub Actions | `.github/workflows/ci.yml` |

### 3.2 Artifact kiểm thử hiện có

| Mã | Tên | Định dạng | Vị trí | Trạng thái |
|---|---|---|---|---|
| TA-001 | Unit test back-end | pytest | `backend/tests/unit/` | 175 passed (gộp cả integration), chạy được không cần hạ tầng ngoài |
| TA-002 | Integration test back-end (Testcontainers) | pytest + testcontainers | `backend/tests/integration/` (`test_owner_isolation.py`, `test_upload_concurrency.py`, `test_baseline_migration.py`, `test_identity_repository.py`) | Viết đầy đủ, **tự `pytest.skip()` khi không có Docker** — 13 test hiện skip trong môi trường dev hiện tại, **chưa xác nhận pass** trên Postgres/Redis thật |
| TA-003 | Unit + component test front-end | Vitest + Testing Library + axe-core | `frontend/src/**/*.test.tsx` | 106 passed, 25 file, 20 file có kiểm tra axe-core |
| TA-004 | E2E test | Playwright | `frontend/e2e/core-flow.spec.ts` (2 kịch bản G-01) | Viết xong, **chưa chạy lần nào** — không có trình duyệt/`npm run dev` song song trong môi trường viết task |
| TA-005 | Bộ đánh giá chất lượng RAG | Python script + YAML dataset | `tools/evaluation/run_eval.py`, `golden_set.yaml`, `no_answer_set.yaml`, `reports/baseline.json` (rỗng) | Script chạy được cú pháp (`py_compile`), **chưa có số liệu thật** (thiếu LLM/TEI) |
| TA-006 | Script kiểm thử hiệu năng | k6 | `k6/ingestion_burst.js`, `k6/qa_load.js` | Viết xong, **chưa chạy** (thiếu staging) |
| TA-007 | Script bảo mật/quyền riêng tư | Python | `tools/security/canary_scan.py`, `privacy_checklist.md` | Kịch bản canary scan có; **canary end-to-end thật** (upload→hỏi→quét log/DB/Prometheus) chưa chạy |
| TA-008 | Môi trường kiểm thử | Docker Compose + Testcontainers | `infra/docker-compose.yml` | Cấu hình đầy đủ, **chưa chạy thật** trong môi trường phát triển các task này (không có Docker) |
| TA-009 | Khung bằng chứng/biên bản pilot | Markdown | `docs/pilot/*.md` | Khung sẵn sàng, toàn bộ ở trạng thái Pending |

---

## 4. Features to be Tested

### 4.1 Ma trận truy xuất User Story → AC → Task → Cấp độ kiểm thử → Trạng thái hiện tại

> Nguồn trạng thái: [`docs/implement/tasks/README.md`](../implement/tasks/README.md) tại thời điểm viết tài liệu này. "Pass thật" nghĩa là test đã chạy và xanh trên hạ tầng mục tiêu (không chỉ chạy đúng cú pháp/skip đúng cách).

| Story | Ưu tiên | AC chính | Task | Cấp độ kiểm thử | Trạng thái kiểm thử hiện tại |
|---|---|---|---|---|---|
| US-001 Đăng nhập | P0 | AC-001.1–.4 | T-101, T-102, T-107 | Unit (39 test T-101, `FakeOIDCAdapter`+`fakeredis`) + Component (axe-core `AuthScreens.test.tsx`) + E2E (`core-flow.spec.ts`, gián tiếp) | Unit **pass thật**; luồng OIDC thật **chưa chạy** (không có IdP — D-03 chưa chốt); E2E chưa chạy |
| US-002 Cô lập dữ liệu | P0 | AC-002.1–.3 | T-104, T-504 | Unit (RLS policy) + Integration (Testcontainers, 4 test gồm 2 ca SQL trực tiếp bỏ qua tầng ứng dụng) | Unit pass thật; Integration **viết đúng, chỉ xác nhận skip đúng cách**, chưa chạy trên Postgres thật |
| US-003 Tải 1 PDF | P0 | AC-003.1–.3 | T-108, T-109, T-201, T-202, T-203, T-208 | Unit (ingestion, upload) + Integration (quota/concurrency) + Component (UploadDropzone) | Unit pass thật (175 test gộp); AC-007.2 (song song) viết bằng Testcontainers, chưa chạy thật; ClamAV/TEI thật chưa test |
| US-004 Tải nhiều tệp | P0 | AC-004.1–.3 | T-108, T-109 | Unit + Integration | Như US-003 |
| US-005 Báo lỗi tệp | P0 | AC-005.1–.2 | T-201, T-205 | Unit (6 test: hỗn hợp/NFC/giới hạn) | Pass thật ở mức unit; chưa chạy với ClamAV thật |
| US-006 Giới hạn tệp | P0 | AC-006.1–.3 | T-105, T-108, T-109 | Unit + Component (magic-byte check `files.test.ts`, 5 test mới) | Pass thật |
| US-007 Hạn mức tài liệu | P0 | AC-007.1–.2 | T-105, T-108 | Unit + Integration (`test_upload_concurrency.py`) | AC-007.1 pass thật (unit); AC-007.2 (5 upload đồng thời tranh 2 chỗ) viết đúng, chưa chạy thật |
| US-008 Xóa tài liệu | P0 | AC-008.1–.3 | T-206, T-208 | Unit + Component (`DeleteConfirmDialog.test.tsx`) | Pass thật |
| US-009 Danh sách tài liệu | P1 | AC-009.1–.4 | T-205 | Component (`DocumentLibrary.test.tsx`, skeleton, điều hướng mũi tên) | Pass thật; AC-009.2 (hiệu năng cuộn 50 tài liệu ≤100ms) chưa đo trên dữ liệu thật |
| US-010 Trạng thái tài liệu | P1 | AC-010.1–.3 | T-204, T-205, T-208 | Unit (SSE pub/sub) + Component (`StatusBadge.test.tsx`, axe-core) | Pass thật ở mức unit/component; độ trễ SSE ≤5s (AC-010.1) chưa đo trên staging |
| US-011 Đặt câu hỏi | P0 | AC-011.1–.5 | T-302, T-303, T-304, T-305, T-306 | Unit (retrieval, qa, SSE) + Component (`Composer.test.tsx`, `ChatPage.test.tsx`) | Pass thật ở mức unit/component với `FakeLLM`/dữ liệu giả; **AC-011.5 (≥85% đúng) cần T-501 chạy thật với LLM thật** — chưa có số liệu |
| US-012 Tổng hợp đa tài liệu | P0 | AC-012.1–.2 | T-401 | Unit (`test_retrieval_service.py`, `test_qa_service.py` — bằng chứng rải 2 tài liệu) | Pass thật ở mức unit; chưa chạy với TEI/rerank thật |
| US-013 Không tìm thấy | P0 | AC-013.1–.3 | T-302, T-307 | Unit (cổng bằng chứng τ) + Component (`NotFoundMessage`) | Pass thật ở mức unit; AC-013.2 (bộ ≥10 câu không đáp án, KR2.2) cần T-501 chạy thật |
| US-014 Tên tài liệu nguồn | P0 | AC-014.1–.4 | T-303, T-306 | Unit (kiểm tra trích dẫn, `test_qa_service.py` AC-014.2 đa tài liệu) + Component | Pass thật ở mức unit; AC-014.3 (đối chiếu nội dung thật) cần bộ câu hỏi chuẩn + người đánh giá |
| US-015 Số trang trích dẫn | P1 | AC-015.1–.3 | T-202, T-402 | Unit (`citations.ts` test) | AC-015.1/.3 pass thật; AC-015.2 (đối chiếu thủ công với PDF thật) chưa làm |
| US-017 Đa ngôn ngữ | P0 | AC-017.1–.3 | T-403 | Unit (`test_qa_language_detection.py`, 4 test, 2 lớp fallback) | Pass thật **chỉ ở nhánh heuristic dự phòng** — `lingua` (nhánh chính) không cài được trong sandbox (thiếu C++ Build Tools cho Python 3.15); AC-017.3 (KR2.1 theo ngôn ngữ) cần T-501 |
| US-020 Sự kiện không chứa nội dung | P0 | AC-020.1–.2 | T-007, T-404, T-503 | Unit (allow-list, hash một chiều, `test_logging_scrub.py` canary-string) | Pass thật ở mức unit; **canary end-to-end thật** (G-04) và xác nhận văn bản ATTT chưa có |
| US-021 Tự xóa hết hạn | P0 | AC-021.1–.2 | T-205, T-207 | Unit (retention job, sửa lỗi `reap_stuck` thiếu publish SSE) | Pass thật ở mức unit; chưa đo trên staging với Celery beat thật |
| US-023 Cấp quyền CLI | P1 | AC-023.1–.2 | T-103 | Unit | Pass thật |

### 4.2 Ma trận cấp độ kiểm thử theo tính năng

| Tính năng (Epic) | Unit | Integration | E2E | UAT | Hồi quy | Hiệu năng | Bảo mật | Khả năng tiếp cận |
|---|---|---|---|---|---|---|---|---|
| EP-01 Truy cập & phân quyền | ✓ pass | ◐ viết, chưa chạy | ◐ viết, chưa chạy | ○ chờ T-601 | ✓ (CI) | — | ✓ RLS/CSRF unit | ✓ |
| EP-02 Quản lý tài liệu | ✓ pass | ◐ viết, chưa chạy | ◐ viết, chưa chạy | ○ chờ T-601 | ✓ (CI) | ○ chờ T-505 | ✓ ClamAV mock, chưa thật | ✓ |
| EP-03 Hỏi đáp | ✓ pass (Fake LLM) | — | ◐ viết, chưa chạy | ○ chờ T-601 | ✓ (CI) | ○ chờ T-505 | ✓ chống prompt injection (unit) | ✓ |
| EP-04 Trích dẫn | ✓ pass | — | ◐ (gộp vào core-flow) | ○ | ✓ (CI) | — | — | ✓ |
| EP-05 Đo lường tối thiểu | ✓ pass | — | — | — | ✓ (CI) | — | ◐ canary unit, chưa E2E | — |

Chú thích: ✓ = có và pass thật · ◐ = đã viết nhưng chưa xác nhận pass trên hạ tầng mục tiêu · ○ = chưa bắt đầu · "—" = không áp dụng cho epic này.

### 4.3 Mô tả chi tiết tính năng (nhóm theo Epic, PRD §3.1)

| Epic | Tên | Story trong phạm vi | AC tiêu biểu |
|---|---|---|---|
| EP-01 | Truy cập và phân quyền | US-001, US-002, US-023 | AC-001.1–.4, AC-002.1–.3, AC-023.1–.2 |
| EP-02 | Quản lý tài liệu | US-003–US-010, US-021 | AC-003.1–.3 … AC-021.1–.2 |
| EP-03 | Hỏi đáp trên tài liệu | US-011, US-012, US-013, US-017 | AC-011.1–.5, AC-012.1–.2, AC-013.1–.3, AC-017.1–.3 |
| EP-04 | Trích dẫn và kiểm chứng | US-014, US-015 | AC-014.1–.4, AC-015.1–.3 |
| EP-05 | Phản hồi và đo lường MVP (chỉ phần P0 US-020) | US-020 | AC-020.1–.2 |

---

## 5. Features Not to be Tested

| Mã | Tính năng | Lý do | Ảnh hưởng | Kế hoạch |
|---|---|---|---|---|
| F-NT-01 | US-016 hỏi tiếp nối, US-018 feedback 👍/👎, US-019 báo cáo tuần, US-022 chấm điểm UI | Post-MVP, chưa có task triển khai (implement_plan §2.1) | Không | Chờ BRD OQ-011 phê duyệt mở rộng phạm vi |
| F-NT-02 | US-024–US-030 (EP-06 backlog) | Chưa thuộc phạm vi MVP-lite | Không | Chờ phê duyệt riêng |
| F-NT-03 | Màn hình quản trị cấp quyền (chỉ CLI/config trong MVP-lite) | Quyết định phạm vi chủ động (BRD §5.0) | Thấp — vận hành thủ công qua CLI đã có test | Có thể bổ sung sau pilot |
| F-NT-04 | Penetration test thật bởi bên thứ ba | Cần ngân sách/nhà cung cấp ngoài, không nằm trong năng lực đội hiện tại | Trung bình — chỉ có SAST/SCA tự động + canary nội bộ | Khuyến nghị thực hiện trước Production Gate |
| F-NT-05 | Load test vượt quy mô pilot (>10 người dùng đồng thời) | Ngoài phạm vi G-06 (PRD §5.1: "quy mô pilot") | Thấp cho pilot, cần làm trước mở rộng | Production Gate |
| F-NT-06 | OCR / PDF scan | DF-04 loại trừ tường minh | Không | P-08 (backlog) |
| F-NT-07 | Đa trình duyệt ngoài Chrome/Edge/Firefox 2 bản mới nhất, thiết bị di động thật | DoD chỉ yêu cầu 3 trình duyệt desktop (implement_plan §8.2); MVP ưu tiên desktop (PRD trụ cột UX) | Thấp | — |
| F-NT-08 | Vận hành 24/7, đa vùng (D-07) | Quyết định hoãn sau Pilot Gate | Không cho pilot | Production Gate |

---

## 6. Approach

### 6.1 Cấp độ và loại kiểm thử

#### 6.1.1 Unit Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | BE, AI, FE (theo module đang sửa) |
| Công cụ | Back-end: `pytest` + `ruff` (lint) + `mypy` (type) + `import-linter` (ranh giới module ADR-01) · Front-end: `vitest` + `@testing-library/react` + `eslint` + `tsc --noEmit` + `jest-axe`/`axe-core` |
| Mục tiêu bao phủ | Không đặt ngưỡng % cứng (dự án MVP-lite, đội nhỏ); thay vào đó **mọi AC P0 phải có ít nhất 1 test unit truy xuất được** |
| Entry criteria | Code đã qua self-review, hợp đồng API/schema đã chốt trong tệp task |
| Exit criteria | `ruff check .`, `mypy app`, `lint-imports`, `pytest` (back-end) và `tsc -b`, `eslint`, `prettier --check`, `vitest` (front-end) đều xanh |
| Kết quả hiện tại | **Back-end: 175 passed, 13 skipped** (13 skip là test integration cần Docker, xem 6.1.2) · **Front-end: 106 passed**, 25 file test, 20 file có kiểm tra axe-core |
| Mocking | `FakeOIDCAdapter`, `FakeLLM`, `fakeredis`, `InMemorySpanExporter` (OTel) thay cho dịch vụ ngoài — test double implement đúng `Port` tương ứng (ADR-01), không mock nội bộ domain logic |

#### 6.1.2 Integration Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | BE, QA |
| Công cụ | `pytest` + `testcontainers` (PostgreSQL 16 + pgvector, Redis 7) + `httpx.AsyncClient`/`asyncio.gather` cho kịch bản đồng thời |
| Phạm vi | RLS 2 người dùng (`test_owner_isolation.py`, 4 ca gồm 2 ca chạy SQL trực tiếp qua vai trò `cwd_app` bỏ qua tầng ứng dụng), tranh chấp hạn mức khi upload đồng thời (`test_upload_concurrency.py`, AC-007.2: 5 upload tranh 2 chỗ còn lại → kỳ vọng đúng 2×201 + 3×422), migration Alembic (`test_baseline_migration.py`), repository danh tính (`test_identity_repository.py`) |
| Entry criteria | Unit test module liên quan đã xanh |
| Exit criteria | Toàn bộ test integration **pass thật** (không chỉ skip đúng cách) trên một Docker host có Testcontainers |
| **Trạng thái thật hiện tại** | Toàn bộ 13 test ở trên **tự `pytest.skip()`** vì môi trường phát triển các task này không có Docker Engine. Đã xác nhận: code thu thập đúng, không lỗi cú pháp/fixture, và logic được viết đúng theo đọc kỹ hành vi RLS/khóa hàng Postgres — **nhưng chưa một lần nào thực sự chạy và pass**. Đây là khoảng trống bắt buộc phải đóng (chạy trên một máy có Docker) trước khi ký G-01/G-03 |

#### 6.1.3 System / End-to-End Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | QA |
| Công cụ | Playwright (`frontend/e2e/core-flow.spec.ts`) |
| Phạm vi | G-01: (1) "upload, ask with citation, and delete" — tải PDF, chờ Sẵn sàng, hỏi, nhận câu trả lời có trích dẫn, xóa tài liệu; (2) "empty state has no answer citations" — trạng thái trống không có thẻ nguồn giả |
| Entry criteria | Integration test pass thật, build FE+BE chạy được cùng lúc |
| Exit criteria | 2/2 kịch bản Playwright pass trên Chrome (desktop) |
| **Trạng thái thật hiện tại** | 2 kịch bản đã viết đúng cú pháp Playwright (`playwright.config.ts` trỏ `testDir: "./e2e"`, dùng `webServer` tự chạy `npm run dev`) nhưng **chưa từng được chạy một lần nào** — môi trường viết các task này không có trình duyệt/Playwright browser binary cài sẵn |

#### 6.1.4 Acceptance Testing (UAT)

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | PM, BA, nhóm người dùng thử nghiệm (PER-01) |
| Công cụ | Biên bản thủ công (`docs/pilot/UAT_FORM.md`, `UAT_MINUTES.md`) |
| Phạm vi | Toàn bộ luồng chính PRD §2.2 (đăng nhập → tải tài liệu → hỏi → kiểm chứng → xóa) |
| Entry criteria | G-01, G-02, G-03, G-04, G-05, G-06 đã Pass hoặc có kế hoạch khắc phục rõ ràng |
| Exit criteria | Biên bản UAT không còn "Blocker" mở (G-07) |
| Trạng thái hiện tại | Mẫu biên bản sẵn sàng ([T-601](../implement/tasks/T-601_uat-execution.md)); chưa chạy UAT thật — cần nhóm người dùng thật và môi trường staging |

#### 6.1.5 Regression Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | CI tự động (không có đội regression riêng — quy mô đội nhỏ, implement_plan §3.1) |
| Công cụ | GitHub Actions (`.github/workflows/ci.yml`) |
| Phạm vi | Toàn bộ unit test (back-end + front-end) + lint + typecheck + boundaries (import-linter) + build image trên mỗi PR |
| Trigger | Mỗi PR vào `main`; job `backend-test` dùng Testcontainers thật trong CI (khác môi trường dev local không có Docker) |
| Tần suất | Mỗi commit/PR |
| **Trạng thái thật hiện tại** | Pipeline đã định nghĩa đầy đủ (`lint → typecheck → boundaries → backend-test → frontend-test → sca/sast → build`); `e2e` và `rag-eval` là job rỗng, **bật khi T-504/T-501 có kết quả chạy thật**. Pipeline này **chưa từng chạy trên GitHub Actions thật** (README dự án ghi rõ "Done (chưa chạy trên GitHub Actions)" cho T-003) |

#### 6.1.6 Performance Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | QA, Tech Lead |
| Công cụ | k6 |
| Phạm vi | `k6/ingestion_burst.js` (tải nhiều PDF đồng thời), `k6/qa_load.js` (10 người dùng hỏi đồng thời, đo p90 latency) |
| Mục tiêu (G-06) | p90 `answer_rendered.latency_ms` ≤ 15.000 ms (KR1.2); tài liệu 20 trang → "Sẵn sàng" ≤ 60s (AC-003.3); không timeout vượt DF-10 = 60s |
| Entry criteria | Staging chạy được với hạ tầng dữ liệu thật + LLM/TEI thật |
| **Trạng thái thật hiện tại** | Script viết xong ([T-505](../implement/tasks/T-505_performance-smoke-test.md)), **chưa chạy lần nào** — không có staging/cụm thật trong môi trường phát triển |

#### 6.1.7 Security & Privacy Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | Tech Lead, ATTT |
| Công cụ | `tools/security/canary_scan.py`, SAST/SCA tự động trong CI (`sca`/`sast` job song song), `test_logging_scrub.py`, `test_analytics_service.py` |
| Phạm vi | (1) Bộ lọc log không rò rỉ nội dung (`question`, `answer`, `content`, `text`, `file_name`, `prompt`) ở mọi logger/span OTel — có test unit canary-string; (2) Allow-list sự kiện analytics không chứa nội dung — có test unit; (3) Canary **end-to-end thật**: upload PDF chứa chuỗi canary duy nhất → hỏi → quét `analytics_event`/log/metric thật, khẳng định chuỗi không xuất hiện; (4) RLS cô lập dữ liệu (xem 6.1.2); (5) CSRF, cookie `HttpOnly;Secure;SameSite=Lax`, rate limit, security headers |
| **Trạng thái thật hiện tại** | (1) và (2) **pass thật** ở mức unit — hai lớp phòng thủ độc lập cho P-03 (SADD). (3) canary end-to-end **chưa chạy** — cần staging. SAST/SCA tự động **chưa chạy** trên registry/scanner thật (không có trong sandbox phát triển) |

#### 6.1.8 Accessibility Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | FE, QA |
| Công cụ | `jest-axe`/`axe-core` qua `expectNoA11yViolations` (helper dùng chung `shared/testing/axe.ts`) |
| Chuẩn | WCAG 2.1 AA (mức component, chưa phải quét toàn trang bằng công cụ như Wave/Lighthouse trên bản dựng thật) |
| Phạm vi hiện có | 20 file test: `AuthScreens`, `AnswerMessage`, `ChatPage`, `CitationChip`, `Composer`, `DeleteConfirmDialog`, `DocumentLibrary`, `DuplicateFileDialog`, `StatusBadge`, `UploadDropzone`, và 10 component `shared/ui/*` (Badge, Banner, Button, Dialog, Drawer, EmptyState, OfflineBanner, Skeleton, Toast, Tooltip) |
| **Trạng thái thật hiện tại** | 0 vi phạm mức `serious`/`critical` **ở cấp component** (pass thật, 106 test front-end bao gồm các ca này). **Chưa** kiểm tra zoom 200%, điều hướng bằng trình đọc màn hình thật (NVDA/VoiceOver), hay quét toàn trang đã render đầy đủ trong trình duyệt — cần trình duyệt thật |

#### 6.1.9 UI/UX Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | FE, QA, Thiết kế |
| Công cụ | Đọc code đối chiếu `html_design/` (29 ảnh thiết kế) thủ công; chưa có visual regression tool tự động |
| Phạm vi | So khớp 29 màn hình ở 1280px và 1024px (DoD implement_plan §8.2), 7 trạng thái Composer, 5 trạng thái trống ES-01–ES-05, trạng thái tài liệu ⏳✅❌⚠ |
| **Trạng thái thật hiện tại** | Phần lớn trạng thái/component đã triển khai đúng theo đọc code (xem ghi chú từng task T-107/T-109/T-305/T-306/T-405); **so khớp ảnh pixel-by-pixel chưa thực hiện** cho bất kỳ màn hình nào — cần trình duyệt/công cụ chụp màn hình thật |

#### 6.1.10 API Testing

| Thuộc tính | Mô tả |
|---|---|
| Đội phụ trách | BE, QA |
| Công cụ | `httpx.AsyncClient`/`TestClient` trong pytest (không dùng Postman/Newman riêng — hợp đồng API được test trực tiếp bằng test tích hợp mức router) |
| Phạm vi | 9 endpoint cốt lõi + `POST /events` (SADD §2.4.2) |

**Bao phủ API:**

| Endpoint | Method | Loại test | Trạng thái |
|---|---|---|---|
| `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | GET/GET/POST | Unit (`FakeOIDCAdapter`) | Pass thật; luồng với IdP thật chưa chạy |
| `GET /me` (API-01) | GET | Unit | Pass thật |
| `GET /config` (API-02) | GET | Unit | Pass thật |
| `GET /documents` (API-03) | GET | Unit | Pass thật |
| `POST /documents` (API-04/05) | POST | Unit + Integration (đồng thời) | Unit pass thật; đồng thời (AC-007.2) viết đúng, chưa chạy thật |
| `POST /documents/{id}/retry` | POST | Unit | Pass thật |
| `GET /documents/events` (API-06, SSE) | GET (SSE) | Unit | Pass thật; độ trễ thật (≤5s) chưa đo |
| `DELETE /documents/{id}` (API-07) | DELETE | Unit | Pass thật |
| `POST /conversations` (API-08) | POST | Unit | Pass thật |
| `POST /conversations/{cid}/questions` (API-09, SSE) | POST (SSE) | Unit (Fake LLM) | Pass thật với LLM giả; chưa chạy với LLM thật |
| `POST /events` | POST | Unit | Pass thật |
| `GET /healthz`, `GET /readyz` | GET | Unit | Pass thật |

### 6.2 Test Execution Strategy

1. **Vòng lặp dev hằng ngày:** mỗi thay đổi chạy đủ bộ unit (`ruff`/`mypy`/`lint-imports`/`pytest` back-end, `tsc`/`eslint`/`prettier`/`vitest` front-end) **cục bộ trước khi mở PR** — không phụ thuộc Docker.
2. **CI trên mỗi PR:** lặp lại bộ unit + chạy integration test thật (CI có Docker/Testcontainers, khác máy dev) + SAST/SCA + build image.
3. **Trước mỗi lần chốt Sprint 5 / trước UAT:** chạy bằng tay (hoặc CI job riêng khi đã bật): E2E Playwright, k6, `run_eval.py` với LLM/TEI thật, canary end-to-end.
4. **UAT:** thực hiện bằng tay theo kịch bản `UAT_FORM.md` với người dùng thật.
5. **Tổng hợp Pilot Gate:** T-603 gom toàn bộ báo cáo ở bước 2–4 vào `PILOT_GATE_EVIDENCE.md`, không gate nào được ký chỉ dựa trên "đã viết test".

---

## 7. Item Pass/Fail Criteria

Tiêu chí Pass/Fail cấp hệ thống **bám trực tiếp theo 7 Pilot Gate của PRD §5.1** — không định nghĩa tiêu chí ra mắt riêng, tránh lệch số hiệu như CL-01 (implement_plan §9) đã ghi nhận.

| Gate | Nhóm | Tiêu chí (nguyên văn PRD §5.1) | Bằng chứng | Người ký |
|---|---|---|---|---|
| **G-01** | Luồng cốt lõi | Upload PDF → xử lý → hỏi → câu trả lời có nguồn hoặc `not_found` hoạt động end-to-end | E2E (`core-flow.spec.ts` pass thật) + demo | QA Lead |
| **G-02** | Chất lượng | Bộ câu hỏi chuẩn nhỏ có thể chạy offline; mọi câu trả lời phải có căn cứ hoặc `not_found`; ngưỡng chính thức được chốt sau baseline | Phiếu đánh giá (`tools/evaluation/reports/baseline.json` có số liệu thật) | BA Lead + PM |
| **G-03** | Cô lập dữ liệu | Người dùng không thể xem hoặc truy vấn tài liệu của người khác | Integration test 2 người dùng **pass thật** (`test_owner_isolation.py`, kể cả 2 ca SQL trực tiếp) | QA Lead + ATTT |
| **G-04** | Quyền riêng tư và AI | Luồng xử lý AI, nơi lưu trữ và dữ liệu thử nghiệm được ATTT phê duyệt; log/analytics không chứa nội dung | Biên bản rà soát ATTT + canary test **end-to-end thật** | ATTT |
| **G-05** | Xóa và retention | Xóa thủ công và dọn dẹp hết hạn không còn cho phép truy xuất tài liệu | Integration test retention pass thật trên staging | QA Lead |
| **G-06** | Hiệu năng tối thiểu | Tài liệu mẫu và câu hỏi mẫu hoàn thành trong giới hạn DF-03/DF-10 ở quy mô pilot | Báo cáo k6 (`qa_load.js`, `ingestion_burst.js`) chạy thật | Tech Lead |
| **G-07** | UAT | Nhóm người dùng thử nghiệm hoàn thành luồng chính, không còn lỗi chặn | Biên bản UAT (`UAT_MINUTES.md`) | Chủ sở hữu nghiệp vụ |

**Nguyên tắc chung (PRD §5.1):** *"Các vấn đề được phép tồn tại khi ra mắt: lỗi Minor về giao diện và các story P1/P2 chưa hoàn thành, miễn là không ảnh hưởng tới cô lập dữ liệu, nguồn trích dẫn, xóa dữ liệu hoặc luồng upload → hỏi."* Test Plan này áp dụng đúng nguyên tắc đó: một task P1 như T-109 (so khớp ảnh thiết kế chưa xong) **không chặn** Pilot Gate miễn G-01–G-07 đạt.

**Tiêu chí Pass/Fail cấp ca kiểm thử:**
- Ca **P0** (gắn với AC của story P0): phải **pass thật** trên hạ tầng mục tiêu (staging có Docker/IdP/LLM thật) trước khi gate liên quan được ký "Đạt".
- Ca **P1** (US-009, US-010, US-015, US-023): được phép còn "In progress" ở MVP-lite nếu không vi phạm nguyên tắc ở trên, nhưng phải ghi rõ trong hồ sơ G-01.
- Một ca integration/E2E **chỉ xác nhận "skip đúng cách"** (không lỗi cú pháp/fixture) **không được tính là "pass"** khi tổng hợp bằng chứng Pilot Gate — phải phân biệt rõ hai trạng thái này trong mọi báo cáo (nguyên tắc đã áp dụng xuyên suốt tài liệu task hiện tại, xem T-108/T-504).

---

## 8. Suspension and Resumption Criteria

### 8.1 Điều kiện tạm dừng (Suspension)

| Mã | Điều kiện | Hành động |
|---|---|---|
| SUS-01 | Build CI đỏ ở job `lint`/`typecheck`/`boundaries` (vi phạm ranh giới module ADR-01) | Dừng merge PR liên quan cho tới khi xanh lại |
| SUS-02 | Một ca integration test **pass trước đó** nay fail trên CI (regression RLS/cô lập dữ liệu) | Dừng toàn bộ kiểm thử ở cấp cao hơn (E2E/UAT) cho tới khi RLS được xác nhận lại — đây là lỗi ưu tiên cao nhất vì ảnh hưởng G-03 |
| SUS-03 | Canary string (test bảo mật) xuất hiện trong log/`analytics_event`/metric | Dừng ngay mọi hoạt động hướng tới G-04; không được tiếp tục UAT cho tới khi khắc phục và canary test lại sạch |
| SUS-04 | Môi trường staging không khởi động được (Postgres/Redis/TEI/ClamAV không healthy) | Dừng integration/E2E/performance test; tiếp tục unit test cục bộ |
| SUS-05 | D-01 (LLM) hoặc D-03 (IdP) chưa chốt tới hạn Sprint 3/Sprint 1 tương ứng | Theo R-01 (implement_plan §7): tiếp tục phát triển qua `LLMPort`/chuẩn OIDC với test double, nhưng **không được coi G-01/G-04 là Đạt** cho tới khi có adapter thật |

### 8.2 Điều kiện tiếp tục (Resumption)

- SUS-01/SUS-02: tiếp tục sau khi fix có PR review + CI xanh lại 1 lần liên tiếp.
- SUS-03: tiếp tục sau khi ATTT xác nhận bằng văn bản nguyên nhân rò rỉ đã được khắc phục và canary scan lại sạch 2 lần liên tiếp.
- SUS-04: tiếp tục sau khi `make smoke-infra` (hoặc tương đương staging) xác nhận 5 dịch vụ hạ tầng healthy.
- SUS-05: tiếp tục đánh giá gate liên quan ngay khi D-01/D-03 chốt và adapter thật được tích hợp + chạy lại toàn bộ test liên quan.

---

## 9. Test Deliverables

| Mã | Tài liệu/Artifact | Giai đoạn | Vị trí |
|---|---|---|---|
| TD-01 | Test Plan này | Trước Sprint 5 | `docs/testing/test_plan.md` |
| TD-02 | Báo cáo kết quả unit/integration test CI | Mỗi PR | GitHub Actions run log + badge |
| TD-03 | Báo cáo đánh giá chất lượng RAG | Trước G-02 | `tools/evaluation/reports/baseline.json` + `tuning_log.md` |
| TD-04 | Báo cáo hiệu năng k6 | Trước G-06 | Output `k6 run` (JSON/HTML), lưu kèm T-505 |
| TD-05 | Báo cáo canary bảo mật/quyền riêng tư | Trước G-04 | `tools/security/` output + biên bản ATTT |
| TD-06 | Báo cáo E2E Playwright | Trước G-01 | `frontend/reports/playwright/`, `reports/e2e.xml` |
| TD-07 | Biên bản UAT | Trước G-07 | `docs/pilot/UAT_MINUTES.md`, `UAT_FORM.md` |
| TD-08 | Nhật ký lỗi UAT + triage | T-602 | `docs/pilot/UAT_DEFECT_LOG.md`, `T602_TRIAGE.md` |
| TD-09 | Hồ sơ bằng chứng Pilot Gate (tổng hợp cuối) | T-603 | `docs/pilot/PILOT_GATE_EVIDENCE.md` |
| TD-10 | Runbook vận hành pilot | Trước mở pilot | `docs/pilot/RUNBOOK.md` |

---

## 10. Testing Tasks

Bảng dưới đây **tái sử dụng đúng 10 task** Sprint 5 + UAT đã có trong [implement_plan.md §5](../implement/implement_plan.md) và [danh mục task](../implement/tasks/README.md) — không tạo lịch kiểm thử song song.

| Task | Mô tả | Gate | Vai trò | Ước lượng | Trạng thái hiện tại |
|---|---|---|---|---|---|
| [T-501](../implement/tasks/T-501_rag-evaluation-harness.md) | Bộ đánh giá RAG offline: chạy bộ câu hỏi chuẩn, tính tỷ lệ đúng/`not_found` | G-02 | AI | 3d | In progress — đã sửa 2 lỗi thật (thiếu `X-CSRF-Token`, điều kiện CI sai dùng `changed_files` như danh sách); chưa chạy thật (thiếu LLM/TEI) |
| [T-502](../implement/tasks/T-502_quality-tuning-round1.md) | Hiệu chỉnh τ, kích thước đoạn, tham số rerank theo T-501 | G-02 | AI | 3d | To do — chờ số liệu T-501 |
| [T-503](../implement/tasks/T-503_security-privacy-hardening.md) | Hoá cứng bảo mật & quyền riêng tư, canary test | G-04 | TL | 2d | In progress — unit canary pass thật; canary E2E + SCA/scan image cần staging |
| [T-504](../implement/tasks/T-504_isolation-tests-and-e2e.md) | Kiểm thử cô lập dữ liệu + E2E Playwright luồng chính | G-01, G-03 | QA | 2d | In progress — 4 integration test viết đúng (chưa chạy thật), E2E chưa chạy |
| [T-505](../implement/tasks/T-505_performance-smoke-test.md) | Kiểm thử hiệu năng quy mô pilot (10 người dùng, k6) | G-06 | QA | 2d | To do — script sẵn sàng, chưa chạy |
| [T-506](../implement/tasks/T-506_quality-tuning-round2.md) | Hiệu chỉnh chất lượng vòng 2 (nếu T-502 chưa đạt) | G-02 | AI | 2d | To do — có điều kiện, chờ T-502 |
| [T-601](../implement/tasks/T-601_uat-execution.md) | Thực hiện UAT với nhóm người dùng thử nghiệm | G-07 | PM · BA | 1 tuần | To do — mẫu biên bản sẵn sàng, chưa chạy UAT thật |
| [T-602](../implement/tasks/T-602_uat-defect-fixing.md) | Khắc phục lỗi chặn phát hiện trong UAT | G-01–G-07 | Cả đội | Dự phòng | To do — quy trình triage sẵn sàng, chờ T-601 |
| [T-603](../implement/tasks/T-603_pilot-gate-evidence.md) | Tổng hợp bằng chứng và trình ký Pilot Gate | Tất cả | TL · QA | 2d | To do — khung 7 gate sẵn sàng, toàn bộ Pending |
| [T-604](../implement/tasks/T-604_pilot-runbook.md) | Runbook vận hành 2 tuần hỗ trợ sau mở pilot | — | OPS | 2d | In progress — nội dung thật, chưa diễn tập sự cố |

**Thứ tự thực hiện bắt buộc:** T-501 → T-502 → (T-506 nếu cần) song song với T-503/T-504/T-505 (độc lập nhau) → T-603 tổng hợp → T-601 UAT → T-602 khắc phục nếu có lỗi chặn → T-603 cập nhật lần cuối → ký Pilot Gate → T-604 vận hành pilot.

---

## 11. Environmental Needs

### 11.1 Khoảng trống môi trường thật đã gặp trong quá trình triển khai (ghi nhận trung thực)

Toàn bộ 47 task được triển khai và unit-test trong một môi trường **sandbox không có**: Docker Engine, một IdP/OIDC thật, một LLM/TEI thật, hay trình duyệt. Đây là nguyên nhân trực tiếp của phần lớn trạng thái "In progress"/"viết nhưng chưa chạy" ở Mục 4 và 6. Bảng dưới liệt kê từng khoảng trống và điều kiện cụ thể để đóng:

| Khoảng trống | Ảnh hưởng | Điều kiện để đóng |
|---|---|---|
| Không có Docker Engine | 13 integration test (RLS, upload đồng thời) chỉ xác nhận "skip đúng cách", không pass thật | Một máy/CI runner có Docker + quyền chạy Testcontainers (`docker.sock` hoặc Docker-in-Docker) |
| Không có IdP/OIDC thật (D-03 chưa chốt) | Luồng đăng nhập thật (US-001) và DevTools kiểm tra token không lộ ra JS chưa xác nhận được | Dựng Keycloak (khuyến nghị mặc định của implement_plan D-03) hoặc kết nối SSO nội bộ thật; đăng ký OIDC client; điền `OIDC_ISSUER`/`OIDC_CLIENT_ID`/`OIDC_CLIENT_SECRET` |
| Không có LLM/TEI thật (D-01 chưa chốt) | Chất lượng câu trả lời (G-02, KR2.1–2.3), đa ngôn ngữ nhánh `lingua` (US-017), AC-011.5 chưa đo được bằng số liệu thật | Một endpoint LLM OpenAI-compatible thật (phương án A mặc định, ADR-03) + dịch vụ TEI chạy `bge-m3`/`bge-reranker-v2-m3` (có sẵn trong `infra/docker-compose.yml`, chỉ cần Docker + ~6GB RAM rảnh) |
| Không có trình duyệt/Playwright browser | 2 kịch bản E2E (G-01) và so khớp ảnh thiết kế (29 màn hình) chưa chạy | `npx playwright install` trên một máy có trình duyệt; hoặc CI runner chuẩn (Ubuntu GitHub-hosted đã có sẵn) |
| Thiếu C++ Build Tools cho Python 3.15 | `lingua-language-detector` (phát hiện ngôn ngữ chính xác hơn, US-017) không cài được, build wheel cho `regex` lỗi | Chạy trên môi trường CI/staging dùng Python 3.12 (đúng `Dockerfile`, đã có wheel dựng sẵn) thay vì Python 3.15 cục bộ |
| Không có cụm staging | G-06 (hiệu năng), canary E2E (G-04), SCA/quét image (T-503) chưa chạy | Cụm staging theo T-004 (Kubernetes nội bộ hoặc tương đương, D-02) |
| Không có ATTT/QA Lead/PM tham gia trực tiếp | G-04 (xác nhận văn bản), G-02 (ký bởi BA Lead+PM), G-07 (UAT) không thể tự động hóa | Lịch rà soát với ATTT từ Sprint 1 (Giả định A-05, implement_plan §2.3) — nếu trễ, là rủi ro chặn ra mắt phút cuối |

### 11.2 Yêu cầu hạ tầng kiểm thử theo cấp độ

| Cấp độ | Hạ tầng tối thiểu |
|---|---|
| Unit | Python 3.12 + Node 20, không cần dịch vụ ngoài (toàn bộ dùng test double) |
| Integration | Docker Engine ≥ 20.10, ≥ 4GB RAM rảnh cho Testcontainers (Postgres+pgvector, Redis) |
| E2E | Node 20 + Playwright browsers (`npx playwright install --with-deps chromium`), FE+BE chạy cùng lúc (`npm run dev` + `uvicorn`) |
| Hiệu năng/Canary/SCA | Staging đầy đủ 5 dịch vụ hạ tầng (`make up` + `--profile app`), LLM/TEI thật, ≥ 6GB RAM rảnh (TEI + ClamAV nặng nhất) |
| UAT | Staging ổn định, tài khoản người dùng thử nghiệm thật đã được cấp quyền (T-103), ≥ 10–15 PDF không nhạy cảm (Giả định A-03) |

---

## 12. Responsibilities

Tái sử dụng đúng cột **Vai trò** đã dùng xuyên suốt `docs/implement/tasks/README.md` và đội ngũ ở `implement_plan.md §3.1`.

| Vai trò | Mã | Trách nhiệm kiểm thử |
|---|---|---|
| Tech Lead | TL | Kiến trúc test (ranh giới module, port/adapter test double), ký G-06, điều phối T-503 |
| Back-end Engineer | BE | Unit + integration test cho `identity`, `documents`, `ingestion`, `retention`, `core`; sửa lỗi phát hiện qua test |
| AI/ML Engineer | AI | Unit test `retrieval`/`qa`, chạy và hiệu chỉnh T-501/T-502/T-506 |
| Front-end Engineer | FE | Unit/component/axe-core test, phối hợp Playwright E2E |
| QA Engineer | QA | Chiến lược kiểm thử tổng thể (tài liệu này), integration/E2E/hiệu năng, ký G-01/G-03/G-05, chủ trì T-504/T-505 |
| DevOps | OPS | Môi trường staging/Testcontainers khả dụng, runbook (T-604) |
| PM · BA | PM · BA | Bộ câu hỏi chuẩn (G-02), chủ trì UAT (T-601), ký G-02 cùng BA Lead |
| An toàn thông tin | ATTT | Rà soát luồng dữ liệu AI, ký G-04, xác nhận văn bản AC-020.2, đồng ký G-03 |
| Chủ sở hữu nghiệp vụ | — | Ký G-07, quyết định mở/hoãn pilot (T-603) |

---

## 13. Staffing and Training Needs

| Nhu cầu | Mô tả | Mức độ cấp thiết |
|---|---|---|
| Vận hành Docker/Testcontainers | Đội BE/QA cần thành thạo chạy Testcontainers cục bộ để tự xác nhận integration test trước khi đẩy lên CI | Cao — là khoảng trống lớn nhất hiện tại |
| Vận hành Keycloak (nếu chọn D-03 phương án B) | Tech Lead/DevOps cần biết đăng ký OIDC client, cấu hình realm | Trung bình, phụ thuộc quyết định D-03 |
| Chạy và đọc kết quả k6 | QA cần biết diễn giải báo cáo p90/p95, phân biệt lỗi hạ tầng và lỗi hiệu năng thật | Trung bình |
| Vận hành Playwright CI | FE/QA cần biết debug trace/video khi E2E fail trên CI | Trung bình |
| Quy trình rà soát ATTT cho dữ liệu AI | ATTT cần hiểu kiến trúc port/adapter LLM và luồng dữ liệu để rà soát đúng trọng tâm G-04 | Cao — ảnh hưởng trực tiếp lịch Sprint 3–5 (R-01, implement_plan §7) |
| Không cần đào tạo thêm | pytest/vitest/axe-core đã được dùng nhất quán xuyên suốt 47 task, đội hiện tại đã thành thạo | — |

---

## 14. Schedule

Lịch kiểm thử bám theo cùng mốc của `implement_plan.md §4` — không tạo lịch song song lệch pha.

| Mốc | Hoạt động kiểm thử chính | Hoàn thành sau | Ngày dự kiến |
|---|---|---|---|
| M-0 | Unit test + CI xanh cho khung Sprint 0 | Sprint 0 | 2026-11-02 |
| M-1 | Unit test đăng nhập + upload 1 tệp; chuẩn bị Docker/Testcontainers | Sprint 1 | 2026-11-16 |
| M-2 | Integration test cô lập dữ liệu + upload đồng thời **chạy thật lần đầu** (cần Docker sẵn sàng) | Sprint 2 | 2026-11-30 |
| M-3 | Unit test hỏi đáp (Fake LLM); chuẩn bị LLM/TEI thật cho T-501 | Sprint 3 | 2026-12-14 |
| M-4 | Đủ unit/component test cho 19 story; chốt D-01/D-03 nếu chưa | Sprint 4 | 2026-12-28 |
| M-5 | **Chạy thật lần đầu:** T-501 (RAG eval), T-503 (canary E2E), T-504 (integration+E2E), T-505 (k6) | Sprint 5 | 2027-01-11 |
| M-6 | UAT (T-601), khắc phục (T-602), ký Pilot Gate (T-603), mở pilot | UAT 2 tuần | 2027-01-25 |

> **Lưu ý tiến độ thật:** tại thời điểm viết tài liệu này, Sprint 0–4 đã hoàn thành phần **code + unit test** (31/47 task Done), nhưng các hoạt động "chạy thật lần đầu" dự kiến ở M-2/M-5 **chưa xảy ra** vì môi trường phát triển không có Docker/LLM/trình duyệt. Lịch ở trên giữ nguyên làm mục tiêu; ngày thực tế phụ thuộc vào thời điểm đội có quyền truy cập Docker host + LLM/TEI thật + staging, không phải vào khối lượng code còn lại (khối lượng code cho Sprint 5 đã sẵn sàng, chỉ chờ chạy).

---

## 15. Risks and Contingencies

| Mã | Rủi ro | Khả năng | Ảnh hưởng | Mức độ | Giảm thiểu |
|---|---|---|---|---|---|
| RT-01 | Không có Docker trong môi trường dev khiến 13 integration test chưa từng pass thật — lỗi logic RLS/khóa hàng Postgres chỉ lộ ra khi chạy thật (ví dụ hành vi `SELECT...FOR UPDATE` dưới tải đồng thời) | Cao (đã xảy ra, đang diễn ra) | Cao — chặn trực tiếp G-01/G-03 | **Cao** | Ưu tiên chạy integration suite trên CI (đã có Testcontainers thật trong `backend-test` job) ngay khi PR được mở, thay vì chỉ tin vào việc test "skip đúng cách" cục bộ |
| RT-02 | `lingua-language-detector` không cài được trên Python 3.15 (thiếu Microsoft Visual C++ 14.0 Build Tools) — mọi lần chạy chỉ thực thi nhánh heuristic dự phòng, chưa từng thực thi nhánh chính | Cao (đã xảy ra) | Trung bình — US-017/AC-017.1–.2 có thể sai nếu heuristic kém hơn `lingua` trên câu ngắn/trộn ngôn ngữ | Trung bình | Chạy lại `test_qa_language_detection.py` trên CI/staging dùng Python 3.12 (có wheel dựng sẵn) trước khi tính G-02 cho US-017; không coi kết quả heuristic là đại diện cho hành vi production |
| RT-03 | D-03 (IdP) chưa chốt — không có IdP thật để kiểm tra luồng OIDC đầu-cuối qua trình duyệt và xác nhận không có token lộ ra JavaScript | Trung bình (phụ thuộc quyết định ngoài đội kỹ thuật) | Cao — chặn hoàn toàn test E2E đăng nhập, ảnh hưởng G-01 | **Cao** | Theo R-01/implement_plan §7: dựng Keycloak làm phương án dự phòng song song (hướng mặc định D-03); không chờ SSO nội bộ nếu trễ |
| RT-04 | Canary end-to-end thật (G-04) chưa từng chạy — chỉ có bằng chứng ở mức unit (log formatter, allow-list analytics); rủi ro rò rỉ nội dung có thể tồn tại ở một đường dẫn chưa được unit test bao phủ (ví dụ log của thư viện bên thứ ba, OTel exporter cấu hình sai ở staging) | Trung bình | Cao — vi phạm G-04 là vấn đề tuân thủ/quyền riêng tư, có thể chặn ra mắt hoàn toàn (PRD §2.1 "Bên ràng buộc") | **Cao** | Chạy canary E2E thật ngay khi có staging, trước khi UAT; không cho phép T-603 kết luận G-04 "Đạt" chỉ dựa trên unit test |
| RT-05 | Playwright E2E và so khớp ảnh thiết kế (29 màn hình) chưa từng chạy — lỗi tương tác thật giữa các component (ví dụ race condition SSE + React state) có thể không lộ ra ở test component đơn lẻ | Trung bình | Trung bình | Trung bình | Ưu tiên chạy Playwright trên CI (chỉ cần cài browser, không cần hạ tầng nặng) sớm nhất có thể, song song với chờ staging cho các gate khác |
| RT-06 | Bộ câu hỏi chuẩn (≥10 câu không đáp án, PDF không nhạy cảm) đến muộn (R-07, implement_plan §7) | Trung bình | Cao — không đo được G-02 đúng hạn | Trung bình | PM/BA theo dõi từ Sprint 2 như implement_plan đã khuyến nghị; nếu trễ, dời T-501/T-502 và rút ngắn Sprint 4 |
| RT-07 | Ngưỡng τ=0,15 (cổng bằng chứng) và kích thước đoạn ~500 token là giá trị đề xuất chưa hiệu chỉnh trên dữ liệu thật (CL-03, implement_plan §9) — có thể gây `not_found` sai hoặc "bịa" khi chạy T-501 lần đầu | Trung bình | Cao — ảnh hưởng trực tiếp KR2.1/KR2.2 | Trung bình | Coi τ là tham số cấu hình (không hard-code), hiệu chỉnh ở T-502/T-506 dựa trên đường cong thật từ T-501 |
| RT-08 | Chi phí/giới hạn tốc độ của LLM thật khi chạy T-501 lần đầu với bộ câu hỏi chuẩn lớn | Thấp–Trung bình | Trung bình | Thấp | Rate limit sẵn có (10 câu/phút/người theo SADD §2.4.1); chạy `run_eval.py` theo lô nhỏ, theo dõi chi phí trước khi chạy toàn bộ bộ chuẩn |

---

## 16. Approvals

| Vai trò | Tên | Chữ ký | Ngày |
|---|---|---|---|
| QA Lead | [TBD] | | |
| Tech Lead | [TBD] | | |
| Product Manager / Business Analyst Lead | [TBD] | | |
| An toàn thông tin (ATTT) | [TBD] | | |
| Chủ sở hữu nghiệp vụ / Nhà tài trợ | [TBD] | | |

> Tài liệu này được phê duyệt theo cùng cơ chế với [`PILOT_GATE_EVIDENCE.md`](../pilot/PILOT_GATE_EVIDENCE.md): mỗi vai trò ký sau khi bằng chứng tương ứng ở Mục 7 (Item Pass/Fail Criteria) đã có kết quả **chạy thật**, không chỉ dựa trên kế hoạch hoặc code đã viết.

---

## Phụ lục A. Tình trạng 47 task tại thời điểm viết Test Plan

Xem đầy đủ tại [`docs/implement/tasks/README.md`](../implement/tasks/README.md) — đây là bảng tóm tắt theo nhóm:

| Nhóm trạng thái | Số task | Ghi chú |
|---|---|---|
| **Done** | 31/47 | Phần lớn kèm chú thích "chưa đo/chạy trên hạ tầng thật" (Postgres/LLM/TEI/staging/GitHub Actions) — xem từng dòng trong README để biết chính xác phần nào còn thiếu |
| **In progress** | 10/47 | T-107, T-108, T-109, T-403, T-404, T-405, T-501, T-503, T-504, T-604 — mọi khoảng trống còn lại đều bị chặn bởi hạ tầng (Docker/LLM/trình duyệt/staging) hoặc quy trình con người (ATTT/QA Lead/PM), không còn khoảng trống code/thiết kế đã biết |
| **To do** | 6/47 | T-502, T-506 (chờ T-501 có số liệu), T-505 (chờ staging), T-601/T-602 (chờ UAT thật), T-603 (chờ kết quả mọi gate con) |

## Phụ lục B. Thuật ngữ

| Thuật ngữ | Ý nghĩa |
|---|---|
| Pass thật | Test đã **chạy** (không chỉ thu thập/skip đúng cú pháp) và xanh trên hạ tầng mục tiêu tương ứng |
| Skip đúng cách | Test tự nhận diện thiếu hạ tầng (ví dụ không có Docker) và gọi `pytest.skip()` một cách có chủ đích, không phải lỗi — nhưng **không chứng minh logic đúng** |
| Testcontainers | Thư viện khởi tạo container thật (Postgres+pgvector, Redis) cho vòng đời một test session, dùng trong `backend/tests/integration/` |
| Canary test | Kỹ thuật chèn một chuỗi nhận diện duy nhất vào dữ liệu đầu vào rồi khẳng định chuỗi đó **không** xuất hiện ở đầu ra (log/metric/analytics) — dùng để chứng minh P-03 (không rò rỉ nội dung) |
| G-01 … G-07 | 7 Pilot Gate theo PRD §5.1, thay thế "Launch Gate production" cho MVP-lite |
