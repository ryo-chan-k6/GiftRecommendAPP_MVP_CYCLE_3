# Experiment: Playwright D2 scaffold + S1 smoke

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-17 |
| Epic | #1438 |
| Task | #1439 |
| follow-up | #1457（Docker 起動後の S1 実測証跡を反映） |
| 目的 | Playwright 導入と D1 S1 相当 smoke の追加 |

## 実施内容

1. `@playwright/test` を `apps/web` に追加
2. `playwright.config.ts` / `e2e/00-playwright-smoke.spec.ts` / `e2e/s1-recommendation-happy-path.spec.ts` を追加
3. scripts: `test:e2e` / `test:e2e:install`
4. ローカル開発手順書 §10.4.17 / チェックリスト Residual を更新

## 結果（事実）

### 初回（Docker 未起動時点）

| 項目 | 値 |
| ---- | ---- |
| Docker | **未起動** |
| api / web / reco | **未起動** |
| Chromium zip | `/tmp/playwright-download-chromium-…1169.zip` 取得済み（`playwright install` は extract でハング） |
| 手動 unzip | Python `zipfile` で `~/.cache/ms-playwright/chromium-1169` に展開 |
| システム依存 | `libnss3.so` / `libnspr4.so` / `libasound.so.2` 等が **not found**。`sudo apt` はパスワード不可のため未インストール |
| `00-playwright-smoke` | **未実行成功**（上記依存不足で browser launch 不可） |
| S1 happy path | API health 未達時は **skip** 設計。本環境ではフルパス未実行 |

### 追記（2026-07-18 / Docker Desktop 起動後）

| 項目 | 値 |
| ---- | ---- |
| Docker | **起動済み**（supabase_* / redis healthy） |
| Redis | `PONG` |
| api health | `200` (`http://localhost:3001/api/v1/health`) |
| reco | `uvicorn` `:8000` 起動確認（`/docs` 200） |
| web | `next dev` `:3000`、SSR HTML に「レコメンド条件入力」あり |
| API S1 | `POST /api/v1/recommendations` → `resultStatus=completed`, `resultItemCount=1` |
| UI S1 | Playwright `chromium.launch`（`executablePath` = 手動展開 Chromium + `LD_LIBRARY_PATH=/tmp/pw-libs/...`）で **PASS** |
| UI S1 詳細 | `/recommendations` → 上司/お礼/3000–5000 → 実行 → `/recommendations/e3aaa2a3-…`、「おすすめのギフト」、価格カード visible |
| `playwright test` CLI | 本 WSL 環境では `--list` 含め **起動直後に無出力ハング**（`timeout` で 124）。プログラム起動の S1 は成功 |

OS ライブラリ不足の回避: deb から `libnss3` / `libnspr4` / `libasound` を `/tmp/pw-libs/root/...` に展開し `LD_LIBRARY_PATH` で参照。

## 推奨再実行（ローカル）

```bash
# OS deps（要権限・推奨）
pnpm --filter @gift-recommendation/web exec playwright install-deps chromium
pnpm --filter @gift-recommendation/web test:e2e:install

# WSL で headless_shell 欠落時の例
export LD_LIBRARY_PATH=/tmp/pw-libs/root/usr/lib/x86_64-linux-gnu
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=$HOME/.cache/ms-playwright/chromium-1169/chrome-linux/chrome

# Docker / supabase / redis / api / reco / web / seed 起動後:
pnpm --filter @gift-recommendation/web test:e2e
```

## 次（推論）

- Human 環境で `playwright install-deps` + 公式 `test:e2e` を再確認し、CLI ハングが環境固有か切り分ける
- GHA Playwright 必須ゲートは後続 Epic
