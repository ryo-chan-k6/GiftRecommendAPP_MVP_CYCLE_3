# db/

DB migration、seed、DDL、検証 SQL を配置する。

| パス | 役割 | 正本 |
| ---- | ---- | ---- |
| `migrations/` | 環境へ適用する migration SQL | 適用正本 |
| `ddl/` | 設計・レビュー用 DDL（1 変更 = 1 ファイル） | 参照用 |
| `seeds/masters/` | 初期マスタ投入 | seed 実行正本 |
| `seeds/test-data/` | ローカル開発用（本番非適用） | ローカルのみ |
| `queries/` | 検証・運用 SQL | — |

運用規約の正本: [マイグレーション方針書](../docs/06_実装設計/database/マイグレーション方針書.md)

ローカル適用コマンドは migration ツール選定後（Human Review）に追記する。
