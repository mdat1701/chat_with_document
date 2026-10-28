// Cấu hình khung (T-001). Quy tắc ranh giới DR-01 – DR-06 (SDD §3.3)
// được thêm ở T-106 bằng `eslint-plugin-boundaries`.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import boundaries from "eslint-plugin-boundaries";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
    },
  },
  {
    files: ["src/**/*.{ts,tsx}"],
    plugins: { boundaries },
    settings: {
      "boundaries/root-path": "src",
      "import/resolver": {
        typescript: { project: "./tsconfig.json" },
      },
      "boundaries/elements": [
        { type: "shared-ui", pattern: "shared/ui/**", mode: "folder" },
        { type: "shared-api", pattern: "shared/api/**", mode: "folder" },
        { type: "shared-analytics", pattern: "shared/analytics/**", mode: "folder" },
        { type: "shared-other", pattern: "shared/**", mode: "folder" },
        { type: "features", pattern: "features/*", mode: "folder", capture: ["feature"] },
        { type: "app", pattern: "app/**", mode: "folder" },
      ],
    },
    rules: {
      // DR-02: shared/* không được import features/*.
      "boundaries/element-types": [
        "error",
        {
          default: "allow",
          rules: [
            { from: ["shared-ui", "shared-api", "shared-analytics", "shared-other"], disallow: ["features"] },
            // shared/ui phải thuần hiển thị — không gọi shared/api hay shared/analytics.
            { from: ["shared-ui"], disallow: ["shared-api", "shared-analytics"] },
          ],
        },
      ],
    },
  },
  {
    // DR-04: chỉ shared/api (và shared/analytics, nơi có "best-effort beacon"
    // riêng cho đo lường) được gọi `fetch`/`EventSource` trực tiếp. Mọi nơi
    // khác phải dùng `apiFetch`/`uploadFile` từ shared/api hoặc `track()` từ
    // shared/analytics — không tự dựng lại hàng đợi sự kiện/gọi mạng riêng.
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/shared/api/**", "src/shared/analytics/**", "src/**/*.test.{ts,tsx}", "src/test-setup.ts"],
    rules: {
      "no-restricted-globals": [
        "error",
        { name: "fetch", message: "Chỉ shared/api hoặc shared/analytics được gọi fetch trực tiếp (DR-04)." },
        { name: "EventSource", message: "Chỉ shared/api được dùng EventSource trực tiếp (DR-04)." },
      ],
    },
  },
  {
    ignores: ["dist/**", "node_modules/**"],
  },
);
