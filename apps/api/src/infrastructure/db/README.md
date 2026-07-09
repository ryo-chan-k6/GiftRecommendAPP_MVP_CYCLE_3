# Phase4a db Repository scaffold

Phase4a `api-foundation`（A3）の DB Repository 骨格。PostgreSQL 接続前に、session / repository 境界と単体テスト可能な scaffold を定義する。

| ファイル | 責務 |
| -------- | ---- |
| `session.ts` | `DbSession` 境界と `ScaffoldDbSession`（query / execute / healthCheck） |
| `repository.ts` | 共通 Repository 骨格（`findById` / `list` / `requireById`） |
| `errors.ts` | infrastructure 層の `DbError` |
| `connection.ts` | 接続文字列のマスク（ログ出力用） |

`apps/api/src/repositories/**` は Phase4b 識別子 Epic でドメイン別 Repository を追加する。本ディレクトリは infrastructure 層の共通境界を担う。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §6.3

## Phase4b 以降

- Supabase / PostgreSQL 実接続は環境変数 `DATABASE_URL` 経由で session 実装を差し替える
- domain 別 Repository は `repositories/` または modules 配下へ配置し、本 session を注入する
