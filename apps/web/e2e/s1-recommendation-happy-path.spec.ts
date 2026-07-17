import { test, expect } from "@playwright/test";

/**
 * D1 S1 相当: SCR-002 → 実行中 → SCR-004（結果あり）。
 * SCR-001 起点は D1 でも不安定だったため /recommendations から開始する。
 *
 * 前提: web / api / reco / DB / Redis / seed 済み（ローカル開発手順書）。
 * 未起動時は skip（実装欠落ではなく環境前提）。
 */

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:3001";

async function isStackReady(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, {
      signal: AbortSignal.timeout(2000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

test.describe("D2 S1 recommendation happy path", () => {
  test.beforeEach(async () => {
    test.skip(
      !(await isStackReady()),
      `API health 未達（${API_BASE}）。web/api/reco/DB を起動してから再実行してください。`,
    );
  });

  test("S1: /recommendations → run → result list has items", async ({
    page,
  }) => {
    await page.goto("/recommendations");

    await expect(
      page.getByRole("heading", { name: "レコメンド条件入力" }),
    ).toBeVisible();

    await page.getByLabel("贈る相手").selectOption({ label: "上司" });
    await page.getByLabel("用途").selectOption({ label: "お礼" });
    await page.getByLabel(/予算下限/).fill("3000");
    await page.getByLabel(/予算上限/).fill("5000");
    await page.getByLabel("好み").fill("上品で、感謝が伝わるもの");
    await page.getByLabel("避けたい条件").fill("カジュアルすぎるものは避けたい");
    await page.getByLabel("NG条件").fill("アルコールはNG");

    await page.getByRole("button", { name: "レコメンドを実行" }).click();

    await expect(page).toHaveURL(/\/recommendations\/[0-9a-f-]+/i, {
      timeout: 120_000,
    });

    await expect(
      page.getByRole("heading", { name: "おすすめのギフト" }),
    ).toBeVisible();

    // 結果カードが1件以上（商品名テキストが存在）
    const cards = page.locator("article, [class*='Card'], li").filter({
      hasText: /¥|円/,
    });
    await expect(cards.first()).toBeVisible({ timeout: 15_000 });
  });
});
