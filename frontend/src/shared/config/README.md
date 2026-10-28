# shared/config

`useAppConfig()` nạp `GET /config` một lần khi khởi động qua
`AppConfigProvider` (lắp trong `app/App.tsx`). Nếu gọi lỗi, dùng
`DEFAULT_APP_CONFIG` (20 MB / 50 tài liệu / 2.000 ký tự) và đặt
`usedFallback = true` — không chặn đăng nhập (SDD §3.4.4, nguyên tắc P-06).
