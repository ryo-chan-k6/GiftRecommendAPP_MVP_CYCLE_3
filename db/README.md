# db/

DDL・検証 SQL を配置する。**DB migration の適用正本は `supabase/migrations/`**（[マイグレーション方針書](../docs/06_実装設計/database/マイグレーション方針書.md)）。

| パス | 役割 | 正本 |
| ---- | ---- | ---- |
| `ddl/` | Phase2 設計・レビュー用 DDL（1 変更 = 1 ファイル） | **参照用**（通常開発では適用しない） |
| `queries/` | 検証・運用 SQL | — |

master seed の SQL 正本は [`supabase/seeds/`](../supabase/seeds/) とする。

master seed の投入順・値の意味は [初期データ定義書](../docs/06_実装設計/database/初期データ定義書.md) を正とする。
