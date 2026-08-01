# batch-data-collect-ops local継続収集結果（#1801）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1801（親Epic #1798 / 統括 #1745） |
| 関連PR | #1807 |
| 前提Decision | [本格収集運用枠](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) / [オーケストレータ導入ゲート](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md) / [fetch_plan](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) |
| 記録日 | 2026-08-01 |
| 実行経路 | `scripts/batch/local_daily_orchestrator.sh --live-rakuten`（個別CLI本線化なし） |
| 段階 | 段階1（開始）。Humanにより Planned Start（2026-08-05）前の早期着手を承認 |

secret・token・APIキー・egress IP・`DATABASE_URL`・Object Storage 実値は本ドキュメントに含めない。

---

## 2. 着手ゲート

| ゲート | 結果 |
| ------ | ---- |
| 運用枠 Decision decided | 充足 |
| local-orchestrator-impl（#1804 / PR #1806）親Epic反映 | 充足 |
| egress IP 照合 | MATCH（値は非記載） |
| worktree `.env` | メイン `.env` への symlink（gitignore） |
| 早期 live 開始 | Human 承認（2026-08-01） |

---

## 3. 親シェル最小修正（収集阻害解消）

| 項目 | 内容 |
| ---- | ---- |
| 背景 | 親シェルが `--genre-ids` を渡さず、BATCH-002 既定 `100` / 未指定で Ranking 失敗 |
| 既知事実（#1765） | Ranking API は `100000`/`100003`/`100004` が HTTP 400。`100005` は成功 |
| 対応 | `scripts/batch` に `--genre-ids`（既定 `100005`）・`--no-update-sort`（既定オン）・`--max-qps` を追加し、002/003（および weekly の 001）へ伝播 |

---

## 4. Run記録

### 4.1 失敗 Run（genre未指定）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:25 JST 付近 |
| `pipeline_batch_run_id` | `fa67f2b8-406a-40dc-bdc5-07435f2cf122` |
| 結果 | FAILED at `ranking_snapshot` |
| 観測 | BATCH-002 `failed=1`。後続停止（設計どおり） |
| 原因 | Ranking 対象ジャンル不正（親シェルが genre 未伝播） |

### 4.2 段階1 Run（genre=100005）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:41 JST 付近 |
| `pipeline_batch_run_id` | `64676aae-be0a-4409-b948-7cda1de1dfbe` |
| ノブ | `pages_per_run=10` / `cursors_per_run=1` / `genre_ids=100005` / `no_update_sort=1` / `max_qps=1` |
| BATCH-002 | **succeeded**（`succeeded=1 failed=0`。`rakuten_backend=http`） |
| BATCH-003 | **failed**（`GRS-RAW-001` object storage put HTTP 400） |
| 後続 import | 未起動（失敗停止） |
| 429 | 本 Run 内では未観測。直前の `rakuten_live_verify` で ItemSearch page2 が GRS-EXT-102（初回）。15分クールダウン後に本 Run を実施 |

### 4.3 Object Storage 切り分け

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `object_storage_live_verify.py --live-object-storage` |
| 判定 | Block（put/get 失敗） |
| HTTP | 400 / 応答本文 `Project not specified.` |
| 原因（事実） | local `.env` の `OBJECT_STORAGE_ENDPOINT` が `.env.example` 系プレースホルダ（`your-project` を含む）のまま |
| 参照 | #1765 §4.6 第1回と同一症状。実プロジェクト endpoint / S3 キー投入後に解消した前例あり |

---

## 5. §5.3.5 見直し

| 項目 | 内容 |
| ---- | ---- |
| 見直し時点（運用枠） | 段階2完了、または本格収集開始から7日のどちらか早い方 |
| 現状 | 段階1未完了（BATCH-003 未成功）。見直し時点未達 |
| 暫定 | 閾値変更なし（維持）。実測レビューは Object Storage 復旧後の継続収集後に実施 |

---

## 6. 停止 / 再開

| 項目 | 内容 |
| ---- | ---- |
| 現在 | **追加の本格収集 Run を一時停止**（Object Storage 未復旧） |
| 保持 | fetch_cursor / ranking 成功分の DB 状態は破棄しない |
| 再開条件 | Human が `OBJECT_STORAGE_ENDPOINT` / Access / Secret / bucket を実プロジェクト向けに修正し、`object_storage_live_verify` が Go 相当になった後 |
| 再開コマンド例 | `./scripts/batch/local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --max-qps 1` |

---

## 7. 累計カウンタ（キャンペーン）

| 指標 | 値 |
| ---- | ---- |
| 本格収集開始日 | 2026-08-01 |
| 期間上限 | 開始から最大7日、または BATCH-003 累計 Run 20回 |
| BATCH-003 成功 Run 累計 | **0**（失敗1） |
| 段階1 進行条件 | 2〜3 Run・429なし・失敗なし・ログ追跡可能 → **未達** |

---

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版。ゲート確認・genre伝播修正・段階1試行・OSプレースホルダによる停止を記録 |
