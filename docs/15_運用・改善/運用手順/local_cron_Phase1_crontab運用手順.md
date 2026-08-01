# local cron Phase1 crontab 運用手順

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順正本（Phase1 crontab） |
| 作成日 | 2026-08-01 |
| 関連Issue | [#1813](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1813)（本手順） / 親Epic [#1811](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1811) |
| Decision正本 | [2026-08-01-batch-local-cron-ops-next](../../../ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md)（`decided`） |
| 親シェル設計正本 | [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) |
| 先行収集結果 | [batch-data-collect-ops_local継続収集結果_1808](./batch-data-collect-ops_local継続収集結果_1808.md) |
| 状態 | 手順正本化済み。**実 crontab 登録は Human（本TaskのAIは登録しない）** |

secret・token・APIキー・egress IP・接続文字列の実値は記載しない。

---

## 2. 目的と非目的

### 2.1 目的

- Phase1（BATCH-001〜008、+017任意）の **crontab 運用手順**を正本化する
- 定常ノブを Decision / 本手順に同期し、Human が安全に cron 登録できる状態にする
- 後続 `cron-ops-verify`（数日無人観測）の着手条件を明記する

### 2.2 非目的（out of scope）

| 対象 | 扱い |
| ---- | ---- |
| 実 crontab への書き込み | **Human のみ**。AI Agent は実行しない |
| `--live-rakuten` の実行 | **Human のみ**（観測期間含む）。AI は実行しない |
| 数日無人観測結果の記録本体 | 後続 Task（`cron-ops-verify`） |
| BATCH-009〜016 配線 | Phase2 別Epic |
| BATCH-018 / 019 | 自動運用対象外 |
| GHA `on.schedule` 有効化（#1792） | 先送り |
| #1607 / GHA 楽天 live | 先送り・禁止維持 |

---

## 3. 起動境界（必須）

| ルール | 内容 |
| ------ | ---- |
| 親シェル経由のみ | crontab に載せるのは `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` のみ |
| 個別 cron 禁止 | BATCH-001〜008（および葉 Batch）を crontab に直接載せない |
| 同時 live 禁止 | 楽天 HTTP live は横断で **常に1本**。daily と weekly を同日同時起動しない |
| 明示 live | cron 行には `--live-rakuten` を明示する（暗黙 live 禁止） |
| 実行場所 | 登録済み egress の **local / WSL のみ**。GHA からの楽天 live は禁止 |
| secret | `.env` 等から読み込む。値をログ・docs・Issue・PR に出さない |

排他（flock）の詳細は [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) §5。

---

## 4. Phase1 定常ノブ（採用値）

本節の値は Human Decision `2026-08-01-batch-local-cron-ops-next` §6 と同期する。最終採択の継続/変更は Human 判断点。

| ノブ | Phase1 定常値 | 備考 |
| ---- | ------------- | ---- |
| `pages_per_run` | **60** | 通常継続（運用方針 §5.3.4）。親シェル既定は 10 のため **cron 行で明示必須** |
| `cursors_per_run` | **1**（既定） | 変更しない |
| `max_qps` | **1** | 長時間・003 安全側。cron 行で明示 |
| `--ranking-genre-ids` | **100005** | Ranking 固定（#1765。他ジャンルは Ranking 400） |
| `--genre-ids` | **1本ローテ** | MVP: `100005` / `100003` / `100004` / `100000` を **1本ずつ**。同時複数ジャンル live 禁止 |
| BATCH-017 | **任意** | 不要時は `--skip-import-summary` |
| 同時 live | **禁止** | 親シェルの rakuten-live flock＋運用ルール |

ジャンルローテ例（日替わり。Ranking は常に `100005`）:

| 日 | `--genre-ids` | `--ranking-genre-ids` |
| -- | ------------- | --------------------- |
| 例1 | `100005` | `100005` |
| 例2 | `100003` | `100005` |
| 例3 | `100004` | `100005` |
| 例4 | `100000` | `100005` |

ローテ切替は Human が crontab 行（または当日の手動上書き方針）を更新する。自動ローテスクリプトの導入は本手順の対象外。

---

## 5. crontab 登録例（参考のみ・AIは登録しない）

タイムゾーンはホストの cron 設定に依存する。以下は **JST 想定の例**。パスは環境に合わせて置換する。

### 5.1 登録対象（親シェルのみ）

```cron
# 【例】実登録は Human。AI / Task #1813 は crontab へ書き込まない。
# リポジトリルートで実行する前提。パス・ユーザは環境に合わせる。
# .env は親シェルが --live-rakuten 時に読み込む（値をエコーしない）。

# local-daily: 月曜〜土曜 00:30 JST（当日の取得ジャンルは --genre-ids を Human がローテ更新）
30 0 * * 1-6  cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-daily.log 2>&1

# local-weekly: 日曜 00:30 JST（当日は daily を入れない。001→002→import→existing）
30 0 * * 0    cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_weekly_orchestrator.sh --live-rakuten --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-weekly.log 2>&1
```

### 5.2 Human が実行する登録コマンド例（実登録はしない・手順のみ）

AI Agent は以下を **実行しない**。Human がタイミングを判断して実施する。

```bash
# 1) 事前確認（楽天 HTTP なし）
cd /path/to/GiftRecommendAPP_MVP_CYCLE_3
./scripts/batch/local_daily_orchestrator.sh --dry-run
./scripts/batch/local_weekly_orchestrator.sh --dry-run

# 2) crontab 編集（例）。既存行を壊さないよう注意。
crontab -e
# → §5.1 の2行を追加（パス・ジャンルを環境に合わせる）

# 3) 登録確認（一覧のみ。書き込みではない）
crontab -l
```

### 5.3 禁止例

```cron
# NG: 葉 Batch を直接 cron する
# 0 1 * * *  ... uv run python -m batch.application.item_pseudo_diff ...

# NG: daily と weekly を同日同時刻に並べる
# NG: --live-rakuten なしで cron する（暗黙 live 拒否で失敗する）
# NG: pages-per-run / max-qps を省略したまま定常運用する（既定 pages=10 のままになる）
```

---

## 6. Human 登録チェックリスト

実登録の実行主体は **Human**。本Task（#1813）の AI は登録・live を行っていない。

| No | 確認 | 担当 |
| --: | ---- | ---- |
| 1 | PC / WSL が登録時刻に起動・ネットワーク接続できる | Human |
| 2 | リポジトリパス・実行ユーザが crontab 行と一致する | Human |
| 3 | `.env` に必要な環境変数名が揃っている（値は docs に書かない） | Human |
| 4 | `RAKUTEN_EXPECTED_EGRESS_IP` 等が運用方針どおり設定されている | Human |
| 5 | crontab は親シェル2行のみ（個別 Batch cron なし） | Human |
| 6 | `--live-rakuten` / `--pages-per-run=60` / `--max-qps 1` / `--ranking-genre-ids 100005` が明示されている | Human |
| 7 | 日曜は weekly のみ（daily と二重起動しない） | Human |
| 8 | ジャンル1本ローテの運用（誰がいつ `--genre-ids` を更新するか）を決めた | Human |
| 9 | `crontab -l` で意図どおりであること | Human |
| 10 | 登録済みである旨を Issue / 後続 verify 着手記録に残す | Human |

---

## 7. ログパスと失敗時の見方

| 種別 | パス（相対: リポジトリルート） |
| ---- | ------------------------------ |
| cron 標準出力/エラー（例） | `scripts/batch/output-local-orchestrator/cron-daily.log` / `cron-weekly.log` |
| 親シェル Run ログ | `scripts/batch/output-local-orchestrator/local-daily-*.log` / `local-weekly-*.log` |
| flock | `scripts/batch/output-local-orchestrator/locks/`（`local-rakuten-live.lock` 等） |

失敗時の見方（概要）:

1. cron ログ末尾で親シェルの exit と段名を確認する
2. 当該 `local-*-*.log` で失敗段・`pipeline_batch_run_id` を確認する
3. `rate_limited` / egress 不一致 / 同時 live 検知なら、追加の楽天 live を開始しない（[楽天Fetch運用方針](./楽天Fetch運用方針.md) / 親シェル手順 §5）
4. 再開は親シェルの `--from-step` / `--pipeline-batch-run-id`（設計手順 §5）。葉を単独で並列 live しない

`output-local-orchestrator/` は gitignored（`scripts/batch/output-*/`）。

---

## 8. 後続 `cron-ops-verify` の着手条件

後続 Task（`task-batch-local-cron-phase1-cron-ops-verify`）は、次を満たしてから着手する。

| No | 条件 |
| --: | ---- |
| 1 | 本手順（#1813）が親Epic Branch へ反映済み |
| 2 | Human が実 crontab を登録済み（§6 チェックリスト） |
| 3 | Human による登録済み記録がある（Issue コメント等） |
| 4 | 観測期間の `--live-rakuten` 実行主体は Human（AI は記録同期のみ） |

本Task完了時点では **実 crontab 未登録**が正しい（AI が登録していない）。

---

## 9. 関連資料

| 資料 | 用途 |
| ---- | ---- |
| [2026-08-01-batch-local-cron-ops-next](../../../ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md) | 次本線・定常ノブ Decision |
| [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) | 親シェル設計・§7 crontab 例 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) | QPS・egress・同時 live |
| [batch-data-collect-ops_local継続収集結果_1808](./batch-data-collect-ops_local継続収集結果_1808.md) | 段階4ノブ・ジャンルローテ実績 |
| [scripts/batch/README.md](../../../scripts/batch/README.md) | 親シェル起動例 |

---

## 10. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版（#1813）。Phase1 crontab 運用手順・定常ノブ・Human 登録チェックリスト・verify 着手条件 |
