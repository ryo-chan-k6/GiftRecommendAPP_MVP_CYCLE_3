# scripts/batch/

Batch 手動実行・dry-run・再実行補助、および local 薄いオーケストレータを配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md) | Batch 環境変数 |
| [CI・CD方針書](../../docs/05_アプリケーション設計/共通/CI・CD方針書.md) | Batch は GitHub Actions 手動/定期実行を基本 |
| [local薄いオーケストレータ設計・運用手順](../../docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md) | local 親シェルの設計正本 |
| [local_cron_Phase1_crontab運用手順](../../docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md) | Phase1 crontab 運用手順・定常ノブ（#1813） |
| [local_cron_Phase2_dry-run検証結果](../../docs/15_運用・改善/運用手順/local_cron_Phase2_dry-run検証結果.md) | Phase2 dry-run 双方モード検証記録（#1824） |
| [fetch_plan拡大_第1波_1ジャンル手動実行手順](../../docs/15_運用・改善/運用手順/fetch_plan拡大_第1波_1ジャンル手動実行手順.md) | 案B第1波・1ジャンル手動起動・切替ゲート（#1846。crontab変更なし） |

## local 薄いオーケストレータ（#1804 / Phase2 #1822）

| スクリプト | 用途 |
| ---------- | ---- |
| `local_daily_orchestrator.sh` | 日次相当（002 → import 連鎖 → 任意で meaning → 016） |
| `local_weekly_orchestrator.sh` | 週次相当（001 → 002 → import → existing → 任意で meaning → 016） |
| `lib/local_orchestrator_common.sh` | flock / Run ID / 段実行 / 失敗停止 / Phase2 意味連鎖 |
| `genre_map_campaign_runner.sh` | ジャンル地図キャンペーン専用 BFS ラッパ（葉 BATCH-001 のみ。親シェル非使用） |
| `lib/genre_map_campaign_common.sh` | キャンペーン用キュー / soft-hard ゲート / Slack フック |

| ディレクトリ | 用途 |
| ------------ | ---- |
| `output-local-orchestrator/` | 親シェルログ＋flock（`locks/` 配下。`scripts/batch/output-*/` で gitignored） |
| `output-genre-map-campaign/` | ジャンル地図キャンペーン状態・ログ（gitignored） |

ジャンル地図キャンペーン（#1827 / #1833）の手順正本: [ジャンル地図キャンペーン_BFS段階同期手順](../../docs/15_運用・改善/運用手順/ジャンル地図キャンペーン_BFS段階同期手順.md)。
AI は `--dry-run` のみ。`--live-rakuten` は Human 専用（`--i-am-human` 必須）。weekly/daily 親シェルは呼ばない。

### 起動例

```bash
# dry-run（順序・flock・pipeline_batch_run_id のみ。楽天HTTPなし）
# 既定は Phase1 互換（009〜016 スキップ）
./scripts/batch/local_daily_orchestrator.sh --dry-run
./scripts/batch/local_weekly_orchestrator.sh --dry-run

# Phase2 配線確認（009〜016 も含む dry-run。live ではない）
./scripts/batch/local_daily_orchestrator.sh --dry-run --run-meaning
./scripts/batch/local_weekly_orchestrator.sh --dry-run --run-meaning

# live（明示フラグ必須。secret は .env から読み、値をエコーしない）
# 実行場所: 登録済み egress IP の WSL/local のみ。GHA 禁止。
# Phase2 意味生成を live で回す場合は Human が --run-meaning を追加（crontab cutover 後）。
set -a && source .env && set +a
./scripts/batch/local_daily_orchestrator.sh --live-rakuten
```

| フラグ | 意味 |
| ------ | ---- |
| `--dry-run` | 外部副作用なしで順序・lock・Run ID を確認 |
| `--live-rakuten` | 楽天 HTTP live 明示（`--dry-run` と排他） |
| `--pipeline-batch-run-id` | 既存 ID の継続（import 連鎖） |
| `--from-step` | 再開開始段 |
| `--skip-import-summary` | import 連鎖末尾の BATCH-017 スキップ |
| `--no-import-chain` | 003/004 後の 005〜008 スキップ |
| `--run-meaning` | Phase2: 009〜016 を実行（**既定はスキップ＝Phase1 互換**） |
| `--skip-meaning` | Phase2: 009〜016 を明示スキップ（既定と同義。`--run-meaning` と排他） |
| `--skip-meaning-summary` | 意味連鎖末尾の BATCH-017 スキップ |
| `--meaning-pipeline-batch-run-id` | 意味連鎖の既存 pipeline ID 継続 |
| `--source` | 意味生成 source（既定 `rakuten`） |
| `--max-items` / `--pages-per-run` / `--cursors-per-run` | 予算ノブ |
| `--genre-ids` | BATCH-003（および weekly BATCH-001）向け。段階3で拡大する側（既定 `100005`） |
| `--ranking-genre-ids` | BATCH-002 Ranking 向け（既定 `100005`。#1765: `100000`/`100003`/`100004` は Ranking 400） |
| `--no-update-sort` / `--allow-update-sort` | BATCH-003 update_sort（既定は除外） |
| `--max-qps` | BATCH-003 安全側 QPS 上書き |

段階3例（Human・Ranking は `100005` のまま、取得ジャンルだけ拡大）:

```bash
# 先にジャンル同期が必要なら weekly（001→002→003…）
./scripts/batch/local_weekly_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1

# 日次のみ（001スキップ。cursor が既にある場合）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

第1波拡大（案B・Human・`--genre-ids` 常に1本。詳細は [手動実行手順](../../docs/15_運用・改善/運用手順/fetch_plan拡大_第1波_1ジャンル手動実行手順.md)）:

```bash
# dry-run（AI可）
./scripts/batch/local_daily_orchestrator.sh --dry-run \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=1 --max-qps 1

# smoke live（Humanのみ。案Bを複数並べない。定常crontabは変更しない）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 101381 --ranking-genre-ids 100005 \
  --pages-per-run=1 --max-qps 1
```

葉 Batch の `--job-run-id` は段ごとに UUID を発行する（`pipeline_batch_run_id` を複数葉の `batch_run_log` PK に共用しない）。業務紐付けは `--diff-batch-run-id` / `--batch-run-id` 等で pipeline ID を渡す。

**実 crontab 登録は Human**（正本: [local_cron_Phase1_crontab運用手順](../../docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md)。設計要約は [local薄いオーケストレータ設計・運用手順](../../docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md) §7）。本スクリプト群は crontab へ書き込まない。

Phase1 定常ノブ例（Human・ジャンルは1本ローテ）:

```bash
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100005 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

Phase2（#1822）で 009〜016 配線を親シェルへ追加済み。**既定はスキップ**（`--run-meaning` opt-in）。
観測中の実 crontab への `--run-meaning` 追加・AI による live 実行は禁止（正本: 設計書 §14）。Airflow 等は導入しない。018/019 は載せない。

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
| 本格収集キャンペーン（オーケストレータ経由） | #1801（完了側） |
| ジャンル地図キャンペーン（BFS ラッパ・葉001） | #1827 / #1833（本 README 追記）→ Human live / collect-docs |
| local cron Phase1（crontab運用・無人観測） | #1811 / #1813（手順）→ 後続 verify |
| local cron Phase2（009〜016 親シェル配線） | #1818 / #1822（実装） / #1824（dry-run記録）→ 後続 cron-cutover（Human） |
| 本番 egress IP 設計 | **Backlog: #1607**・未検討（GHA楽天liveは禁止維持） |
