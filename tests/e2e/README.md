# tests/e2e/

システムテスト（Epic C C3 `test-system.yml`）向け E2E テスト配置先。

C3 Task では workflow 骨格と主要 API 導線テストを追加する。C2 では fixture 正本のみ整備し、実行コードは C3 scope とする。

## 実行

| 実行環境 | 手順 |
| -------- | ---- |
| GHA Layer2 | Actions → **Test System (Layer2)** → `workflow_dispatch` |
| ローカル（DB 起動済み） | `DATABASE_URL=... REDIS_URL=... bash tests/e2e/run-system-tests.sh` |

### workflow_dispatch 入力

| 入力 | 既定 | 説明 |
| ---- | ---- | ---- |
| `skip_api_e2e` | `true` | Phase4b 以前は API health / RecommendationRun を skip |
| `api_base_url` | 空（localhost:3001） | 将来 cloud dev 用 |
| `reco_base_url` | 空（localhost:8000） | 将来 cloud dev 用 |

## レポート

実行後、`tests/e2e/results/` に以下を出力する（GHA では artifact として保存）。

- `system-test-report.json` — Agent 読取用
- `system-test-report.md` — Human 確認用

## C3 からの参照

| 参照先 | 用途 |
| ------ | ---- |
| `tests/fixtures/manifest.json` | パス索引 |
| `tests/fixtures/api-input/` | E2E 入力 |
| `supabase/seeds/test-data/` + `scripts/db/seed-test-data.sh` | ephemeral DB 前提データ |
| `.github/workflows/ci-db.yml` | ephemeral DB 手順の正本（C1） |
| `.github/workflows/test-system.yml` | Layer2 システムテスト workflow |

Phase4b skip 条件の正本は [テスト定義書 §9.5.3](../../docs/05_アプリケーション設計/テスト/テスト定義書.md) を参照する。
