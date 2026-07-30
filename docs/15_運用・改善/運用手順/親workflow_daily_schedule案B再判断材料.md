# 親workflow daily schedule 案B 再判断材料

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | #1732 Wave（案B再判断）Human判断材料 正本（docs） |
| 対象 | `batch-daily-orchestrator.yml` の `on.schedule` 有効化（案B）可否判断 |
| 作成日 | 2026-07-30 |
| 関連 Epic | [#1732](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1732)（batch-parent-schedule-phase2） |
| 関連 Task | [#1733](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1733) / [#1735](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1735) / [#1739](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1739) / [#1742](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1742) |
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
| daily D1 初回検証 | **PARTIAL**（Run 30358450150、BATCH-017 failure） | 事実 |
| daily D1 再検証 | **PASS**（Run 30509052971、親全体 success、BATCH-017 success） | 事実 |
| import 連鎖 GHA live（003→…→017） | #1717 で **成功**（Run 30389689202、`item_import` 緑） | 事実 |
| Slack 失敗通知配線 | #1730 で daily/weekly に配線済み | 事実 |
| Slack 失敗通知 E2E | #1735 / #1739 で GHA **PASS**。開発運用・システムエラー通知両チャンネルの UI 到達を Human 確認済み | 事実 / Human確認 |
| cron JST 00:30 同期 | docs・YAMLコメントを `30 15`（UTC）へ同期済み。schedule は無効 | 事実 |
| weekly / manual 親の実ランタイム検証 | **未実施** | 事実 |
| 楽天API本番 egress（#1607） | GHA では live 楽天禁止。Scaffold 経路のみ | 事実 |
| meaning 葉（009–015）live | 未実施（#1726 は 017 UUID/ensure まで） | 事実 |

**現在地（事実 + 推論）:** 案B再判断前の high 技術検証（Slack E2E / daily 親 D1 再実行）は完了した。案Bを自動採用せず、Scaffold 定期取込・監視・rollback・コストを Human が判断する段階である。

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
- #1742 で daily 親 D1 を再実行し、親 conclusion **success**、`item_import / import_summary`（BATCH-017）**success**、meaning-generation・distribution_metricsまで全 job success を確認（Run 30509052971）。

### 4.3 再検証の判定（事実 + 推論）

- **事実:** daily 親 D1 再検証は **PASS**。初回 PARTIAL の blocker だった BATCH-017 failure は再現しなかった。
- **事実:** `run_retry_after=false` のため retry は skipped、failure がないため `notify_failure` は skipped。
- **推論:** 親本線の単回実行安定性は確認できた。ただし cron の長期連続運転、#1607 完了後の楽天 live、Scaffold データ蓄積上限は未確認。

詳細: [親workflow daily 再検証結果（D1）](./親workflow_daily再検証結果_D1.md)

---

## 5. 依存・前提（事実）

| 前提 | 内容 | 区分 |
| ---- | ---- | ---- |
| 楽天API本番 egress | GHA 登録 egress IP 外のため **GHA 上の楽天 live は禁止**。003 は Scaffold。実楽天疎通は local/WSL のみ。固定 egress は [#1607](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1607)（Backlog） | 事実 |
| Environment `stg` | Run 30509052971 は Human 承認操作なしに全 job が進行。cron 起動時の挙動は未確認 | 事実 / 未確認 |
| Slack 失敗通知 | #1735 / #1739 で GHA PASS。開発運用・システムエラー通知両チャンネルの UI 到達を Human 確認済み | 事実 / Human確認 |
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
| Slack / 通知 | 失敗通知の送信回数は失敗頻度に依存。#1735 / #1739 で経路・通知先分離確認済み。運用コストの定量は未計測 | 事実 / 未確認 |
| #1607 完了後 | 本番 egress 後に live 取込へ切り替えると外部 API 課金・実行時間が変わりうる。案B採否とは別ゲート | 推論 |

**含意（推論）:** 現状（Scaffold 前提）では外部 API 課金リスクは低い一方、GHA 定期実行と Scaffold データの蓄積コストは残る。金額閾値や許容上限は Human 判断事項とする。

---

## 6. 案B採用前の検証状況（事実 + 推論）

| 優先 | 検証 | 目的 | 現状 |
| ---- | ---- | ---- | ---- |
| high | Slack 失敗通知 E2E | 失敗時に想定 channel へ通知が届くか | **#1735 / #1739 完了**（GHA / UI PASS）。詳細: [親workflow_Slack失敗通知E2E結果](./親workflow_Slack失敗通知E2E結果.md) |
| high | daily 親 D1 再実行 | BATCH-017 PARTIAL の解消を daily 親全体で確認 | **#1742 完了**（親全体 PASS）。詳細: [親workflow_daily再検証結果_D1](./親workflow_daily再検証結果_D1.md) |
| medium | weekly / manual 親 D1 相当 | weekly 固有 job（offline_evaluation 等）の実ランタイム確認 | 未実施 |
| medium | Environment 承認 × schedule 整合 | 無人 cron 時の承認待ち挙動確認 | 未確認 |
| low | 監視・rollback 手順 | 定期失敗時の検知・停止（schedule 再コメントアウト）手順の明文化 | 未整備 |

---

## 7. 選択肢と推奨（Human判断）

| 案 | 内容 | メリット | デメリット / リスク |
| -- | ---- | -------- | ------------------- |
| **B-0** | schedule 無効を継続し、監視・rollback・Scaffold蓄積方針を先に整備 | 運用前提を固めてから開始できる | daily 定期運用の開始が先送り |
| **B-1** | Human明示承認後、daily scheduleのみ有効化（weeklyは無効維持） | high技術検証を満たした状態で設計 §16.2 へ進める | Scaffold定期取込・監視・rollbackの受容判断が必要 |
| **B-2** | weeklyも同時に有効化 | 早期に全定期運用 | weekly D1未実施のため **非推奨** |

**推奨（推論）:** high技術検証は完了したため、次は Human 判断ゲート。Scaffold定期取込・監視・rollbackを許容できる場合は B-1、未整備なら B-0を継続する。AIは採否を確定しない。

---

## 8. Human判断ゲート

以下は Human が確定する（AI は確定しない）。

1. high 技術検証完了を踏まえ、B-1（daily schedule 有効化）へ進むか、B-0（無効継続）とするか。
2. #1607（本番 egress）未完了・**Scaffold 前提のまま定期運用**を許容するか。
3. Slack 失敗通知の実送信・メンション運用、監視・rollback 手順の準備で十分か。
4. **`on.schedule` のコメント解除（= 定期開始）は、本ゲート通過後に別 PR で Human 明示承認のもと実施する。**

> production / 定期実行の最終承認は Human 専任。本書および #1732 は無承認の定期開始を含まない（#1637 out_of_scope を継承）。

---

## 9. 後続 Task 候補（#1732 配下）

| 候補 | 種別 | 内容 |
| ---- | ---- | ---- |
| Slack 失敗通知 E2E / 通知先分離 | test / chore | **#1735 / #1739 完了**（GHA / UI確認済み） |
| daily 親 D1 再実行 | test | **#1742 完了**（親全体 PASS、BATCH-017 success） |
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
| 2026-07-30 | #1735 Slack失敗通知E2E結果を反映（GHA PASS / UIはHuman確認） |
| 2026-07-30 | #1739 通知先分離UI確認・#1742 daily親D1再検証PASSを反映。high技術検証完了 |
