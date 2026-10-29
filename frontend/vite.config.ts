/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// SDD §1.3: SPA tệp tĩnh, JS ban đầu mục tiêu ≤250KB gzip.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@app": fileURLToPath(new URL("./src/app", import.meta.url)),
      "@features": fileURLToPath(new URL("./src/features", import.meta.url)),
      "@shared": fileURLToPath(new URL("./src/shared", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Back-end API cục bộ (T-002 docker-compose expose cổng 8000).
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      // Luồng đăng nhập OIDC (T-101) nằm ngoài tiền tố /api/v1 — thiếu
      // dòng này khiến `/auth/login`/`/auth/callback` bị Vite trả về
      // `index.html` (SPA fallback) thay vì tới backend thật, khiến đăng
      // nhập không thể chạy được trong dev local (phát hiện khi chạy
      // TC-001 thủ công). `changeOrigin: false` (khác `/api`): backend
      // tính `redirect_uri` OIDC bằng `request.url_for()`, dựa vào header
      // `Host` nó thấy được — giữ nguyên Host gốc (`localhost:5173`) để
      // trình duyệt quay lại đúng origin frontend sau khi IdP chuyển
      // hướng về, thay vì kẹt ở origin riêng của backend (cổng 8000, nơi
      // SPA không được phục vụ). Trong staging/production, FE và BE nằm
      // chung một host qua Ingress nên vấn đề này không tồn tại.
      "/auth": { target: "http://localhost:8000", changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
    // e2e/ chứa kịch bản Playwright (T-504), chạy bằng `playwright test`,
    // không phải vitest — loại trừ để tránh xung đột runner.
    exclude: ["e2e/**", "node_modules/**"],
  },
});
