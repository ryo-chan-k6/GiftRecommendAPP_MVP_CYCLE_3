# local cron Phase2 dry-run 検証結果

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順・検証記録正本（Phase2 dry-run） |
| 作成日 | 2026-08-02 |
| 関連Issue | [#1824](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1824)（本記録） / 実装 [#1822](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1822) / 親Epic [#1818](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1818) |
| 設計正本 | [local薄いオーケストレータ設計・運用手順](./local薄いオーケストレータ設計・運用手順.md) §11〜§15 |
| Phase1 crontab 正本 | [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) |
| 状態 | dry-run 双方モード検証済み。**実 crontab 載せ替え（cron-cutover）は Human ゲート・未実施** |

secret・token・APIキー・egress IP・接続文字列の実値は記載しない。
本記録は `--dry-run` のみ。`--live-rakuten` / 実 Batch live / 実 crontab 変更は含まない。

---

## 2. 目的と非目的

### 2.1 目的

- Phase2 配線（BATCH-009〜016）の `--dry-run` 結果を再現可能に残す
- Phase1 互換スキップ（既定 / `--run-meaning` なし）を確認する
- 後続 cron-cutover（Human）の判断材料を揃える

### 2.2 非目的（out of scope）

| 対象 | 扱い |
| ---- | ---- |
| 実 crontab 変更・載せ替え | **cron-cutover / Human ゲート**。本記録では実施しない |
| AI による `--live-rakuten` / 実 Batch live | **禁止**（実施していない） |
| BATCH-018 / 019 | 対象外 |
| #1792 schedule 有効化 / #1607 / GHA 楽天 live | 対象外 |
| Phase1 #1811 の再開・完了扱い | 対象外 |

---

## 3. 実行条件（事実）

| 項目 | 内容 |
| ---- | ---- |
| 実行日 | 2026-08-02 |
| 実行主体 | AI Agent（Worker / okuri-ai-bot 作業ブランチ上） |
| 作業 Branch | `test/task-1824-phase2-dry-run-verify`（base: `chore/epic-1818-batch-local-cron-phase2`、#1823 MERGED 取り込み済み） |
| 作業ディレクトリ | Task worktree（リポジトリルート相当） |
| モード | `--dry-run` のみ（`live_rakuten=0`） |
| 既定ノブ | `genre_ids=100005` / `ranking_genre_ids=100005` / `pages_per_run=10` / `max_items=100`（dry-run 既定） |

再現コマンド（リポジトリルート）:

```bash
# Phase1 互換スキップ（既定。009〜016 を走らない）
./scripts/batch/local_daily_orchestrator.sh --dry-run
./scripts/batch/local_weekly_orchestrator.sh --dry-run

# Phase2 配線 ON（009〜016 も含む dry-run。live ではない）
./scripts/batch/local_daily_orchestrator.sh --dry-run --run-meaning
./scripts/batch/local_weekly_orchestrator.sh --dry-run --run-meaning
```

---

## 4. 結果サマリ（事実）

| # | コマンド | `run_meaning` | exit | 結果 |
| -: | -------- | ------------: | ---: | ---- |
| 1 | `local_daily_orchestrator.sh --dry-run` | 0 | 0 | SUCCEEDED。meaning / distribution_metrics を skip |
| 2 | `local_daily_orchestrator.sh --dry-run --run-meaning` | 1 | 0 | SUCCEEDED。009〜015(+017 meaning) → 016 まで STEP ok |
| 3 | `local_weekly_orchestrator.sh --dry-run` | 0 | 0 | SUCCEEDED。meaning / distribution_metrics を skip |
| 4 | `local_weekly_orchestrator.sh --dry-run --run-meaning` | 1 | 0 | SUCCEEDED。existing 連鎖後に 009〜016 まで STEP ok |

共通確認:

- 本線 flock の取得・解放ログあり（`local-batch-mainline.lock`）
- 各 STEP は `STEP ok (dry-run)`（実 Python Batch / 楽天 HTTP は未実行）
- ログに secret / token / 接続文字列実値は含まれない

---

## 5. 段順序（事実）

### 5.1 local-daily — Phase1 互換スキップ

順序（すべて dry-run ok）:

1. `ranking_snapshot`
2. import 連鎖: `item_pseudo_diff` → `raw_staging` → `product_diff` → `item_apply` → `item_active_status` → `import_summary`
3. `skip meaning chain (Phase1 compat; pass --run-meaning to enable BATCH-009〜016)`
4. `skip distribution_metrics (Phase1 compat; requires --run-meaning)`

### 5.2 local-daily — Phase2 ON（`--run-meaning`）

§5.1 の 1〜2 の後に続き:

1. meaning 連鎖: `item_generation_queue` → `item_semantic` → `feature_input_hash` → `item_feature` → `feature_normalization` → `embedding_input_hash` → `item_embedding` → `meaning_summary`
2. `distribution_metrics`

### 5.3 local-weekly — Phase1 互換スキップ

順序（すべて dry-run ok）:

1. `genre_sync` → `ranking_snapshot`
2. import 連鎖（§5.1 と同型）
3. existing 連鎖: `item_recheck` → import 連鎖再実行
4. meaning / distribution_metrics を skip（§5.1 と同メッセージ）

### 5.4 local-weekly — Phase2 ON（`--run-meaning`）

§5.3 の 1〜3 の後に続き:

1. meaning 連鎖（§5.2 と同型）
2. `distribution_metrics`

---

## 6. cron-cutover 着手条件（再確認）

| 条件 | 内容 |
| ---- | ---- |
| 着手条件 | Phase1 観測完了 **または** Human 明示承認 |
| 実施者 | **Human**（AI は実 crontab を変更しない） |
| 想定内容 | 観測用 cron 行へ `--run-meaning` を追加する等。Phase1 ノブ・親シェル経由・個別 cron 禁止を維持 |
| 本 Task の状態 | dry-run 材料は揃った。**載せ替え判断・実施は後続 cron-cutover / Human** |

詳細は設計正本 §14 / §15.3、および [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) を正とする。

---

## 7. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-02 | #1824。daily/weekly ×（既定 skip / `--run-meaning`）の dry-run 結果を本記録として追加 |
