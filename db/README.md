# db/

DDL・seed・検証 SQL を配置する。**DB migration の適用正本は `supabase/migrations/`**（[マイグレーション方針書](../docs/06_実装設計/database/マイグレーション方針書.md)）。

| パス | 役割 | 正本 |
| ---- | ---- | ---- |
| `ddl/` | 設計・レビュー用 DDL（1 変更 = 1 ファイル） | 参照用 |
| `seeds/masters/` | 初期マスタ投入 SQL | seed 論理正本 |
| `seeds/test-data/` | ローカル開発用（本番非適用） | ローカルのみ |
| `queries/` | 検証・運用 SQL | — |

migration 適用・ローカル起動は [supabase/README.md](../supabase/README.md) を参照する。

master seed の投入順・値の意味は [初期データ定義書](../docs/06_実装設計/database/初期データ定義書.md) を正とする。
