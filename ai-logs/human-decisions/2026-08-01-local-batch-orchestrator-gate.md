# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-01-local-batch-orchestrator-gate` |
| Log種別 | `human-decision` |
| 件名 | local薄いオーケストレータ導入ゲート（Issue分割・Phase1範囲・cron境界・allowed_paths・#1801停止） |
| 発生日時 | 2026-08-01 |
| 記録日時 | 2026-08-01 |
| 発生元Command | 人間依頼（Issue計画承認）→ Orchestrator AI |
| 関連Issue | #1798（親Epic・本線#6） / #1801（local継続収集） / #1745（統括） |
| 前提決定 | `2026-07-31-batch-data-collect-ops-plan` / `2026-07-30-rakuten-fetch-ops-policy` / `2026-07-31-batch-daily-schedule-enable-b0` |
| 重要度 | `high` |
| 状態 | `decided` |

本Logは、B-0下で楽天APIを登録 egress IP の local から本格収集するにあたり、
「GHA相当をローカルで薄く再現」する方針の Human ゲート採択を正本化する。
実装本体・収集実行・schedule有効化・#1607・secret変更は含めない。

---

## 2. 結論

推奨案をすべて採択する。

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | Issue分割 | **NEW-A（設計）と NEW-B（実装）を #1801 から分離**する。#1801 に吸収しない |
| 2 | Phase1再現範囲 | **楽天Fetch本線中心**（BATCH-001〜004。必要なら import 連鎖 005〜008 まで）。BATCH-009〜015（意味生成）は Phase1 に含めない |
| 3 | cronの成果物境界 | **親シェルスクリプト＋運用手順（crontab例含む）まで**を Issue 成果物とする。**実 crontab 登録・PC常時起動は Human** |
| 4 | Epic `allowed_paths` | `#1798` に **`scripts/batch/**` を追加**する |
| 5 | #1801 の扱い | NEW-B 完了まで **収集実行の本作業は停止**（PR未作成維持）。Planned Start / 依存をオーケストレータ実装完了後へ更新する |

### 2.1 実行制御の方針（確認）

| 項目 | 決定 |
| ---- | ---- |
| 起動 | OS cron または手動は **親シナリオ 1〜2 本**（日次相当 / 週次相当）。子 Batch の個別 cron は禁止 |
| 順序 | GHA `jobs.needs` 相当を **親シェルの直列実行**で再現。失敗時は後続停止 |
| 排他 | `flock` 等で本線ロック＋**楽天 live 横断 1 本** |
| Run ID | `pipeline_batch_run_id` を親で生成し各段へ伝播 |
| 本格ジョブ基盤 | Airflow / Prefect 等は **導入しない**（本ゲート範囲外・非採用） |
| #1607 / GHA楽天live / schedule有効化 | **本ゲート外**（既存どおり out of scope） |

---

## 3. 運用上の境界

- 本ゲートは **#1798 配下の Task 追加・順序変更**に限定する。新規本線 Epic は作らない。
- 楽天 HTTP live は local / 登録 egress IP のみ。GHA からの楽天 live は禁止を維持する。
- secret・接続文字列・token 実値は docs / Issue / PR / 本Log に記載しない。
- チャット上の同意だけでは正本とせず、本Log（`decided`）と Definition / Issue 反映を正本とする。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| Task Definition | `local-orchestrator-design` / `local-orchestrator-impl` 追加 | 本Logと同時に実施 |
| Epic Definition #1798 | `scripts/batch/**` を allowed_paths に追加。子Task候補を更新 | 本Logと同時に実施 |
| #1801 Definition / Issue | 依存に impl Task を追加。Planned Start を後ろ倒し。オーケストレータ経由収集を scope に明記 | 本Logと同時に実施 |
| `/start-task` | design → impl の順で Issue / Branch 作成 | 本Log後 |
| #1745 | 本線#6追跡にオーケストレータ Task 差し込みを反映 | 本Log後 |
| #1792 / #1607 / GHA楽天live | 対象外 | 対象外 |

---

## 5. 参照

- `docs/05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md`
- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- `ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md`
- `scripts/batch/README.md`
- Issue #1798 / #1801 / #1745
