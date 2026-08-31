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
| [`setup-python.sh`](./setup-python.sh) | ルート uv workspace の `.venv` 作成・sync（worktree ごと） |
| [`pytest-python.sh`](./pytest-python.sh) | `packages/shared-logic` / `test-fixtures` の pytest |
| [`setup-python-reco.sh`](./setup-python-reco.sh) | `apps/reco/.venv` 作成（pyproject 整備後） |
| [`pytest-reco.sh`](./pytest-reco.sh) | `apps/reco/tests/unit` の pytest（骨格 merge 後） |
| [`setup-python-batch.sh`](./setup-python-batch.sh) | `apps/batch/.venv` 作成（pyproject 整備後） |
| [`pytest-batch.sh`](./pytest-batch.sh) | `apps/batch/tests/unit` の pytest（骨格 merge 後） |
| [`start-api.sh`](./start-api.sh) | api を `pnpm dev:api` で起動（port **3001**） |
| [`start-web.sh`](./start-web.sh) | web を `pnpm dev:web` で起動（port **3000**） |
| [`start-local-data-browser.sh`](./start-local-data-browser.sh) | local DB の読み取り専用可視化（**127.0.0.1:8787**。`apps/web` 非掲載） |

## 使い方

リポジトリルートから実行する。

```bash
./scripts/dev/copy-env-example.sh
./scripts/dev/check-env-names.sh
# .env を編集後
./scripts/dev/check-env-names.sh --strict

# 疎通チェック（DB / Redis 起動後。api / reco placeholder 期間は --skip-apps 推奨）
./scripts/dev/smoke-check.sh --skip-apps
# インフラのみ（env チェック省略例）
# ./scripts/dev/smoke-check.sh --skip-env --skip-db --skip-apps   # Redis docker のみ確認
# web 起動後、または PUB-001 / INT-001 完了後: apps 疎通も確認
# ./scripts/dev/smoke-check.sh

# Redis（Docker Desktop 起動済みであること）
./scripts/dev/start-redis.sh
redis-cli -u "$REDIS_URL" PING   # 未インストール時は smoke-check が docker 経由で PING
./scripts/dev/stop-redis.sh
```

### アプリ起動（reco → api → web）

各ターミナルで順に実行する（起動順の正本は [基盤構成設計書](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md)）。

```bash
./scripts/dev/start-reco.sh   # terminal 1 — http://localhost:8000
./scripts/dev/start-api.sh    # terminal 2 — http://localhost:3001
./scripts/dev/start-web.sh    # terminal 3 — http://localhost:3000
```

### local データ可視化（管理者確認用サンプル）

SQL を書かずに商品・意味連鎖・Relationship / Occasion / Pair・推薦入力を見る。**localhost のみ**。Vercel には出ない。

楽天ランキングAPIの **①総合 / ③年代別 / ④性別 / ⑤年代×性別**（②ジャンル指定は対象外）を取得し、ジャンル・ショップコード・キーワード選定の材料にする画面は `/ranking`。

`external_genre` の階層と直下子数、OKURI 初期取り扱い対象のチェックは `/genres`。選択は local cache（DB 未書き込み）。ランキング分析の「対象ジャンルで絞り込む」で使えます。`external_genre.parent` が L1 直付けになっている場合は `staging_genre` から直近親を再構成して表示します。

```bash
./scripts/dev/start-local-data-browser.sh   # http://127.0.0.1:8787
# http://127.0.0.1:8787/ranking
# http://127.0.0.1:8787/genres
```

| 項目 | 内容 |
| ---- | ---- |
| bind | `127.0.0.1` のみ（`0.0.0.0` 不可） |
| DB | `.env` の `DATABASE_URL` が loopback のときだけ接続 |
| 操作 | DB は SELECT のみ。ランキング取得・対象ジャンル選択は **local cache**（DB 未書き込み） |
| ランキング | `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` が必要。値は画面・ログに出さない |
| 対象外 | ②ジャンル別ランキング（公式仕様で age / sex と併用不可） |
| 非掲載 | `apps/web` には置かない（Preview 公開を避ける） |

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

Phase4 実装前でも **web** は Next.js が待受するため、停止時は `Ctrl+C` が必要。api / reco / batch が placeholder の場合は即終了するため、通常は停止操作不要。

### Python 単体テスト（worktree ごと）

```bash
./scripts/dev/setup-python.sh
./scripts/dev/pytest-python.sh

# reco-foundation 骨格 merge 後
./scripts/dev/setup-python-reco.sh
./scripts/dev/pytest-reco.sh

# batch-foundation 骨格 merge 後
./scripts/dev/setup-python-batch.sh
./scripts/dev/pytest-batch.sh
```

| 項目 | 内容 |
| ---- | ---- |
| ツール | `uv` + `.python-version`（3.14） |
| venv | ルート `.venv` + `apps/reco/.venv` + `apps/batch/.venv`（いずれも worktree ローカル） |
| CI | `.github/workflows/ci-reco.yml`（Layer1 最小） |

| 項目 | 内容 |
| ---- | ---- |
| monorepo 正本 | ルート `package.json` の `dev:reco` / `dev:api` / `dev:web` |
| batch | ルート `pnpm dev:batch`（ジョブ単位 CLI。本格運用は Phase4b defer） |
| web | `apps/web` の `dev` は **Next.js 実起動**（`pnpm install` 後に `./scripts/dev/start-web.sh`） |
| api | Express + `GET /api/v1/health`（`pnpm install` 後に `./scripts/dev/start-api.sh`） |
| reco | uvicorn + `GET /internal/reco/v1/health`（`setup-python-reco.sh` 後に `./scripts/dev/start-reco.sh`。`X-Internal-Api-Key` 必須） |
| batch | `dev` script は **placeholder**（即終了） |

| [ローカル開発手順書 §6.2](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | Python 初回セットアップ |
| [ローカル開発手順書 §6–§10](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) | 起動・疎通確認 |

### 疎通確認（smoke-check）

| 項目 | 内容 |
| ---- | ---- |
| 一括実行 | `./scripts/dev/smoke-check.sh`（`--skip-*` 対応） |
| env | `./scripts/dev/check-env-names.sh --strict` |
| PostgreSQL | `psql "$DATABASE_URL" -c 'SELECT 1'`（`DATABASE_URL` は [DB構築手順書 §8](../../docs/06_実装設計/database/DB構築手順書.md) / `supabase status` に合わせる） |
| Redis | `redis-cli -u "$REDIS_URL" PING`、または `redis-cli` 未インストール時は smoke-check が **docker compose exec** 経由で PING |
| app health | web / api / reco 起動後は health 200 を期待。未起動時は smoke-check が skip（exit 0） |
| API-PUB-002 縦串 | [ローカル開発手順書 §10.4](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md)（Issue #1137）。`POST /api/v1/recommendations` は現状 404（Router 未マウント）。手順・既知ギャップは手順書を正本とする |
