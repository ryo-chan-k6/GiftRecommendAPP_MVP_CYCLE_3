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

**案 A（恒久）:** BATCH-003 開始時に `pipeline_batch_run_id` を `batch_run_log` へ **ensure INSERT**（`ON CONFLICT DO NOTHING`、`batch_name=item_import_pipeline`）。葉の tracker 行とは別ヘッダとして 017 の `require_batch_run` / LOGICAL FK を満たす。

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
2. **検証の正本は `Batch Rakuten Item Import`（または Daily 内の `item_import`）** とする
3. 各葉 job の conclusion と `pipeline_batch_run_id` を記録する（secret なし）
4. Storage SigV4 失敗時は Dashboard の Region と実装既定（`us-east-1`）の不一致を疑う

> **Daily Orchestrator 全体 conclusion は見ない。**  
> Daily は meaning-generation 等（本 Task out of scope）を後続実行するため、親全体が failure でも **`item_import` が緑なら本 Task の GHA live 検証は成功**と扱う（Human 確定: 案1 / 2026-07-29）。

## 5. 検証結果（#1717）

| 項目 | 内容 |
| --- | --- |
| Run | [30389689202](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30389689202) |
| SHA | `3ce3f2ee` |
| `item_import`（003→…→017） | **成功**（017 `insert_applied=True`） |
| `item_meaning_generation` / 017 | 失敗（非 UUID `gha-meaning-…`）。**本 Task 対象外** → 別 Task |
| 判定 | **import 連鎖 GHA live 検証 = 成功**（案1） |

### meaning 017（#1726）

| 項目 | 内容 |
| --- | --- |
| 問題 | 非 UUID `gha-meaning-…` を live 017 に渡し Postgres UUID エラー |
| 対応 | `batch-item-meaning-generation.yml` の resolve を UUID 化。017 は pipeline 欠落時 ensure |
| 葉 009–015 | 当面 scaffold（live 化は別途 Human） |

## 6. 残リスク

- schedule は無効のまま（別 Wave）
- ranking_snapshot / existing-item-pipeline は本 Task 対象外
- meaning 葉（009–015）live は未実施（#1726 は 017 UUID/ensure まで）
- Daily 親全体は meaning 葉 scaffold でも 017 まで通る想定（集計は空寄りになりうる）
- Environment `stg` の required reviewers により、各葉 job 実行前に Human 承認が必要
- **GHA 上の楽天 live は禁止**（登録 egress IP 外）。実楽天疎通は local/WSL のみ。固定 egress は Backlog

## 7. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-28 | 初版（Object Storage 未配線） |
| 2026-07-29 | Object Storage Secrets/Variables 登録後、003/005 に live 配線 |
| 2026-07-29 | 案 A: GHA の 003 楽天を Scaffold に戻す（HTTP 403 / CI live 禁止方針） |
| 2026-07-29 | 案 A scaffold Raw に itemUrl/itemPrice 等を付与（005 GRS-VAL-001 回避） |
| 2026-07-29 | 案 A: BATCH-003 で pipeline `batch_run_log` ensure（017 `require_batch_run` 不足解消） |
| 2026-07-29 | 案1: import 連鎖検証成功を記録。meaning 017 は別 Task。Daily 全体 conclusion は判定に使わない |
| 2026-07-29 | #1726: meaning resolve UUID 化 + 017 pipeline ensure |
