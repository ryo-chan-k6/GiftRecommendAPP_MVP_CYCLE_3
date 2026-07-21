import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E（並列計画 D2）。
 * 既定 baseURL は http://localhost:3000。上書きは WEB_BASE_URL。
 * 実 API 連携の S1 は api/reco/DB 起動が前提（ローカル開発手順書 §9〜§10）。
 */
const baseURL = process.env.WEB_BASE_URL ?? "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  timeout: 120_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
    launchOptions: {
      // WSL / 欠落 shared library 環境向け。必要時のみ executablePath を上書き。
      args: ["--no-sandbox", "--disable-gpu"],
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
        ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH }
        : {}),
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
