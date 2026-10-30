# Báo cáo thực thi — TC-020 Không lộ nội dung nhạy cảm qua Network/sự kiện phân tích

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:10:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-013, sau khi sửa 2 lỗi thật phát hiện ngay trong lúc chạy ca này (xem Ghi chú) |
| Kết luận chung | **PASS** |

## Phương pháp

Thay vì mở DevTools thủ công, gắn listener `page.on("requestfinished")` của Playwright để ghi lại **toàn bộ** 154 request/response (kể cả body) trong suốt luồng: đăng nhập → tải tài liệu tên nhạy cảm `bao-cao-mat-2026.pdf` (nội dung chứa chuỗi canary `ZZCANARY7781`) → đặt câu hỏi chứa chuỗi canary `ZZQUESTION9912` → xóa tài liệu. Sau đó quét toàn bộ payload đã ghi tìm 3 chuỗi canary, loại trừ chính request hỏi-đáp (nơi câu hỏi tất nhiên xuất hiện, đúng như test case cho phép).

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL |
|---|---|---|---|
| KQ1 | Không request/response nào chứa `ZZCANARY7781` | Quét 154 request: **0 lần xuất hiện** | **PASS** |
| KQ2 | Không request/response nào (ngoài chính request hỏi-đáp) chứa `ZZQUESTION9912` | **0 lần xuất hiện** ở các request khác; đúng như dự kiến, chuỗi này chỉ có trong `reqBody` của `POST /conversations/.../questions` (đã loại trừ theo quy định của ca) | **PASS** |
| KQ3 | Không request sự kiện phân tích nào chứa tên tệp đầy đủ `bao-cao-mat-2026.pdf` | `POST /api/v1/events` (duy nhất 1 request, xem bên dưới) không chứa tên tệp này. Có 1 kết quả khớp ở `POST /api/v1/documents` (API upload chính nó — **không phải kênh phân tích**, cần tên tệp để lưu trữ, đúng chức năng, không phải sai lệch) | **PASS** (loại trừ false-positive đã giải thích) |
| KQ4 | `/events` chỉ chứa khóa `props` thuộc allow-list | `eventsRequestBodies` ghi lại đúng 1 request `POST /api/v1/events` với 5 sự kiện: `session_started{is_first_session}`, `empty_state_viewed{state_code}`, `document_upload_started{file_size_bucket}`, `question_submitted{question_length, language, ready_doc_count}`, `answer_failed{error_code}` — **không có khóa nào ngoài allow-list đã khai báo ở T-404**, không có `file_name`/`content`/`question`/`answer` | **PASS** |

## 2 lỗi THẬT phát hiện và đã sửa ngay trong lúc chạy ca này

Lần chạy đầu tiên của ca này cho kết quả `eventsRequestsCount: 0` — **không một sự kiện phân tích nào** tới được `/api/v1/events` dù thao tác đã tạo ra ít nhất 5 sự kiện hợp lệ. Chẩn đoán ra 2 lỗi thật độc lập, cả hai đều **chưa từng bị phát hiện** vì chưa có test nào (kể cả test đơn vị) từng chạy hết đường đi thật của việc gửi sự kiện phân tích:

1. **`frontend/src/shared/analytics/client.ts`**: chỉ đẩy lô (`flush()`) khi đủ **20** sự kiện hoặc khi trang bị đóng (`pagehide`) — **thiếu hoàn toàn nhánh đẩy theo thời gian** mà chính T-404 §5 bước 5 đã quy định ("gom lô theo thời gian (ví dụ 5 giây) HOẶC khi đủ 20 sự kiện"). Hậu quả thật: một phiên dùng bình thường (vài thao tác) gần như không bao giờ đạt 20 sự kiện, và nếu người dùng không đóng tab theo cách kích hoạt `pagehide` (ví dụ chuyển app trên di động), **toàn bộ dữ liệu phễu kích hoạt/MET-003 không bao giờ được ghi nhận**. Đã sửa: thêm `setInterval(() => void flush(), 5000)`. Thêm 3 unit test (`client.test.ts`, trước đây **0 test** cho module này).
2. **`backend/app/api/main.py::csrf_protection`**: sau khi sửa (1), request đầu tiên thật sự được gửi đi nhưng bị middleware CSRF chặn `403 CSRF_INVALID` — vì `navigator.sendBeacon()` (dùng cho nhánh `pagehide`, không liên quan gì tới lỗi này nhưng cùng hàm `flush()`) và ngay cả `fetch()` thường trong `client.ts` đều **không bao giờ gắn `X-CSRF-Token`**. Gắn header cho `fetch()` thì được, nhưng `sendBeacon()` **không thể gắn header tùy ý theo đặc tả API trình duyệt** — nghĩa là nhánh "không mất sự kiện cuối khi rời trang" (chính mục tiêu thiết kế của T-404 §5 bước 5) **không bao giờ có thể hoạt động được** nếu vẫn yêu cầu CSRF. Đã sửa: miễn CSRF riêng cho `/api/v1/events` (vẫn giữ nguyên yêu cầu session hợp lệ qua `get_current_user` — không mở ra ghi dữ liệu ẩn danh). Đánh đổi chấp nhận được: giả mạo request này chỉ khiến chính trình duyệt nạn nhân tự gửi sự kiện phân tích giả cho tài khoản của họ, không đọc/sửa được tài nguyên nào khác. Thêm 1 test xác nhận `/api/v1/events` không bị chặn bởi CSRF trong khi `/api/v1/conversations` vẫn bị chặn như cũ.

Xác nhận: backend `ruff/mypy/pytest` (180 passed, 13 skipped, +2 từ 2 test mới); frontend `tsc/eslint/prettier/build/vitest` (111 passed, +3 từ test mới).

## Ghi chú

Đây là lần đầu tiên US-020/AC-020.1 (P-03 "nội dung không bao giờ lọt ra ngoài") được xác nhận bằng cách **thật sự chặn và đọc payload mạng** của toàn bộ luồng tải lên → hỏi đáp → xóa, thay vì chỉ test đơn vị allow-list riêng lẻ. Kết quả xác nhận allow-list hoạt động đúng trong điều kiện thật, nhưng quá trình chạy ca này cũng vô tình lộ ra đây là **lần đầu tiên dữ liệu phân tích thật sự rời được trình duyệt** trong toàn bộ dự án — minh chứng rõ giá trị của việc kiểm thử đầu-cuối so với test đơn vị đơn thuần.
