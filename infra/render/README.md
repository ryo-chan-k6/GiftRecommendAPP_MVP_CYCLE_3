# infra/render/

API サービス（`apps/api`）の Render 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [デプロイ設定書](../../docs/14_リリース/デプロイ設定/デプロイ設定書.md) | MVP プロバイダ正本（API = Render） |
| [基盤構成設計書 §5.2](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | API 基盤 |
| [環境変数定義書 §7](../../docs/06_実装設計/cross_cutting/環境変数定義書.md) | API 環境変数 |
| [簡易stg構築手順 §6.4](../../docs/15_運用・改善/運用手順/簡易stg構築手順.md) | stg 構築チェック（A1〜A4） |

## MVP 方針

- 本番用 `render.yaml` 等の IaC 本配置は **未配置**（Dashboard 手動作成可。IaC は後続）
- Secret は Render Dashboard の Environment Variables で注入する（実値を Git に含めない）
- Node バージョンはリポジトリルート [`.node-version`](../../.node-version) に従う

## 推奨 Web Service 設定（API stg / prod）

| 項目 | 推奨 |
| ---- | ---- |
| Language / Runtime | Node |
| Root Directory | （空＝リポジトリルート。pnpm workspace のため） |
| Branch | stg: `develop` / prod: 運用方針に従う（別サービス推奨） |
| Health Check Path | `/api/v1/health`（`/healthz` ではない） |

### Build Command

```bash
corepack enable && pnpm install --frozen-lockfile && pnpm --filter @gift-recommendation/api build
```

前提: ルート [`pnpm-workspace.yaml`](../../pnpm-workspace.yaml) に `allowBuilds`（esbuild / sharp / unrs-resolver）があること（#1718）。  
`strict-dep-builds=false` などの暫定フラグは **使わない**。

### Start Command

```bash
pnpm --filter @gift-recommendation/api exec node dist/src/index.js
```

### 主な Environment Variables（名前のみ）

| Key | 備考 |
| --- | ---- |
| `APP_ENV` | `stg` / `prod` |
| `DATABASE_URL` | Secret |
| `REDIS_URL` | Secret（Upstash。TLS 推奨） |
| `RECO_BASE_URL` | Reco の Base URL |
| `RECO_INTERNAL_API_KEY` | Secret（reco と同一値） |
| `CORS_ALLOWED_ORIGINS` | Web origin |
| `PORT` | Render が注入する場合は未設定可 |

詳細は [環境変数定義書 §7](../../docs/06_実装設計/cross_cutting/環境変数定義書.md)。

## ローカル開発

ローカル API 起動時の env はリポジトリルートの `.env`（`.env.example` からコピー）を参照。[ローカル開発手順書](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) を正本とする。
