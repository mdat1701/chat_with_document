// Cấu hình khung (T-001). Quy tắc ranh giới đầy đủ DR-01 – DR-06
// (SDD §3.3) được thêm ở T-106 bằng `eslint-plugin-boundaries`.
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";

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
    ignores: ["dist/**", "node_modules/**"],
  },
);
