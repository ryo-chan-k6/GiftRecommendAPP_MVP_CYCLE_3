import { test, expect } from "@playwright/test";

/** Playwright 自体の起動確認（外部スタック不要）。 */
test("playwright chromium launches", async ({ page }) => {
  await page.goto("about:blank");
  expect(page.url()).toBe("about:blank");
});
