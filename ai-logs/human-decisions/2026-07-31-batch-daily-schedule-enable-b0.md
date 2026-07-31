# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-31-batch-daily-schedule-enable-b0` |
| Log種別 | `human-decision` |
| 件名 | daily schedule有効化（案B）の採否 — 慎重案（B-0） |
| 発生日時 | 2026-07-31 |
| 記録日時 | 2026-07-31 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-daily-schedule-enable/schedule-decision.yaml` |
| 関連Issue | #1791（本Decision） / #1789（本線#5） / #1745（統括） / #1732（吸収元・CLOSED） / #1792（有効化・延期） |
| 前提 | [親workflow_daily_schedule案B再判断材料](../../docs/15_運用・改善/運用手順/親workflow_daily_schedule案B再判断材料.md) / daily D1再検証PASS / Slack失敗通知E2E完了 |
| 重要度 | `high` |
| 状態 | `decided` |

---

## 2. 結論

案B再判断材料 §8 の Human判断ゲートについて、**慎重案**を採択する。

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | B-0 vs B-1 | **B-0（schedule無効継続）**。監視/rollback最小手順とScaffold定期の目的・期限を整備したうえで、別Decisionにより B-1 を再判断する |
| 2 | #1607未完了・Scaffold前提の定期運用 | **無期限の許容はしない**。現状は schedule 無効のため定期取込自体を開始しない。将来の期限付き試行（B-1）を検討する場合も、「本番取込」ではなく「親orchestrator定期健全性確認」に限定する |
| 3 | 監視・rollback・通知準備 | **現状のままでは不十分**。失敗通知経路は確認済みだが、判定・停止・復旧・汚染方針が未整備。最小手順docsを整備してから B-1 再判断の前提とする |
| 4 | weekly同時（B-2） | **不採用**（案B材料どおり非推奨を維持） |
| 5 | `on.schedule` コメント解除 | **本Decisionでは実施しない**。B-1 再採択後も、別PR・Human明示承認が必須 |

---

## 3. 運用上の境界

- B-0 は「永久に schedule しない」ではない。**いま有効化しない**決定であり、再判断条件を明示する。
- B-1 再判断の前提（最低）:
  1. [親workflow_daily_schedule監視・rollback最小手順](../../docs/15_運用・改善/運用手順/親workflow_daily_schedule監視・rollback最小手順.md) が存在する
  2. Scaffold定期の目的・期限・禁止事項（GHA楽天live禁止維持）が Decision または同手順に書かれている
  3. あらためて B-1 の Human Decision Log が `decided` になる
  4. scheduleコメント解除は別PRで Human明示承認する
- GHA楽天HTTP live・#1607実装・weekly schedule・secret変更は本決定に含めない。
- #1792（daily on.schedule有効化）は B-1 再採択まで着手しない。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1791 | 本Decision Log・案B材料・ギャップ一覧同期・監視/rollback最小手順追加 | 実施対象 |
| #1792 | daily on.schedule有効化 | **延期**（B-1再採択後） |
| #1789 | Epic完了条件の解釈: B-0採択でも Decision Log 完了は満たす。schedule有効化は B-1時のみ | 運用中 |
| B-1再判断 | 最小手順整備後に Human が再判断 | 未決 |
| #1607 | 本番egress。本Decision外 | Backlog |

---

## 5. 参照

- `docs/15_運用・改善/運用手順/親workflow_daily_schedule案B再判断材料.md`
- `docs/15_運用・改善/運用手順/親workflow_daily再検証結果_D1.md`
- `docs/15_運用・改善/運用手順/親workflow_Slack失敗通知E2E結果.md`
- `docs/15_運用・改善/運用手順/親workflow_daily_schedule監視・rollback最小手順.md`
- `docs/05_アプリケーション設計/アプリ/batch/バッチ親workflow_schedule有効化ギャップ一覧.md`
- Issue #1789 / #1791 / #1792 / #1745 / #1732
