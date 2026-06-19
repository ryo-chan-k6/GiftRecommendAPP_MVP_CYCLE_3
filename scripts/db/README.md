# scripts/db/

DB migration / seed / 検証 SQL 実行補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [DB構築手順書](../../docs/06_実装設計/database/DB構築手順書.md) | ローカル DB 起動・migration 適用の正本 |
| [マイグレーション方針書](../../docs/06_実装設計/database/マイグレーション方針書.md) | `supabase/migrations/` 正本 |
| [プロジェクトディレクトリ構成定義書 §11](../../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) | `db/` 正本 |
| [`supabase/.cli-version`](../../supabase/.cli-version) | Supabase CLI バージョン pin |

## 補助 script（Phase3b Task A3）

| script | 用途 |
| ------ | ---- |
| `check-cli-version.sh` | pin と `supabase --version` の一致確認 |
| `start-local.sh` | `supabase start`（pin 確認後） |
| `migrate-up.sh` | `supabase migration up` |
| `status.sh` | `supabase status` |
| `stop-local.sh` | `supabase stop` |

いずれも **リポジトリ worktree ルート**から実行する。

```bash
./scripts/db/check-cli-version.sh
./scripts/db/start-local.sh
./scripts/db/migrate-up.sh
```

## 前提

- **Supabase CLI + Docker Desktop**（WSL2）。Neon をローカル DB 正本としない
- ローカル接続 env: `DATABASE_URL`（[環境設計書 §19.5 / §19.6 / §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md)）
- seed 詳細は Task A4 `seed-strategy` で正本化

## 配置予定（後続）

- master seed 投入ラッパー（A4）
- ローカル検証 SQL 実行
