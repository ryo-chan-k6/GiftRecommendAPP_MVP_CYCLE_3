# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-01-batch-local-cron-ops-next` |
| Log種別 | `human-decision` |
| 件名 | 本格収集(#1798)完了後の次本線: local cron 全BATCH自動運用（GHA延期） |
| 発生日時 | 2026-08-01 |
| 記録日時 | 2026-08-01 |
| 関連Issue | #1798（本線#6完了側） / #1745（統括） / #1792 / #1607（延期） |
| 前提 | `2026-07-31-batch-data-collect-ops-plan` / `2026-07-31-batch-daily-schedule-enable-b0` / #1808 案A一旦終了 |
| 重要度 | `high` |
| 状態 | `decided` |

---

## 2. 結論

本線#6（#1798）のキャンペーンは **案A（一旦終了）** で打ち切る。  
次の自動運用目標は **GHA ではなく local cron** とする。

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | 実行本線 | **local cron**（PC/WSL 常時起動は Human） |
| 2 | 自動運用対象 BATCH | **001〜016**（017は連鎖内の既存方針どおり任意可） |
| 3 | 対象外 | **018 / 019**（Offline Eval / Feedback。自動運用に含めない） |
| 4 | GHA `on.schedule`（#1792 / B-1） | **先送り**（本 Decision では有効化しない） |
| 5 | 固定egress / GHA楽天live（#1607） | **先送り**（楽天 HTTP は local・登録egressのみ維持） |
| 6 | 次Epic分割 | (1) crontab + Phase1（001〜008）定常 (2) local Phase2（009〜016を親へ） |

---

## 3. 運用上の境界

- 子 Batch の個別 cron は禁止。起動は local 親シナリオ（daily / weekly）のみ。
- 楽天 live は同時1本。GHA からの楽天 HTTP live は禁止維持。
- secret 実値は docs / Issue / PR / 本Log に記載しない。
- #1798 の成果（親シェル・収集結果・§5.3.5維持）を develop 反映したうえで、上記次Epicに着手する。

---

## 4. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1798 | Epic 完了PR（→ develop） | 本Decision記録と同時進行 |
| 新規 Epic（crontab Phase1） | 001〜008 の cron 無人運用定着 | 未着手 |
| 新規 Epic（local Phase2） | 親シェルへ 009〜016 配線・検証・cron載せ替え | 未着手 |
| #1792 / #1607 | 先送り（本線に吸収しない） | 延期維持 |
| #1745 | 本線#6完了追跡・次本線（local cron）を本文更新 | 実施 |

---

## 5. 参照

- `docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md`
- `docs/15_運用・改善/運用手順/batch-data-collect-ops_local継続収集結果_1808.md`
- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- Issue #1798 / #1745 / #1792 / #1607
