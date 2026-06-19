# supabase/seeds/test-data/

ローカル開発・テスト用 seed SQL の配置先（**本番非適用**）。

| 項目 | 方針 |
| ---- | ---- |
| 自動投入 | `supabase db reset` では **投入しない**（`config.toml` [db.seed] に含めない） |
| 担当 | Epic C C2 `test-fixtures-seed` |
| 投入 | 後続 script またはテスト setup から明示的に実行 |

master seed は [`../masters/`](../masters/) を正とする。
