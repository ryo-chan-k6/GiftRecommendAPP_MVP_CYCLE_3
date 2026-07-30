# 親workflow daily schedule 案B 再判断材料

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | #1732 Wave（案B再判断）Human判断材料 正本（docs） |
| 対象 | `batch-daily-orchestrator.yml` の `on.schedule` 有効化（案B）可否判断 |
| 作成日 | 2026-07-30 |
| 関連 Epic | [#1732](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1732)（batch-parent-schedule-phase2） |
| 関連 Task | [#1733](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1733) |
| 先行 Epic | [#1637](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1637)（案A完了。schedule 無効維持） |

### 1.1 目的

Epic #1637（案A）完了後に残る「daily schedule 有効化（案B）」の可否を、Human が根拠付きで判断できるよう、事実・残リスク・選択肢・判断ゲートを1箇所に正本化する。

**本 Task では `on.schedule` のコメント解除・production 定期開始は行わない。**

### 1.2 区分（本書の記法）

| 区分 | 意味 |
| ---- | ---- |
| 事実 | 正本 docs・YAML・Issue・PR・Run から確認できる内容 |
| 推論 | 事実から導いた解釈・影響・推奨（断定しない） |
| 未確認 | 現時点で確認できていない内容 |
| Human判断 | Human が確定する事項 |

---

## 2. 30秒サマリ

| 観点 | 状態 | 区分 |
| ---- | ---- | ---- |
| 案A（schedule 無効維持） | #1637 で完了・merge 済み（PR #1731） | 事実 |
| daily D1 手動検証 | **PARTIAL**（親 conclusion=failure、失敗は BATCH-017 step） | 事実 |
| import 連鎖 GHA live（003→…→017） | #1717 で **成功**（Run 30389689202、`item_import` 緑） | 事実 |
| Slack 失敗通知配線 | #1730 で daily/weekly に配線済み。**実送信は未確認** | 事実 / 未確認 |
| cron JST 00:30 同期 | docs・YAMLコメントを `30 15`（UTC）へ同期済み。schedule は無効 | 事実 |
| weekly / manual 親の実ランタイム検証 | **未実施** | 事実 |
| 楽天API本番 egress（#1607） | GHA では live 楽天禁止。Scaffold 経路のみ | 事実 |
| meaning 葉（009–015）live | 未実施（#1726 は 017 UUID/ensure まで） | 事実 |

**推奨（推論）:** 案B（daily schedule 有効化）は現時点で**採用せず**、まず §6 の追加検証（Slack E2E・BATCH-017 の PARTIAL 解消確認・weekly/manual D1）を実施してから再判断するのが安全。

---

## 3. 対象と現状（事実）

### 3.1 daily 親 workflow の現状

出典: `.github/workflows/batch-daily-orchestrator.yml`

| 項目 | 現状 |
| ---- | ---- |
| `on.schedule` | **コメントアウト（無効）**。`# - cron: "30 15 * * 0-5"`（JST 月〜土 00:30） |
| `workflow_dispatch` | あり（`max_items` / `run_retry_after`） |
| concurrency | `group: batch-mainline` / `cancel-in-progress: false` |
| permissions | `contents: read` / `actions: write` |
| 失敗通知 | `notify_failure` job あり（#1730、Slack 通知） |
| jobs 連鎖 | `ranking_snapshot → item_import → item_meaning_generation → distribution_metrics →（retry_failed_items）` |

### 3.2 正本 Phase 方針

出典: [バッチ実行スケジュール設計書](../../05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) §16

| Phase | 内容 |
| ----- | ---- |
| 1 | 親 `on.schedule` 無効。`workflow_dispatch` で検証（**案A = 現状**） |
| 2 | **daily** cron 有効化（基本処理安定後）（**案B = 本書の判断対象**） |
| 3 | weekly cron 有効化 |
| 4 | 018/019 / manual シナリオ（本線外） |

---

## 4. D1（daily 手動検証）の結果と残課題（事実 + 推論）

出典: [親workflow手動検証結果_D1](./親workflow手動検証結果_D1.md)（Run 30358450150、2026-07-28）

### 4.1 事実

- 親 `workflow_dispatch` は machine account から起動可能。`jobs.needs` 連鎖は設計どおり。
- 判定は **PARTIAL**（親 conclusion=failure）。失敗は複合子 `item_import` 内 **BATCH-017（import_summary）step**。
- 親 YAML の schedule / concurrency 自体の不具合ではない。

### 4.2 その後の進捗（事実）

- #1717（案C3）で import 連鎖 GHA live（003→…→017）が **成功**（Run 30389689202、017 `insert_applied=True`）。D1 当時の 017 失敗要因（scaffold demo / `batch_run_id` 前提不足）は、案A の `ensure_batch_run` 実装で解消方向。
- #1728 / #1726 で meaning-generation の 017 も pipeline `batch_run_log` ensure により UUID エラーを解消。

### 4.3 残課題（未確認）

- D1 と同条件（daily 親 `workflow_dispatch`, 低 `max_items`）での **再実行 PASS は未確認**。#1717 の検証正本は `Batch Rakuten Item Import`（複合子）であり、daily 親全体の再 PARTIAL/PASS は再測定していない。
- meaning 葉（009–015）は当面 scaffold。daily 親全体を回すと集計が空寄りになりうる（C3 メモ §6）。

---

## 5. 依存・前提（事実）

| 前提 | 内容 | 区分 |
| ---- | ---- | ---- |
| 楽天API本番 egress | GHA 登録 egress IP 外のため **GHA 上の楽天 live は禁止**。003 は Scaffold。実楽天疎通は local/WSL のみ。固定 egress は [#1607](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1607)（Backlog） | 事実 |
| Environment `stg` | 各葉 job 実行前に required reviewers による Human 承認が必要 | 事実 |
| Slack 失敗通知 | #1730 で配線済み。token/channel は Secrets/Variables 参照。**実送信・メンションの動作は未確認** | 事実 / 未確認 |
| cron 時刻 | JST 00:30 = UTC `30 15`（daily `* * 0-5` / weekly `* * 6`）。docs・YAMLコメント同期済み | 事実 |

### 5.1 案Bで schedule を有効化した場合の含意（推論）

- schedule 有効化は `stg` Environment 上でも「無人での定期起動」を意味する。楽天は Scaffold のため、定期実行しても**本番相当のデータ取込にはならない**（Scaffold データが定期で入る）。
- Environment required reviewers があると、**無人 cron 起動でも各葉 job が承認待ちで停止**する可能性がある（自動運転にならない）。→ 承認設定と schedule 有効化の整合は Human 確認が必要（未確認）。

### 5.2 コスト観点（推論 / 未確認）

案B（daily schedule 有効化）により増えうるコスト要因を整理する。**現時点で金額・回数の実測はしていない**（未確認）。

| 要因 | 内容 | 区分 |
| ---- | ---- | ---- |
| GitHub Actions 実行時間 | daily cron（月〜土）による親＋葉 workflow の定期起動。承認待ちで停止する場合は実行時間は増えないが、起動試行自体は発生しうる | 推論 |
| 外部 API 課金 | GHA 上の楽天 live は禁止（#1607 未完了）。現状は Scaffold のため **本番相当の楽天 API 課金は発生しない** | 事実 / 推論 |
| ストレージ・DB 書込 | Scaffold データの定期取込により DB 行数・ログが増えうる。上限・保持方針の定量評価は未実施 | 推論 / 未確認 |
| Slack / 通知 | 失敗通知の送信回数は失敗頻度に依存。実送信未確認のためコスト影響も未計測 | 未確認 |
| #1607 完了後 | 本番 egress 後に live 取込へ切り替えると外部 API 課金・実行時間が変わりうる。案B採否とは別ゲート | 推論 |

**含意（推論）:** 現状（Scaffold 前提）では外部 API 課金リスクは低い一方、GHA 定期実行と Scaffold データの蓄積コストは残る。金額閾値や許容上限は Human 判断事項とする。

---

## 6. 案B採用前に推奨する追加検証（推論）

| 優先 | 検証 | 目的 | 現状 |
| ---- | ---- | ---- | ---- |
| high | Slack 失敗通知 E2E | 失敗時に想定 channel へ通知が届くか | 未実施（#1732 別 Task 候補） |
| high | daily 親 D1 再実行 | BATCH-017 PARTIAL の解消を daily 親全体で確認 | 未実施 |
| medium | weekly / manual 親 D1 相当 | weekly 固有 job（offline_evaluation 等）の実ランタイム確認 | 未実施 |
| medium | Environment 承認 × schedule 整合 | 無人 cron 時の承認待ち挙動確認 | 未確認 |
| low | 監視・rollback 手順 | 定期失敗時の検知・停止（schedule 再コメントアウト）手順の明文化 | 未整備 |

---

## 7. 選択肢と推奨（Human判断）

| 案 | 内容 | メリット | デメリット / リスク |
| -- | ---- | -------- | ------------------- |
| **B-0（推奨）** | 当面 schedule 無効のまま。§6 の high 項目（Slack E2E・daily 親 D1 再実行）を先に実施し、結果を見て再判断 | 無人失敗・空集計・承認待ちの露出を避けられる。安全 | daily 定期運用の開始が先送り |
| **B-1** | §6 完了後に daily schedule のみ有効化（weekly は無効維持） | 設計 §16.2 どおり段階的 | Scaffold 定期取込の意味・監視体制の準備が必要 |
| **B-2** | 即 daily schedule 有効化 | 早期に定期運用 | D1 PARTIAL 再確認前・Slack 未検証・承認待ち未確認のまま無人化。**非推奨** |

**推奨（推論）:** **B-0**。案B本採用（B-1）は §6 の high 検証が揃い、Human が「Scaffold データの定期取込を許容」「監視・rollback 準備済み」と判断した後が安全。

---

## 8. Human判断ゲート

以下は Human が確定する（AI は確定しない）。

1. 案B（daily schedule 有効化）を **今** 進めるか、§6 の追加検証後に再判断するか。
2. #1607（本番 egress）未完了・**Scaffold 前提のまま定期運用**を許容するか。
3. Slack 失敗通知の実送信・メンション運用、監視・rollback 手順の準備で十分か。
4. **`on.schedule` のコメント解除（= 定期開始）は、本ゲート通過後に別 PR で Human 明示承認のもと実施する。**

> production / 定期実行の最終承認は Human 専任。本書および #1732 は無承認の定期開始を含まない（#1637 out_of_scope を継承）。

---

## 9. 後続 Task 候補（#1732 配下）

| 候補 | 種別 | 内容 |
| ---- | ---- | ---- |
| Slack 失敗通知 E2E | test / chore | 失敗を意図的に発生させ、通知到達を secret なしで記録 |
| daily 親 D1 再実行 | test | BATCH-017 PARTIAL 解消を daily 親全体で確認・記録 |
| weekly / manual D1 相当 | test | weekly 固有 job の実ランタイム検証・記録 |
| （Human 承認後のみ）daily schedule 有効化 | chore | `on.schedule` コメント解除。別 PR・Human 明示承認必須 |

---

## 10. 完了条件（本 Task）

- [x] 事実・推論・未確認・Human判断点を分離して正本化
- [x] D1 PARTIAL・Slack 実送信・weekly/manual・#1607・コスト/承認・rollback を整理
- [x] 案Bの採否選択肢と推奨案を提示
- [x] Human 明示承認前に schedule 有効化しないゲートを明記
- [x] secret / token / 接続文字列実値を含まない

---

## 11. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版（#1732 / #1733 案B再判断材料） |
| 2026-07-30 | AI Review対応: §5.2 コスト観点（推論/未確認）を追記 |
