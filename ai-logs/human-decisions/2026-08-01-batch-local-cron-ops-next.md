# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-01-batch-local-cron-ops-next` |
| Log種別 | `human-decision` |
| 件名 | 本格収集(#1798)完了後の次本線: local cron 全BATCH自動運用（GHA延期） |
| 発生日時 | 2026-08-01 |
| 記録日時 | 2026-08-01 |
| 関連Issue | #1798（本線#6完了側） / #1745（統括） / #1792 / #1607（延期） / #1811（Phase1 Epic） / #1813（crontab運用手順） / #1816（曜日・時刻採択） |
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
| #1798 | Epic 完了PR（→ develop） | 完了（PR #1810 → develop） |
| Epic #1811（crontab Phase1） | 001〜008 の cron 無人運用定着 | 進行中 |
| Task #1813（cron-ops-runbook） | crontab運用手順正本化・定常ノブ同期 | 完了（実登録はHuman） |
| Task #1816（曜日・時刻） | daily=火〜日 05:00 / weekly=月曜 05:00 JST | 反映中 |
| 後続 cron-ops-verify | Human登録後の数日無人観測結果docs化 | 未着手（Human登録待ち） |
| 新規 Epic（local Phase2） | 親シェルへ 009〜016 配線・検証・cron載せ替え | 着手（設計・実装・dry-run先行。観測中のcrontab載せ替えはHumanゲート） |
| #1792 / #1607 | 先送り（本線に吸収しない） | 延期維持 |
| #1745 | 本線#6完了追跡・次本線（local cron）を本文更新 | 実施 |

---

## 5. 参照

- `docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md`（crontab運用手順正本・#1813）
- `docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md`
- `docs/15_運用・改善/運用手順/batch-data-collect-ops_local継続収集結果_1808.md`
- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- Issue #1798 / #1745 / #1792 / #1607 / #1811 / #1813 / #1816

---

## 6. Phase1 定常ノブ（#1813 同期）

#1808 段階4の通常継続を、local cron Phase1 の初期定常ノブとして採用する。
最終採択の継続/変更、および実 crontab 登録タイミングは **Human 判断点**。

| ノブ | Phase1 定常値 | 根拠 |
| ---- | ------------- | ---- |
| `pages_per_run` | **60** | 通常継続（楽天Fetch運用方針 §5.3.4 / #1808） |
| `cursors_per_run` | **1** | 同上 |
| `max_qps` | **1** | 長時間・003 安全側 |
| `--ranking-genre-ids` | **100005** | Ranking 固定（#1765） |
| `--genre-ids` | **ジャンル1本ローテ** | MVP: `100005` / `100003` / `100004` / `100000` を1本ずつ。同時複数禁止 |
| BATCH-017 | **任意** | 連鎖内。不要時は `--skip-import-summary` |
| 同時楽天 live | **禁止（常に1本）** | Decision §3 / 楽天Fetch運用方針 §6.2 |
| crontab スケジュール | **daily=火〜日 05:00 JST** / **weekly=月曜 05:00 JST** | Human 採択（#1816）。同日二重起動しない。cron 例: daily `0 5 * * 0,2-6` / weekly `0 5 * * 1`（ホスト JST 前提） |

運用手順正本: `docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md`。
実 crontab 登録・PC常時起動・観測期間の `--live-rakuten` は Human。AI は登録・live を実行しない。
