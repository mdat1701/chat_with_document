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
