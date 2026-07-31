# 親workflow daily schedule 監視・rollback最小手順

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 運用手順（最小・試行前ゲート） |
| 対象 | `batch-daily-orchestrator.yml` の daily `on.schedule`（将来の B-1 試行向け） |
| 作成日 | 2026-07-31 |
| 関連 | #1789 / #1791 / [Decision Log 2026-07-31-b0](../../../ai-logs/human-decisions/2026-07-31-batch-daily-schedule-enable-b0.md) |
| 現状 | **scheduleは無効（B-0）**。本手順は B-1 再判断前の最低ライン |

secret / token / channel ID / 接続文字列の実値は記載しない。

---

## 2. 目的と非目的

### 2.1 目的（B-1を将来採択する場合）

- 親orchestratorの**定期健全性**を確認する（失敗通知・concurrency・無人起動の学習）
- 失敗時に **止める・切り分ける・戻す** 担当と手順を曖昧にしない

### 2.2 非目的

- 楽天本番相当データの自動収集（GHA楽天HTTP liveは禁止。#1607未完了）
- weekly schedule の運用
- 無期限の Scaffold 定期取込

---

## 3. Scaffold定期の方針（B-1試行時）

| 項目 | 方針 |
| ---- | ---- |
| 位置づけ | 本番取込ではなく、親workflow定期健全性の試行 |
| 期間 | **期限付き**（例: 最大2週間、または連続成功 N 回）。期限は B-1 Decision Log で確定する |
| 量 | 低 `max_items` を維持できる設定を優先 |
| 禁止 | GHAからの楽天HTTP live、#1607未充足での本番相当egress前提化 |
| 終了 | 期限到達・連続失敗・容量懸念で **B-0へ戻す**（schedule再無効化） |

現状（B-0）では定期取込自体を開始しない。

---

## 4. 監視（最小）

| 観点 | やり方 |
| ---- | ---- |
| 検知 | daily親が failure / cancelled のとき、失敗通知（SYSTEM_ALERTS）を見る |
| 初回週 | B-1開始後の最初の数回は Human が Actions 一覧を確認する |
| Environment | 初回cron前後で、葉jobが承認待ちで止まっていないかを1回確認する |
| 記録 | 連続失敗・停止判断は Issueコメントまたは運用結果docsへ（secretなし） |

閾値の初期案（HumanがB-1 Decisionで確定してよい）:

- **連続 failure 2回** → schedule無効化（rollback）を開始する
- 単発 failure → 原因切り分け（手動 `workflow_dispatch`）し、再発なら停止判断

---

## 5. rollback（schedule再無効化）

1. `batch-daily-orchestrator.yml` の `on.schedule` を再度コメントアウトする PR を作成する（baseは当時の運用Branch / `develop`方針に従う）
2. PR本文に「B-0へ戻す」「理由（連続失敗 / 期限到達 / 容量懸念等）」を書く
3. Human Review / merge 後、Actionsに不要な再発火がないことを確認する
4. 必要なら手動 `workflow_dispatch` で切り分けを続ける（scheduleは無効のまま）

担当: Human（merge判断）。AIは rollback PR の下書きまで可。mergeは Human。

---

## 6. 復旧

1. 失敗jobのログを確認（secretを転記しない）
2. 低 `max_items` の手動 dispatch で再現・修正確認
3. 安定を確認してから、**別Decision**で B-1再開可否を判断する（自動再開しない）

---

## 7. 汚染・蓄積

- Scaffoldデータの無制限蓄積は避ける
- B-1試行終了時に、stgの不要行・ログの扱いを Human が判断する（本手順では削除コマンドを定めない）

---

## 8. B-1再判断チェックリスト

- [ ] 本手順を読んだ
- [ ] Scaffold定期の目的・期限案を決めた
- [ ] 連続失敗時の停止担当を決めた
- [ ] GHA楽天liveを開かないことを再確認した
- [ ] 新しい Human Decision Log で B-1 を採択する（本B-0 Logの上書きではない）

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-31 | 初版（#1791 / B-0慎重案の整備物） |
