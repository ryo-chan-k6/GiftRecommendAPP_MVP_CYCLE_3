# supabase/

Supabase CLI プロジェクト配置。DB migration の **適用正本** は `migrations/`、master seed の **SQL 正本** は `seeds/masters/` とする。

| パス | 役割 |
| ---- | ---- |
| `.cli-version` | Supabase CLI バージョン pin（正本） |
| `config.toml` | Supabase CLI 設定（ローカルポート、DB バージョン、`[db.seed]` 等） |
| `migrations/` | 環境へ適用する SQL（Supabase CLI 管理） |
| `seeds/masters/` | master seed SQL 正本（`db reset` 時に自動投入） |
| `seeds/test-data/` | ローカル / テスト用（自動 seed 外） |

`supabase/seed.sql` 単体正本は **採用しない**。modular seeds + `config.toml` [db.seed] を正とする。

## Supabase CLI バージョン

正本: [`supabase/.cli-version`](./.cli-version)

```bash
./scripts/db/check-cli-version.sh
```

## ローカル開発

詳細手順の正本: [DB構築手順書](../docs/06_実装設計/database/DB構築手順書.md)

```bash
./scripts/db/start-local.sh
./scripts/db/migrate-up.sh
./scripts/db/reset-local.sh    # migration + master seed（ローカル DB 全消去）
./scripts/db/seed-masters.sh   # master seed のみ再投入
./scripts/db/status.sh
```

`supabase status` の DB URL を `.env` の `DATABASE_URL` に合わせる（実値は Git 管理しない）。

Redis は Supabase 外で起動する（[基盤構成設計書](../docs/06_実装設計/cross_cutting/基盤構成設計書.md) §5.5）。

**DDL スモーク検証（Phase2）**: [ローカルDB検証手順書](../docs/06_実装設計/database/ローカルDB検証手順書.md)（`db/ddl/` 直接適用）。通常開発では **`supabase migration up` を正**とする。

**初期データ**: [初期データ定義書](../docs/06_実装設計/database/初期データ定義書.md)（投入順・行数・固定 ID）。
