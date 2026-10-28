import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  reporter: [["html", { outputFolder: "reports/playwright" }], ["junit", { outputFile: "reports/e2e.xml" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  webServer: process.env.E2E_BASE_URL ? undefined : {
    command: "npm run dev -- --host 0.0.0.0",
    port: 5173,
    reuseExistingServer: !process.env.CI,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
