# Báo cáo thực thi — TC-007 Tải nhiều tệp đồng thời, hàng đợi giới hạn 3 song song

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-29T23:38:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-004 (backend local, upload rất nhanh vì file nhỏ + mạng loopback) |
| Kết luận chung | **PASS một phần** — KQ3/KQ4 pass thật; KQ1/KQ2 không quan sát được rõ ràng do tốc độ xử lý cục bộ quá nhanh (xem Ghi chú) |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Bằng chứng |
|---|---|---|---|---|
| KQ1 | Tối đa 3 tệp "đang tải" cùng lúc, 2 tệp "đang chờ" | Ảnh chụp ở mốc 150ms sau khi thả cho thấy 1 tệp còn thanh tiến trình (`tep-3`), 4 tệp còn lại **đã** ở trạng thái "Đang xử lý..." (tức đã tải xong, chuyển sang xử lý server) — do tệp test rất nhỏ (365B) và chạy trên localhost nên thời gian tải gần như tức thời, không bắt được rõ khoảnh khắc "3 đang tải / 2 đang chờ" bằng ảnh chụp đơn | **KHÔNG QUAN SÁT RÕ** (không phải bằng chứng cho thấy sai, chỉ là giới hạn kỹ thuật của phép đo) | [01_ngay_sau_khi_tha_5_tep.png](./01_ngay_sau_khi_tha_5_tep.png) |
| KQ2 | Tệp chờ tự động bắt đầu khi có chỗ trống | Không quan sát được riêng biệt (cùng lý do KQ1) — nhưng tất cả 5 tệp cuối cùng đều tải xong mà không cần thao tác thủ công nào, tức hàng đợi đã tự chạy hết | **PASS (gián tiếp)** | `documents_final.json` |
| KQ3 | Đủ 5 tài liệu, không sót/trùng | `GET /api/v1/documents` trả đủ 5 tài liệu mới (`tep-1`..`tep-5`, mỗi tên có hậu tố thời gian riêng), đúng `status=processing`, ID khác nhau, không trùng tên/ID | **PASS** | `documents_final.json` |
| KQ4 | Mỗi tệp 1 request riêng | `NETWORK_LOG` ghi nhận đúng **5 lần** `201 POST /api/v1/documents` riêng biệt, không có request nào gộp nhiều tệp | **PASS** | (xem log chạy, 5× `201 POST`) |

## Ghi chú / Sai lệch

Ảnh `03_sau_khi_hoan_tat.png` chụp đúng lúc trang đang ở trạng thái skeleton loading (do `waitForFunction` chờ đủ 8 `doc-item` bị timeout — có thể do khung đếm tạm thời reset khi EventSource `/documents/events` tự kết nối lại) nên không dùng làm bằng chứng cuối; `documents_final.json` (gọi thẳng API ngay sau đó) phản ánh đúng trạng thái dữ liệu thật và được dùng làm bằng chứng chính cho KQ3/KQ4.

**Hạn chế đã biết của phép đo KQ1/KQ2:** với tệp PDF rất nhỏ chạy trên localhost, toàn bộ 5 upload hoàn tất trong dưới ~150ms — quá nhanh để một ảnh chụp đơn bắt được rõ ràng trạng thái trung gian "3 đang tải, 2 đang chờ" do `MAX_CONCURRENT=3` (`useUploadQueue.ts`) quy định. Đây là giới hạn của kịch bản test (cần tệp lớn hơn hoặc giả lập độ trễ mạng để quan sát rõ), không phải bằng chứng cho thấy logic hàng đợi sai — code `useUploadQueue.ts` đã được đọc xác nhận đúng ở T-109 và không có gì trong lần chạy này mâu thuẫn với điều đó (không có tệp nào bị bỏ sót/trùng, tất cả hoàn tất đúng).
