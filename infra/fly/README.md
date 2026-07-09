# infra/fly/

Reco サービス（`apps/reco`）の Fly.io 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [基盤構成設計書 §5.3](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | Reco は外部公開しない |
| [環境設計書 §19.6](../../docs/06_実装設計/cross_cutting/環境設計書.md) | Reco 環境変数 |

## MVP（Task ③）

- `fly.toml` 等の deploy 設定は **未配置**（README のみ）
- Internal API 認証: `RECO_INTERNAL_API_KEY`（api 側と同一値、ログ出力禁止）

## 主な Secret / Config（§19.6）

| 変数 | 区分 |
| ---- | ---- |
| `DATABASE_URL` | secret |
| `REDIS_URL` | secret |
| `OPENAI_API_KEY` | secret |
| `RECO_INTERNAL_API_KEY` | secret |
| `APP_ENV` | config |
