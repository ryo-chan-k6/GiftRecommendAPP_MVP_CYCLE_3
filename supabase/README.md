# supabase/

Supabase CLI プロジェクト配置。DB migration の **適用正本** は `migrations/` とする。

| パス | 役割 |
| ---- | ---- |
| `.cli-version` | Supabase CLI バージョン pin（正本） |
| `config.toml` | Supabase CLI 設定（ローカルポート、DB バージョン等） |
| `migrations/` | 環境へ適用する SQL（Supabase CLI 管理） |
| `seed.sql` | 任意（`db/seeds/` との関係は Task A4 で決定） |

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
./scripts/db/status.sh
```

`supabase status` の DB URL を `.env` の `DATABASE_URL` に合わせる（実値は Git 管理しない）。

master seed（migration 完了後）の骨子は Task A4 まで暫定として以下を参照:

```bash
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
for f in db/seeds/masters/*.sql; do
  psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"
done
```

Redis は Supabase 外で起動する（[基盤構成設計書](../docs/06_実装設計/cross_cutting/基盤構成設計書.md) §5.5）。

**DDL スモーク検証（Phase2）**: [ローカルDB検証手順書](../docs/06_実装設計/database/ローカルDB検証手順書.md)（`db/ddl/` 直接適用）。通常開発では **`supabase migration up` を正**とする。

**初期データ**: [初期データ定義書](../docs/06_実装設計/database/初期データ定義書.md)（投入順・行数・固定 ID）。
