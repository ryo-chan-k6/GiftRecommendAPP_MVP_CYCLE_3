# infra/render/

API サービス（`apps/api`）の Render 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [基盤構成設計書 §5.2](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | API 基盤 |
| [環境設計書 §19.5](../../docs/06_実装設計/cross_cutting/環境設計書.md) | API 環境変数 |
| [環境設計書 §19.9](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 設定先マトリクス（API ホスティング列） |

## MVP（Task ③）

- 本番 deploy 用 `render.yaml` 等は **未配置**（README のみ）
- 変数名の正本: `.env.example` / 環境設計書 §19.5
- Secret は Render Dashboard / Environment Group で注入する

## ローカル開発

ローカル API 起動時の env はリポジトリルートの `.env`（`.env.example` からコピー）を参照。手順は Task ④（ローカル開発手順）で正本化予定。
