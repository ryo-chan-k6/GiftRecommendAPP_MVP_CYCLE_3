# infra/fly/

Reco サービス（`apps/reco`）の Fly.io 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [デプロイ設定書](../../docs/14_リリース/デプロイ設定/デプロイ設定書.md) | MVP プロバイダ正本（Reco = Fly.io） |
| [基盤構成設計書 §5.3](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | Reco は外部公開しない（方針） |
| [環境変数定義書 §8](../../docs/06_実装設計/cross_cutting/環境変数定義書.md) | Reco 環境変数 |
| [簡易stg構築手順 §6.5](../../docs/15_運用・改善/運用手順/簡易stg構築手順.md) | stg 構築チェック（C1〜C4） |
| [API-INT-001 実装仕様書](../../docs/06_実装設計/api/API-INT-001_RecoヘルスチェックAPI実装仕様書.md) | Health path / 認証 |

## MVP 方針

| 項目 | 内容 |
| ---- | ---- |
| 配置ファイル | `Dockerfile` / `fly.toml` / `.dockerignore` / 本 README |
| stg app 名（推奨） | `okuri-reco-stg`（`fly.toml` の `app`） |
| Region（推奨） | `nrt`（Tokyo） |
| Runtime | Python 3.14 + uvicorn（`apps/reco`） |
| Listen | `0.0.0.0:8000` |
| 認証 | `RECO_INTERNAL_API_KEY`（api と同一値。ログ出力禁止） |
| 公開 | 方針上は外部公開しない。MVP 簡易 stg では **HTTPS + Internal API Key** で API（Render）から到達可能にする。private / Flycast 本格閉鎖は後続可 |
| Secret | Fly Secrets で注入（実値を Git に含めない） |

## ファイル

| ファイル | 役割 |
| -------- | ---- |
| [`Dockerfile`](./Dockerfile) | `apps/reco` イメージ（リポジトリルートを build context） |
| [`fly.toml`](./fly.toml) | stg 推奨 Fly 設定 |
| [`.dockerignore`](./.dockerignore) | monorepo context の転送削減 |

## 前提（ローカル）

- [flyctl](https://fly.io/docs/hands-on/install-flyctl/) インストール済み
- `fly auth login` 済み
- 作業ディレクトリは **リポジトリルート**

## 初回アプリ作成（C1・Human）

未作成の場合:

```bash
fly apps create okuri-reco-stg
```

既に別名で作成済みの場合は、`fly.toml` の `app` を合わせてからデプロイする（または `--app` で上書き）。

prod は **別アプリ**（例: `okuri-reco-prod`）を作成し、stg と共有しない。

## Secrets / Config（C2・C3・Human）

名前のみ。実値は Dashboard / CLI のみ。チャット・docs・Issue に書かない。

| 変数 | 区分 | 備考 |
| ---- | ---- | ---- |
| `APP_ENV` | config | `fly.toml` `[env]` で `stg` を設定済み。上書き可 |
| `DATABASE_URL` | secret | **API と同じ** stg Supabase |
| `REDIS_URL` | secret | **API と同じ** Upstash stg（TLS 推奨） |
| `RECO_INTERNAL_API_KEY` | secret | **Render API と同一値** |
| `OPENAI_API_KEY` | secret | Embedding / LLM（health 自体は DB probe のみ） |

例（値はシェル履歴に残るため、運用では Dashboard 推奨）:

```bash
fly secrets set DATABASE_URL=... REDIS_URL=... RECO_INTERNAL_API_KEY=... OPENAI_API_KEY=... -a okuri-reco-stg
```

## デプロイ（C4・Human）

リポジトリルートで:

```bash
fly deploy --config infra/fly/fly.toml
```

イメージは `infra/fly/Dockerfile` を使い、context はリポジトリルート（`ignorefile` で `apps/reco` 以外を除外）。

### 起動コマンド（イメージ CMD）

```bash
uvicorn reco.api.main:app --app-dir src --host 0.0.0.0 --port 8000
```

## Health 確認（S3・Human）

アプリケーション Health（正本）:

- Method / Path: `GET /internal/reco/v1/health`
- Header: `X-Internal-Api-Key: <RECO_INTERNAL_API_KEY>`
- 期待: HTTP 200 かつ `data.status` が `"ok"`（DB probe 成功時）

```bash
curl -sS -H "X-Internal-Api-Key: ${RECO_INTERNAL_API_KEY}" \
  "https://okuri-reco-stg.fly.dev/internal/reco/v1/health"
```

- Key なし → 401
- DB NG → 503

Fly プラットフォーム check は **TCP :8000**（Key を `fly.toml` に埋め込まない）。アプリ疎通の正は上記 curl。

Key 実値をチャット・ログ・スクショに残さないこと。

## API（Render）側の接続（Human・必須）

Reco URL 確定後、Render API stg に以下を設定して再デプロイする。

| Key | 値の形 |
| --- | ------ |
| `RECO_BASE_URL` | `https://okuri-reco-stg.fly.dev`（末尾 `/` なし） |
| `RECO_INTERNAL_API_KEY` | Reco と同一 |

## out of scope（本ディレクトリの正本）

- secret 実値
- Fly アカウント作成・課金
- private networking の強制
- `apps/reco` コード変更
