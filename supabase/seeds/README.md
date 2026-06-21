# supabase/seeds/

Supabase CLI 管理下の seed SQL 配置。正本は [`config.toml`](../config.toml) の `[db.seed].sql_paths` と連動する。

| パス | 役割 | `db reset` 時 |
| ---- | ---- | ------------- |
| `masters/` | master seed SQL 正本（開発用ダミーデータ） | 自動投入 |
| `test-data/` | ローカル / テスト用（本番非適用） | **投入しない** |

## master seed

- SQL 正本: `masters/*.sql`（ファイル名昇順 = [初期データ定義書](../../docs/06_実装設計/database/初期データ定義書.md) §7）
- CLI 設定: `supabase/config.toml` → `[db.seed] sql_paths = ["./seeds/masters/*.sql"]`
- 手動再投入: `./scripts/db/seed-masters.sh`（migration 済み・データ維持時）

## test-data

Layer2 システム/品質テスト用最小 seed（Issue #674）。自動 seed には含めない。

- SQL: `test-data/*.sql`
- 投入: `./scripts/db/seed-test-data.sh`
- fixture 索引: `tests/fixtures/manifest.json`
