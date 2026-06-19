# scripts/dev/

ローカル開発向けの補助スクリプト（Task ③ / Task A5）。

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
| [環境設計書 §19](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 環境変数定義 |
| [環境設計書 §19.9](../../docs/06_実装設計/cross_cutting/環境設計書.md) | local 列 |
| [`.env.example`](../../.env.example) | ダミー値付き変数名一覧 |
| [`docker-compose.dev.yml`](../../docker-compose.dev.yml) | Redis サービスのみ |

## スクリプト

| スクリプト | 用途 |
| ---------- | ---- |
| [`copy-env-example.sh`](./copy-env-example.sh) | `.env.example` → `.env` コピー（既存 `.env` は上書きしない） |
| [`check-env-names.sh`](./check-env-names.sh) | `.env.example` の MVP 必須変数名が `.env` に存在するか確認（**値は表示しない**） |
| [`start-redis.sh`](./start-redis.sh) | `docker-compose.dev.yml` で Redis を起動 |
| [`stop-redis.sh`](./stop-redis.sh) | Redis コンテナを停止 |

## 使い方

リポジトリルートから実行する。

```bash
./scripts/dev/copy-env-example.sh
./scripts/dev/check-env-names.sh
# .env を編集後
./scripts/dev/check-env-names.sh --strict

# Redis（Docker Desktop 起動済みであること）
./scripts/dev/start-redis.sh
redis-cli -u "$REDIS_URL" PING
./scripts/dev/stop-redis.sh
```

| [ローカル開発手順書 §6–§10](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | 初回セットアップ・起動・疎通確認 |
