# scripts/db/

DB migration / seed / 検証 SQL 実行補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [プロジェクトディレクトリ構成定義書 §11](../../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) | `db/` 正本 |
| Phase2 Epic | `db/migrations` / `db/seeds` は DB 物理設計 Task scope |

## MVP（Task ③）

- README のみ（実行スクリプトは Phase2 / Task ④ 以降で追加）
- ローカル接続 env: `DATABASE_URL`（§19.5 / §19.6 / §19.7）

## 配置予定（後続）

- migration 実行ラッパー
- seed 投入補助
- ローカル検証 SQL 実行
