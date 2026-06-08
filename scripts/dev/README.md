# scripts/dev/

ローカル開発向けの補助スクリプト（Task ③）。

## 前提（Human 判断 2026-06-07）

- **docker-compose 同梱なし**。PostgreSQL / Redis は手動起動または Neon / クラウド dev を利用
- 環境変数はリポジトリルートの `.env`（`.env.example` から作成）を正とする
- secret 実値をスクリプト出力・ログに含めない

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 環境変数定義 |
| [環境設計書 §19.9](../../docs/06_実装設計/cross_cutting/環境設計書.md) | local 列 |
| [`.env.example`](../../.env.example) | ダミー値付き変数名一覧 |

## スクリプト

| スクリプト | 用途 |
| ---------- | ---- |
| [`copy-env-example.sh`](./copy-env-example.sh) | `.env.example` → `.env` コピー（既存 `.env` は上書きしない） |
| [`check-env-names.sh`](./check-env-names.sh) | `.env.example` の MVP 必須変数名が `.env` に存在するか確認（**値は表示しない**） |

## 使い方

リポジトリルートから実行する。

```bash
./scripts/dev/copy-env-example.sh
./scripts/dev/check-env-names.sh
# .env を編集後
./scripts/dev/check-env-names.sh --strict
```

詳細な起動手順は Task ④（ローカル開発手順 docs）で正本化予定。
