# scripts/

汎用スクリプト配置ディレクトリ（正本: [プロジェクトディレクトリ構成定義書](../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) §12）。

GitHub Issue / PR / Projects に強く依存するスクリプトは `.github/scripts/` に置く。

## サブディレクトリ

| パス | 役割 |
| ---- | ---- |
| [`dev/`](./dev/) | 開発環境起動・ローカル確認補助 |
| [`db/`](./db/) | migration / seed / 検証 SQL 実行補助 |
| [`batch/`](./batch/) | Batch 手動実行・dry-run 補助 |
| [`ops/`](./ops/) | health check / post deploy check 補助 |
| [`ai/`](./ai/) | Task Definition 検証等（Python 実装は Phase0 別 Task） |

## 環境変数

- 変数名正本: [環境設計書 §19](../docs/06_実装設計/cross_cutting/環境設計書.md)
- ローカル例示: [`.env.example`](../.env.example)（`.env` は Git 管理しない）

## MVP（Task ③）

- `scripts/dev/` に最小補助のみ実装
- docker-compose 同梱なし（Human 判断 2026-06-07）
- PostgreSQL / Redis は手動起動またはクラウド dev インスタンスを前提
