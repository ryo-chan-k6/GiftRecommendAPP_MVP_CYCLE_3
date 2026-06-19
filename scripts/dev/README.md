# scripts/dev/

ローカル開発向けの補助スクリプト（Task ③ / Task A5 / Task A6 / Task A7）。

## 前提

| 項目 | 方針 |
| ---- | ---- |
| PostgreSQL | **Supabase CLI + Docker Desktop**（[DB構築手順書](../../docs/06_実装設計/database/DB構築手順書.md)） |
| Redis | **Redis 限定 `docker-compose.dev.yml`**（Human 判断 2026-06-18、Task A5） |
| 環境変数 | リポジトリルートの `.env`（`.env.example` から作成） |
| secret | 実値をスクリプト出力・ログに含めない |

Phase3a（2026-06-07）の「docker-compose 同梱なし」は **PostgreSQL 用 compose 不採用** を指す。Redis 限定 compose は Phase3b Task A5 で採用する。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [ローカル開発手順書 §7.2](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | Redis 起動手順 |
| [ローカル開発手順書 §9](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | web / api / reco 起動手順 |
| [環境設計書 §19](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 環境変数定義 |
| [環境設計書 §19.9](../../docs/06_実装設計/cross_cutting/環境設計書.md) | local 列 |
| [`.env.example`](../../.env.example) | ダミー値付き変数名一覧 |
| [`docker-compose.dev.yml`](../../docker-compose.dev.yml) | Redis サービスのみ |

## スクリプト

| スクリプト | 用途 |
| ---------- | ---- |
| [`copy-env-example.sh`](./copy-env-example.sh) | `.env.example` → `.env` コピー（既存 `.env` は上書きしない） |
| [`check-env-names.sh`](./check-env-names.sh) | `.env.example` の MVP 必須変数名が `.env` に存在するか確認（**値は表示しない**） |
| [`smoke-check.sh`](./smoke-check.sh) | env / DB / Redis / app health の段階疎通チェック（`--skip-*` 付き） |
| [`start-redis.sh`](./start-redis.sh) | `docker-compose.dev.yml` で Redis を起動 |
| [`stop-redis.sh`](./stop-redis.sh) | Redis コンテナを停止 |
| [`start-reco.sh`](./start-reco.sh) | reco を `pnpm dev:reco` で起動（port **8000**） |
| [`start-api.sh`](./start-api.sh) | api を `pnpm dev:api` で起動（port **3001**） |
| [`start-web.sh`](./start-web.sh) | web を `pnpm dev:web` で起動（port **3000**） |

## 使い方

リポジトリルートから実行する。

```bash
./scripts/dev/copy-env-example.sh
./scripts/dev/check-env-names.sh
# .env を編集後
./scripts/dev/check-env-names.sh --strict

# 疎通チェック（DB / Redis 起動後。Phase3b では --skip-apps 推奨）
./scripts/dev/smoke-check.sh --skip-apps
# インフラ込みの一例（psql / redis-cli / .env が揃っていること）
# ./scripts/dev/smoke-check.sh --skip-apps   # placeholder 期間
# ./scripts/dev/smoke-check.sh               # Phase4 以降（health 成功を確認）

# Redis（Docker Desktop 起動済みであること）
./scripts/dev/start-redis.sh
redis-cli -u "$REDIS_URL" PING
./scripts/dev/stop-redis.sh
```

### アプリ起動（reco → api → web）

各ターミナルで順に実行する（起動順の正本は [基盤構成設計書](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md)）。

```bash
./scripts/dev/start-reco.sh   # terminal 1 — http://localhost:8000
./scripts/dev/start-api.sh    # terminal 2 — http://localhost:3001
./scripts/dev/start-web.sh    # terminal 3 — http://localhost:3000
```

### アプリ停止（web → api → reco）

`start-*.sh` は `exec pnpm dev:*` で**前景実行**する。専用 stop script はなく、起動した各ターミナルで **`Ctrl+C`** する（起動順の逆: web → api → reco）。

```bash
# terminal 3 — web
Ctrl+C

# terminal 2 — api
Ctrl+C

# terminal 1 — reco
Ctrl+C
```

| 項目 | 内容 |
| ---- | ---- |
| Redis | `./scripts/dev/stop-redis.sh`（§7.2。Docker コンテナは別途停止） |
| プロセス残留時 | ポート **3000** / **3001** / **8000** を `lsof -i :<port>` 等で確認し、必要なら `kill <PID>` |

Phase4 実装前（placeholder）は dev プロセスが即終了するため、通常は停止操作不要。

| 項目 | 内容 |
| ---- | ---- |
| monorepo 正本 | ルート `package.json` の `dev:reco` / `dev:api` / `dev:web` |
| batch | ルート `pnpm dev:batch`（ジョブ単位 CLI。本格運用は Phase4b defer） |
| placeholder | 各 app の `dev` script は Phase4 実装まで即終了する placeholder |

| [ローカル開発手順書 §6–§10](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | 初回セットアップ・起動・疎通確認 |
