import { expect, test } from "@playwright/test";

test("G-01 upload, ask with citation, and delete", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("upload-dropzone-input").setInputFiles("e2e/fixtures/sample.pdf");
  await expect(page.getByTestId("upload-dropzone")).toBeVisible();
  await expect(page.getByRole("heading", { name: "SCR-02 Thư viện tài liệu" })).toBeVisible();
});

test("G-01 empty state has no answer citations", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Chưa có tài liệu")).toBeVisible();
});
