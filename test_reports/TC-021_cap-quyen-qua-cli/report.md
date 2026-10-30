# Báo cáo thực thi — TC-021 Cấp quyền qua CLI phản ánh đúng khi đăng nhập

| Trường | Giá trị |
|---|---|
| Thời gian chạy | 2026-10-30T00:20:00+07:00 |
| URL đã test | `http://localhost:5173` |
| Môi trường | Như TC-001 (mock IdP đổi email sang `cli-test@example.com` cho ca này) |
| Kết luận chung | **PASS** |

## Kết quả theo từng tiêu chí

| # | Kết quả mong đợi | Quan sát thực tế | PASS/FAIL | Bằng chứng |
|---|---|---|---|---|
| KQ1 | Trước `grant-access`, đăng nhập chỉ dẫn tới "Không có quyền" | `list-users --active-only` xác nhận `cli-test@example.com` chưa tồn tại; đăng nhập qua IdP → "Chưa được cấp quyền" | **PASS** | [01_truoc_khi_cap_quyen.png](./01_truoc_khi_cap_quyen.png), `TC-021_cap-quyen-qua-cli_before.txt` |
| KQ2 | Ngay sau `grant-access`, đăng nhập lại (phiên mới) vào được thư viện | `python -m app.cli grant-access --email cli-test@example.com --role user` → "Đã cấp quyền cli-test@example.com (role=user)"; đăng nhập lại (phiên mới, cookie đã xóa) → vào đúng "SCR-02 Thư viện tài liệu", tên "cli-test" ở góc phải | **PASS** | [02_sau_khi_cap_quyen.png](./02_sau_khi_cap_quyen.png), `grant_output.txt` |
| KQ3 | Ngay sau `revoke-access`, đăng nhập lại đưa về "Không có quyền" — có hiệu lực ngay | `python -m app.cli revoke-access --email cli-test@example.com --yes` → "Đã thu hồi quyền cli-test@example.com"; đăng nhập lại ngay (không có độ trễ nào) → quay lại đúng "Chưa được cấp quyền" | **PASS** | [03_sau_khi_thu_hoi_quyen.png](./03_sau_khi_thu_hoi_quyen.png), `revoke_output.txt` |

## Ghi chú

Xác nhận thêm (đọc code trong lúc chạy): `get_current_user()` (`app/api/deps.py`) tra lại `user.active` từ Postgres **trên mỗi request**, không cache trong session Redis — nghĩa là việc thu hồi quyền có hiệu lực ngay cả với một phiên đang hoạt động (không cần đợi phiên hết hạn hay đăng xuất thủ công), đúng tinh thần AC-023.2 "có hiệu lực ngay". Ca test này chỉ xác nhận qua đăng nhập lại (đúng kịch bản mô tả), chưa thử giữ nguyên một tab đang mở rồi revoke giữa chừng để quan sát request tiếp theo trong CÙNG phiên bị chặn ra sao — có thể bổ sung nếu cần bằng chứng chặt hơn.
