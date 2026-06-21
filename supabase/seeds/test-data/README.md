# supabase/seeds/test-data/

ローカル開発・Layer2 GHA テスト用 seed SQL（**本番非適用**）。

| 項目 | 方針 |
| ---- | ---- |
| 自動投入 | `supabase db reset` では **投入しない**（`config.toml` [db.seed] に含めない） |
| 担当 | Epic C C2 `test-fixtures-seed`（Issue #674） |
| 投入 | `./scripts/db/seed-test-data.sh`（master seed 適用後に明示実行） |
| fixture 対応 | 論理 ID は `tests/fixtures/manifest.json` の `items` を正とする |

## ファイル

| ファイル | 内容 |
| -------- | ---- |
| `01_test_items.sql` | item / item_image / item_review_summary（3 件） |
| `02_test_item_derived.sql` | item_feature / item_meaning / item_embedding |

master seed は [`../masters/`](../masters/) を正とする。C1 `ci-db.yml` は master seed のみ自動適用する。
