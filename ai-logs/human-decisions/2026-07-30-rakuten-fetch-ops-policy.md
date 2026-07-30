# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-30-rakuten-fetch-ops-policy` |
| Log種別 | `human-decision` |
| 件名 | 楽天Fetchの取得量・Run分割・再開・実行場所に関する運用値 |
| 発生日時 | 2026-07-30 |
| 記録日時 | 2026-07-30 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-live-rakuten-fetch/rakuten-fetch-ops-decisions.yaml` |
| 関連Issue | #1764（Decision Log化） / #1763（楽天Fetch live切替） / #1749（運用方針） |
| 前提決定 | `2026-07-24-rakuten-api-qps-ip-verify-policy` / `2026-07-25-rakuten-operational-qps-revise-to-2` |
| 重要度 | `high` |
| 状態 | `decided` |

---

## 2. 結論

[楽天Fetch運用方針](../../docs/15_運用・改善/運用手順/楽天Fetch運用方針.md) §10 の推奨案を、以下のとおり採択する。

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | MVP対象ジャンル | **本Decisionでは保留**。具体的な `fetch_plan` は local live 実行前にHuman承認する |
| 2 | BATCH-003カタログ深さ | **事業上の取得打ち切り上限を設けない**。承認済みスコープを継続取得し、範囲完了時のみ `exhausted` とする |
| 2b | BATCH-003 Run予算 | 通常継続は `pages_per_run=60` / `cursors_per_run=1` / route 1本 / `hits=30` / 45分。立ち上げは10ページから段階拡張する |
| 2c | 監視閾値 | 運用方針 §5.3.5 の比率・増分・エラー率ベース初期値を採択し、運用開始1週間後に実測で見直す |
| 3 | BATCH-004件数 | **100件から開始**し、3回連続正常後に最大1000件/週まで段階拡張する |
| 4 | Run分割 | **route・cursor単位**。BATCH-003はRun予算到達後もpositionを保持して次回継続する |
| 5 | `paused` 再開 | **手動再開**。初回は15分以上のクールダウンと原因確認後に `active` へ戻す |
| 6 | `failed` 再開 | **手動再開**。原因解消・再実行安全性確認後に `active` へ戻す |
| 7 | GHA楽天live | **当面localのみ**。GitHub-hosted runnerから楽天HTTPを呼ばない。#1607を本Epicへ吸収しない |
| 8 | 安全側QPS=1 | **長時間Run、BATCH-003/004、429後の再開時のみ**適用する。常用QPS=2は変更しない |
| 9 | クールダウン | **初回15分、再発時60分以上**。同一Runでの無限再試行は行わない |

---

## 3. 運用上の境界

- No.1の保留は「対象ジャンルを無制限にする」という意味ではない。local live 実行前に、最小 `fetch_plan` をHumanが承認する。
- Run予算は1 Runの進行量・時間を制限するものであり、BATCH-003のカタログ深さを恒久的に打ち切る値ではない。
- `max_items` は親workflowから後続Batchへ渡す処理件数であり、楽天FetchのRun予算とは別物である。
- 閾値超過時はRun予算・頻度・対象範囲・安全側QPSを調整し、Human明示判断なしに恒久打ち切りへ変更しない。
- GHA楽天live、#1607、本番定期実行、schedule有効化、secret変更は本決定に含めない。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1764 | 本Decision Logと楽天Fetch運用方針・ギャップ一覧を同期 | 実施対象 |
| #1765 | 採択値に沿ってBATCH-001〜004 local liveを実装・検証 | #1764完了後 |
| local live開始前 | MVP対象ジャンルの具体的 `fetch_plan` をHuman承認 | 未決・実行ゲート |
| 運用開始1週間後 | Run予算・監視閾値を実測で見直す | 後続 |
| #1607 / schedule | 本番egress・GHA楽天live・定期実行を別Issueで判断 | 本Task外 |

---

## 5. 参照

- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- `ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md`
- `ai-logs/human-decisions/2026-07-25-rakuten-operational-qps-revise-to-2.md`
- Issue #1763 / #1764 / #1765
