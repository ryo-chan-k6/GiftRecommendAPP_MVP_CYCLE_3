# Experiment: Playwright D2 scaffold + S1 smoke

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-17 |
| Epic | #1438 |
| Task | #1439 |
| 目的 | Playwright 導入と D1 S1 相当 smoke の追加 |

## 実施内容

1. `@playwright/test` を `apps/web` に追加
2. `playwright.config.ts` / `e2e/00-playwright-smoke.spec.ts` / `e2e/s1-recommendation-happy-path.spec.ts` を追加
3. scripts: `test:e2e` / `test:e2e:install`
4. ローカル開発手順書 §10.4.17 / チェックリスト Residual を更新

## 結果（事実）

| 項目 | 値 |
| ---- | ---- |
| Docker | **未起動** |
| api / web / reco | **未起動** |
| Chromium zip | `/tmp/playwright-download-chromium-…1169.zip` 取得済み（`playwright install` は extract でハング） |
| 手動 unzip | Python `zipfile` で `~/.cache/ms-playwright/chromium-1169` に展開 |
| システム依存 | `libnss3.so` / `libnspr4.so` / `libasound.so.2` 等が **not found**。`sudo apt` はパスワード不可のため未インストール |
| `00-playwright-smoke` | **未実行成功**（上記依存不足で browser launch 不可） |
| S1 happy path | API health 未達時は **skip** 設計。本環境ではフルパス未実行 |

## 未達理由（事実）

本エージェント実行環境では (1) Docker 未起動 (2) Playwright Chromium の OS ライブラリ不足 により、E2E 実行まで到達できなかった。コード・手順・skip 設計は投入済み。

## 推奨再実行（ローカル）

```bash
# OS deps（要権限）
pnpm --filter @gift-recommendation/web exec playwright install-deps chromium
# または distro 向け: sudo apt install libnss3 libnspr4 libasound2t64 …

pnpm --filter @gift-recommendation/web test:e2e:install
# Docker / supabase / redis / api / reco / web / seed 起動後:
pnpm --filter @gift-recommendation/web test:e2e
```

## 次（推論）

- Human 環境で上記再実行し S1 pass を実験ログへ追記する
- GHA Playwright 必須ゲートは後続 Epic
