# scripts/db/

DB migration / seed / 検証 SQL 実行補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [DB構築手順書](../../docs/06_実装設計/database/DB構築手順書.md) | ローカル DB 起動・migration・seed 適用の正本 |
| [マイグレーション方針書](../../docs/06_実装設計/database/マイグレーション方針書.md) | `supabase/migrations/` 正本 |
| [プロジェクトディレクトリ構成定義書 §11](../../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) | `db/` / `supabase/` 配置 |
| [`supabase/.cli-version`](../../supabase/.cli-version) | Supabase CLI バージョン pin |

## 補助 script

| script | 用途 |
| ------ | ---- |
| `check-cli-version.sh` | pin と `supabase --version` の一致確認 |
| `start-local.sh` | `supabase start`（pin 確認後） |
| `migrate-up.sh` | `supabase migration up` |
| `reset-local.sh` | `supabase db reset`（migration + master seed） |
| `seed-masters.sh` | master seed のみ再投入（データ維持時） |
| `verify-seed-setup.sh` | `supabase/seeds/masters` と `config.toml [db.seed]` の正本整合検証 |
| `status.sh` | `supabase status` |
| `stop-local.sh` | `supabase stop` |

いずれも **リポジトリ worktree ルート**から実行する。

```bash
./scripts/db/check-cli-version.sh
./scripts/db/start-local.sh
./scripts/db/migrate-up.sh
./scripts/db/reset-local.sh
./scripts/db/seed-masters.sh
```

## 前提

- **Supabase CLI + Docker Desktop**（WSL2）。Neon をローカル DB 正本としない
- master seed 正本: `supabase/seeds/masters/` + [`supabase/config.toml`](../../supabase/config.toml) `[db.seed]`
- ローカル接続 env: `DATABASE_URL`（[環境設計書 §19.5 / §19.6 / §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md)）
