# supabase/seeds/test-data/

ローカル開発・Layer2 GHA テスト用 seed SQL（**本番非適用**）。

| 項目 | 方針 |
| ---- | ---- |
| 自動投入 | `supabase db reset` では **投入しない**（`config.toml` [db.seed] に含めない） |
| 担当 | Epic C C2 `test-fixtures-seed`（Issue #674） |
| 投入 | `./scripts/db/seed-test-data.sh`（master seed 適用後に明示実行） |
| fixture 対応 | 論理 ID は `tests/fixtures/manifest.json` の `items` を正とする |

## ファイル

| ファイル | 内容 |
| -------- | ---- |
| `01_test_items.sql` | item / item_image / item_review_summary（3 件） |
| `02_test_item_derived.sql` | item_feature / item_meaning / item_embedding |

master seed は [`../masters/`](../masters/) を正とする。C1 `ci-db.yml` は master seed のみ自動適用する。

## API-PUB-002 縦串との関係（Issue #1137）

| 観点 | 現状 |
| ---- | ---- |
| item 側 fixture | 3 件 + feature 24 行で **充足**（boss/thanks 向けの意味特徴を含む） |
| `recommendation_request` seed | **未同梱**。追加しても api Router 未マウント・ScaffoldDbSession・reco pair_reader scaffold 等（[ローカル開発手順書 §10.4.4](../../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md)）を解消しない |
| 本ディレクトリの方針 | レーン 0c では **SQL 拡充せず**、縦串ブロッカーは app / composition 後続 Task へ切り出す |

検証コマンド例:

```bash
./scripts/db/seed-test-data.sh
# → items=3, item_feature rows=24
```
