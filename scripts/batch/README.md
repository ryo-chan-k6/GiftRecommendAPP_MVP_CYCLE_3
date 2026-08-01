# scripts/batch/

Batch 手動実行・dry-run・再実行補助、および local 薄いオーケストレータを配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md) | Batch 環境変数 |
| [CI・CD方針書](../../docs/05_アプリケーション設計/共通/CI・CD方針書.md) | Batch は GitHub Actions 手動/定期実行を基本 |
| [local薄いオーケストレータ設計・運用手順](../../docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md) | local 親シェルの正本 |

## local 薄いオーケストレータ（#1804）

| スクリプト | 用途 |
| ---------- | ---- |
| `local_daily_orchestrator.sh` | 日次相当 Phase1（002 → import 連鎖） |
| `local_weekly_orchestrator.sh` | 週次相当 Phase1（001 → 002 → import → existing） |
| `lib/local_orchestrator_common.sh` | flock / Run ID / 段実行 / 失敗停止 |

| ディレクトリ | 用途 |
| ------------ | ---- |
| `output-local-orchestrator/` | 親シェルログ＋flock（`locks/` 配下。`scripts/batch/output-*/` で gitignored） |

### 起動例

```bash
# dry-run（順序・flock・pipeline_batch_run_id のみ。楽天HTTPなし）
./scripts/batch/local_daily_orchestrator.sh --dry-run
./scripts/batch/local_weekly_orchestrator.sh --dry-run

# live（明示フラグ必須。secret は .env から読み、値をエコーしない）
# 実行場所: 登録済み egress IP の WSL/local のみ。GHA 禁止。
set -a && source .env && set +a
./scripts/batch/local_daily_orchestrator.sh --live-rakuten
```

| フラグ | 意味 |
| ------ | ---- |
| `--dry-run` | 外部副作用なしで順序・lock・Run ID を確認 |
| `--live-rakuten` | 楽天 HTTP live 明示（`--dry-run` と排他） |
| `--pipeline-batch-run-id` | 既存 ID の継続 |
| `--from-step` | 再開開始段 |
| `--skip-import-summary` | BATCH-017 スキップ |
| `--no-import-chain` | 003/004 後の 005〜008 スキップ |
| `--max-items` / `--pages-per-run` / `--cursors-per-run` | 予算ノブ |
| `--genre-ids` | 対象ジャンル（既定 `100005`。#1765: Ranking API は `100000`/`100003`/`100004` が 400） |
| `--no-update-sort` / `--allow-update-sort` | BATCH-003 update_sort（既定は除外） |
| `--max-qps` | BATCH-003 安全側 QPS 上書き |

**実 crontab 登録は Human**（例は設計・運用手順 §7）。本スクリプト群は crontab へ書き込まない。

Phase1 に BATCH-009〜015 は含めない。Airflow 等は導入しない。

## ハーネス（明示 live のみ）

| スクリプト | 用途 |
| ---------- | ---- |
| `rakuten_live_verify.py` | 楽天 API 疎通（#1603 / TV-001〜003）。`--live-rakuten` 必須 |
| `object_storage_live_verify.py` | Supabase Storage（S3 互換）put/get（#1617・リリース準備）。`--live-object-storage` 必須 |

出力ディレクトリ `scripts/batch/output-*/` は Git 管理外。CI 既定 live は禁止。

### 楽天 live（#1603）

| 項目 | 内容 |
| ---- | ---- |
| 実行場所 | 登録済み外部 IP を持つ **WSL（local）のみ**。CI live 禁止 |
| QPS | **常用 2**（ハードキャップ 10）。`RAKUTEN_MAX_QPS` / `RAKUTEN_MIN_INTERVAL_MS` |
| IP 照合 | `RAKUTEN_EXPECTED_EGRESS_IP` **必須**。不一致時は楽天 HTTP しない |
| 出力 | `scripts/batch/output-rakuten-live/`（gitignored） |
| secret | env の `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY`。値をログに出さない |
| Human 判断 | `ai-logs/human-decisions/2026-07-25-rakuten-operational-qps-revise-to-2.md`（常用 QPS=2） |

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten \
  --output-dir ../../scripts/batch/output-rakuten-live
```

### Object Storage live（#1617・リリース準備）

手順正本: [ローカル開発手順書 §7.4](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) / [PoC 計画](../../docs/90_PoC/外部API疎通検証/Supabase_Storage_S3互換疎通検証計画.md)

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/object_storage_live_verify.py \
  --live-object-storage --probe-missing \
  --output-dir ../../scripts/batch/output-object-storage-live
```

## 後続

| 対象 | 担当 |
| ---- | ---- |
| 本格収集キャンペーン（オーケストレータ経由） | #1801 |
| 本番 egress IP 設計 | **Backlog: #1607**・未検討（GHA楽天liveは禁止維持） |
