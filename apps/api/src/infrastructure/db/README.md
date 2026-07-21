# api DB session / Repository

`apps/api` の DB アクセス境界。PostgreSQL 接続は環境変数 `DATABASE_URL` 経由で session 実装を差し替える。

| ファイル | 責務 |
| -------- | ---- |
| `session.ts` | `DbSession` 境界と `ScaffoldDbSession`（query / execute / healthCheck） |
| `postgres-session.ts` | `PostgresDbSession`（`pg` Pool） |
| `factory.ts` | `createDbSession`（`DATABASE_URL` があれば postgres、なければ scaffold） |
| `repository.ts` | 共通 Repository 骨格（`findById` / `list` / `requireById`） |
| `errors.ts` | infrastructure 層の `DbError` |
| `connection.ts` | 接続文字列のマスク（ログ出力用） |

`apps/api/src/repositories/**` は Phase4b 識別子 Epic でドメイン別 Repository を追加する。本ディレクトリは infrastructure 層の共通境界を担う。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §6.3

## 切替方針

| 条件 | 実装 |
| ---- | ---- |
| `DATABASE_URL` が非空かつ `scaffold://` でない | `PostgresDbSession` |
| 未設定 / 空 / `scaffold://` / `forceScaffold` | `ScaffoldDbSession` |

ローカル開発（`./scripts/dev/start-api.sh`）は `.env` の `DATABASE_URL` を読み込むため、PUB-002 は実 PostgreSQL へ `recommendation_request` を INSERT する。

単体テスト・CI は `DATABASE_URL` なし、または `createDbSession({ forceScaffold: true })` / 明示的な `ScaffoldDbSession` 注入で実 DB に依存しない。

**禁止:** 接続文字列・`.env` 実値をログ・docs・commit に出力すること。ログには `maskDatabaseUrl` のみ使用する。
