# BATCH import 連鎖 GHA live 化メモ（案 C3）

## 1. 目的

Epic `#1637` / Task `#1717` で確定した案 C3 に従い、BATCH import 連鎖
（003 → 005 → 006 → 007 → 008 → 017）を GitHub Actions の **stg live** 経路へ切り替える。

本メモは運用上の要点のみを記載する。secret 実値は記載しない。

## 2. Run ID 分離

| ID | 役割 | 生成箇所 |
| --- | --- | --- |
| `pipeline_batch_run_id` | 連鎖全体で共有する業務 `batch_run_id`（obs / raw object key / product_diff / 下流フィルタ / 017 集計対象） | 親 `batch-rakuten-item-import.yml` の `resolve-run-id`（UUID） |
| `job_run_id`（葉ごと） | 各葉の tracker / `batch_run_log` PK | 各葉 workflow で新規 UUID |

017 live では **`job_run_id` ≠ `batch_run_id` が必須**（PK 衝突回避）。

## 3. Environment / Secrets（stg）

| 用途 | Secret 名 |
| --- | --- |
| DB | `STG_DATABASE_URL` → job env `DATABASE_URL` |
| Rakuten（003 のみ） | `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` |
| live フラグ（003） | `BATCH_RAKUTEN_LIVE=1`（または `--live-rakuten`） |

- GitHub Environment: `stg`
- **prod 禁止**
- Object Storage 用 Secrets は未登録 → **`--live-object-storage` は付けない**（scaffold storage）

## 4. 疎通手順（Human）

1. Environment `stg` の Secrets / 承認設定を確認する
2. `Batch Rakuten Item Import` を `workflow_dispatch`（`max_items` は低め推奨）
3. 各葉 job の conclusion と `pipeline_batch_run_id` を記録する（secret なし）
4. Object Storage 未登録により 003→005 の raw 実体参照が失敗し得る点を確認し、必要なら別 Task で live 有効化

## 5. 残リスク

- Object Storage 未登録のため、003 の raw 実体は runner 内 scaffold に留まり、005 以降の raw 読取が失敗し得る
- schedule は無効のまま（別 Wave）
- ranking_snapshot / meaning-generation / existing-item-pipeline は本 Task 対象外
