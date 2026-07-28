# infra/vercel/

Web アプリ（`apps/web`）の Vercel 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [デプロイ設定書](../../docs/14_リリース/デプロイ設定/デプロイ設定書.md) | MVP プロバイダ正本（Web = Vercel） |
| [基盤構成設計書 §5.1](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | Web 基盤 |
| [環境変数定義書 §6](../../docs/06_実装設計/cross_cutting/環境変数定義書.md) | Web 環境変数 |
| [認証・認可方針書 §17.2](../../docs/05_アプリケーション設計/基盤/認証・認可方針書.md) | Web は server-side secret を保持しない |
| [簡易stg構築手順 §6.6](../../docs/15_運用・改善/運用手順/簡易stg構築手順.md) | stg 構築チェック（W1〜W4） |

## MVP 方針

| 項目 | 内容 |
| ---- | ---- |
| アプリ | `apps/web`（Next.js） |
| リポジトリ設定 | [`apps/web/vercel.json`](../../apps/web/vercel.json) |
| Secret | `NEXT_PUBLIC_*` に secret を含めない。DB / API Key / Service Role を Web に置かない |
| stg / prod | 専用 Project 分離、または Environment（Preview ≒ stg、Production ≒ prod）で分離 |

## Dashboard 推奨設定（Web stg）

**Settings → General → Build & Development Settings**

| 項目 | 推奨 |
| ---- | ---- |
| Framework Preset | **Next.js** |
| Root Directory | **`apps/web`**（`./` やリポジトリルートにしない） |
| Output Directory | **空**。Override トグルは **Off**（`public` を指定しない） |
| Install Command | Override On なら `cd ../.. && corepack enable && pnpm install --frozen-lockfile`（`vercel.json` と同値） |
| Build Command | Override On なら `cd ../.. && pnpm --filter @gift-recommendation/web build` |
| Node.js Version | **24.x**（ルート `.node-version` / `engines.node`） |
| Include source files outside Root Directory | **ON** |

`vercel.json` がある場合も、Dashboard の **Output Directory Override が On のまま `public`** だと Next.js 配信が壊れ、ビルド成功後に 404 や `No Output Directory named "public"` になり得る。

## Environment Variables（名前のみ）

| 変数 | Environment | 備考 |
| ---- | ----------- | ---- |
| `NEXT_PUBLIC_API_BASE_URL` | Preview（stg）/ Production（prod） | stg API の origin。末尾 `/` なし |
| `API_BASE_URL` | 同上 | `NEXT_PUBLIC_*` と同値推奨 |

置かない: `DATABASE_URL`、`*_API_KEY`、`SUPABASE_SERVICE_ROLE_KEY` 等。

stg 専用 Project で Production Branch = `develop` の場合は、変数を **Production**（または Preview+Production）にも付ける。

## Deployment Protection

Preview URL は既定で Vercel Authentication がかかることがある。

- 未ログイン → ログイン画面
- 権限なし / 旧デプロイ URL → `404 NOT_FOUND` / `DEPLOYMENT_NOT_FOUND`

stg をブラウザで確認するだけなら、**Settings → Deployment Protection** で Preview の保護を外すか、プロジェクト所有者でログインした状態で **最新 Deployment の Visit** を使う。

## 確認手順（重要）

1. Deployments で **最新の Ready** を開く
2. その行の **Visit** を使う（URL のハッシュはデプロイごとに変わる）
3. **旧 Preview URL をブックマークしない**（旧 URL は `DEPLOYMENT_NOT_FOUND` になる）
4. `/` と `/recommendations` がアプリとして表示されること
5. DevTools → Network で API が stg（例: `*.onrender.com`）を向いていること

安定して共有する URL が必要なら、Production デプロイまたは Project の `*.vercel.app` ドメインを使う。

## API 側 CORS

Web origin 確定後、Render API の `CORS_ALLOWED_ORIGINS` に stg Web origin を追加して再デプロイする。

## out of scope

- secret 実値
- Vercel アカウント作成・課金
- `apps/web` の機能変更
