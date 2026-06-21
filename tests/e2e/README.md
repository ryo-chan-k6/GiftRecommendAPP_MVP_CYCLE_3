# tests/e2e/

システムテスト（Epic C C3 `test-system.yml`）向け E2E テスト配置先。

C3 Task では workflow 骨格と主要 API 導線テストを追加する。本 Task（C2）では fixture 正本のみ整備し、実行コードは C3 scope とする。

## C3 からの参照

| 参照先 | 用途 |
| ------ | ---- |
| `tests/fixtures/manifest.json` | パス索引 |
| `tests/fixtures/api-input/` | E2E 入力 |
| `supabase/seeds/test-data/` + `scripts/db/seed-test-data.sh` | ephemeral DB 前提データ |
| `.github/workflows/ci-db.yml` | reusable ephemeral DB |
