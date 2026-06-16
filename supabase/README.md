# supabase/

Supabase CLI プロジェクト配置。DB migration の **適用正本** は `migrations/` とする。

| パス | 役割 |
| ---- | ---- |
| `config.toml` | Supabase CLI 設定（ローカルポート、DB バージョン等） |
| `migrations/` | 環境へ適用する SQL（Supabase CLI 管理） |
| `seed.sql` | 任意。`db/seeds/` との関係は Phase3 で決定 |

## ローカル開発（骨子）

```bash
# Supabase CLI インストール後
supabase start
supabase migration up
```

Redis は Supabase 外で Docker 起動する（[基盤構成設計書](../docs/06_実装設計/cross_cutting/基盤構成設計書.md) §5.5）。

詳細は [マイグレーション方針書](../docs/06_実装設計/database/マイグレーション方針書.md) および Phase3 DB構築手順書を正とする。
