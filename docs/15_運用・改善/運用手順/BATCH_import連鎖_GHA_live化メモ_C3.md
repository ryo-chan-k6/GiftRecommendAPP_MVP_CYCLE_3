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

## 3. Environment / Secrets / Variables（stg）

| 用途 | 名前 | 種別 |
| --- | --- | --- |
| DB | `STG_DATABASE_URL` → job env `DATABASE_URL` | Secret |
| Object Storage | `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` | Secret |
| Object Storage | `OBJECT_STORAGE_BUCKET` / `OBJECT_STORAGE_ENDPOINT` | Variable |
| live フラグ | `BATCH_OBJECT_STORAGE_LIVE=1`（003/005） | Variable / CLI |

- GitHub Environment: `stg`
- **prod 禁止**
- 003/005 は `--live-object-storage` 付き
- **003 の楽天 HTTP は GHA では行わない**（Scaffold）。`--live-rakuten` / `RAKUTEN_*` は GHA に載せない

## 4. 疎通手順（Human）

1. Environment `stg` の Secrets / Variables / 承認設定を確認する
2. `Batch Rakuten Item Import` または `Batch Daily Orchestrator` を `workflow_dispatch`（`max_items` は低め推奨）
3. 各葉 job の conclusion と `pipeline_batch_run_id` を記録する（secret なし）
4. Storage SigV4 失敗時は Dashboard の Region と実装既定（`us-east-1`）の不一致を疑う

## 5. 残リスク

- schedule は無効のまま（別 Wave）
- ranking_snapshot / meaning-generation / existing-item-pipeline は本 Task 対象外
- Environment `stg` の required reviewers により、各葉 job 実行前に Human 承認が必要
- **GHA 上の楽天 live は禁止**（登録 egress IP 外）。実楽天疎通は local/WSL のみ。固定 egress は Backlog

## 6. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-28 | 初版（Object Storage 未配線） |
| 2026-07-29 | Object Storage Secrets/Variables 登録後、003/005 に live 配線 |
| 2026-07-29 | 案 A: GHA の 003 楽天を Scaffold に戻す（HTTP 403 / CI live 禁止方針） |
