# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-03-batch-genre-map-campaign-ops-plan` |
| Log種別 | `human-decision` |
| 件名 | 楽天ジャンル地図キャンペーンの運用枠（起点・1 Run上限・停止・定常cron非干渉・QPS・Human live境界） |
| 発生日時 | 2026-08-03 |
| 記録日時 | 2026-08-03 |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-genre-map-campaign/ops-plan-decision.yaml` |
| 関連Issue | #1829（本Decision） / #1827（親Epic） / #1811（Phase1 cron・変更しない） / #1818（Phase2・変更しない） / #1745（統括） |
| 前提決定 | `2026-07-30-rakuten-fetch-ops-policy` / `2026-07-31-rakuten-fetch-mvp-fetch-plan` / `2026-08-01-batch-local-cron-ops-next` |
| 重要度 | `high` |
| 状態 | `recommended`（Human Reviewで最終採択。採択後に `decided` へ更新） |

本Logは、Epic #1827 の着手ゲートとして、ジャンル地図キャンペーンの運用枠を正本化する。
AIは推奨案を整理するのみで、最終採択は Human とする。
live実行・定常crontab変更・#1811/#1818完了操作・secret実値は含めない。

---

## 2. 推奨案（Human採択待ち）

| No | 論点 | 推奨案 | Human採択 |
| --: | ---- | ------ | --------- |
| 1 | 起点・探索方式 | **root `0` からの BFS**。BATCH-001 は直下 `children` のみのため、未同期 children を次 Run の `--genre-ids` へ載せて段階同期する | **採択待ち** |
| 2 | 1 Run あたり genre 上限 | **20 genre**（調整可。429・時間・paused増に応じて Human が下げる） | **採択待ち** |
| 3 | QPS | **常用QPS=2は維持**。キャンペーンの BATCH-001 Run は運用方針の**安全側**に合わせ `--max-qps 1`（001向け）。**商品収集 cron（daily/weekly）と同時 live 禁止** | **採択待ち** |
| 4 | 停止条件 | 下記 §2.2。いずれかで追加キャンペーン Run を停止し Human へ通知 | **採択待ち** |
| 5 | 定常cron非干渉 | **#1811 の daily/weekly は変更しない**。キャンペーンは葉 BATCH-001 CLI（または専用ラッパ）のみ。**weekly親全体は回さない** | **採択待ち**（境界は確定推奨） |
| 6 | live実行境界 | **AIは `--live-rakuten` しない**。liveは Human のみ。GHA楽天HTTP・#1607・`on.schedule` 有効化は対象外維持 | **採択待ち**（境界は確定推奨） |
| 7 | MVP fetch_plan 4ID | **`100000` / `100003` / `100004` / `100005` は置き換えない**。ジャンル地図は後続 BATCH-002/003 計画の**拡大情報源** | **採択待ち**（境界は確定推奨） |

### 2.1 BFS 運用イメージ（推奨）

```text
1. 起点 genreId = 0 で BATCH-001 を実行（1 Run 上限内）
2. 取得した直下 children のうち、未同期（external_genre 未登録 or 未展開）をキューへ
3. 次 Run はキュー先頭から最大 20 genre を --genre-ids に載せる
4. キューが空になるか、停止条件に達するまで繰り返す
```

- BATCH-001 の仕様上、1回の同期は起点＋直下 children まで。全階層の自動総なめではない。
- 実装ラッパ・live実行本体は後続 Task（runner）。本Logは枠のみ。

### 2.2 停止条件（推奨）

以下のいずれかで **追加のキャンペーン Run を停止**し Human へ通知する。

1. **429が連続**（同一Runで再発、またはクールダウン後も再発）
2. **`paused` が増える**（campaign対象 cursor / 同期失敗相当の滞留が増加）
3. **予定 Run 消化**（Humanが事前に決めたキャンペーン Run 予算・日数・キュー消化計画の到達）
4. **Human中断**（明示停止）

加えて、既存の楽天Fetch運用方針に従い、egress不一致・secret漏えい疑い・想定外の同時楽天live検知でも即停止する。

### 2.3 実行経路（推奨）

| 経路 | キャンペーンでの扱い |
| ---- | -------------------- |
| 葉 BATCH-001 CLI | **推奨**（`--genre-ids` で BFS チャンクを明示） |
| 専用ラッパ（後続） | 可（dry-run可。weekly親を呼ばない） |
| `local_weekly_orchestrator.sh` 全体 | **禁止**（001以外の連鎖と定常ノブを巻き込む） |
| `local_daily_orchestrator.sh` | **禁止**（商品収集本線。地図キャンペーンと混在させない） |
| Phase1/Phase2 crontab 行の変更 | **禁止**（#1811 / #1818） |

### 2.4 QPS・同時実行（推奨）

| 項目 | 推奨 |
| ---- | ---- |
| 常用QPS | **2**（既存決定を変更しない） |
| キャンペーン BATCH-001 | **安全側 `max_qps=1`** |
| 同時楽天live | **常に1本**。daily/weekly 商品収集 cron の live と重ねない |
| CI / GHA 楽天live | **禁止**（既存方針維持） |

---

## 3. 運用上の境界

- 本枠は **ジャンル地図把握の別枠キャンペーン**に限定する。商品本格収集（#1798系）や定常cron（#1811/#1818）を置き換えない。
- MVP fetch_plan 4IDの承認内容（直下 children・keywordなし等）は変更しない。地図成果は後続の取得計画検討用。
- secret・接続文字列・token・APIキー実値は docs / Issue / PR / 本Log に記載しない。
- AI Agent は `--live-rakuten` を実行しない。dry-run・docs・Decision 同期のみ。
- チャット上の同意だけでは正本とせず、本Logの Human 採択（`decided`）と [楽天Fetch運用方針](../../docs/15_運用・改善/運用手順/楽天Fetch運用方針.md) 同期を正本とする。

---

## 4. Humanに決めてほしいこと

1. **root `0` BFS を採択するか**（推奨: 採択）
2. **1 Run あたり genre 上限を 20 とするか**（推奨: 20。別値なら数値を明示）
3. **§2.2 停止条件を採択するか**（追加・緩和があれば明示）

採択後は本Logの状態を `decided` に更新し、§2 表の Human採択欄を埋める。

---

## 5. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1829 | 本Decision Log・楽天Fetch運用方針同期 | 実施対象 |
| inventory（後続Task） | external_genre 棚卸し。本枠 Human採択後に大規模 live 禁止を維持したまま着手可 | 着手ゲート |
| runner（後続Task） | BFS手順または最小ラッパ（`--dry-run`可）。liveはHuman | 枠採択後 |
| collect-docs（後続Task） | Human live 結果の docs 同期 | live後 |
| #1811 / #1818 | **変更・完了操作しない**（Relationships追跡のみ） | 対象外 |
| GHA楽天live / #1607 / schedule | 本Decision外 | 対象外 |

---

## 6. 確認した事実

- BATCH-001 は起点 `--genre-ids` ＋直下 children までの同期であり、全階層自動総なめではない（BATCH-001仕様書・Epic背景）。
- MVP fetch_plan は `100000` / `100003` / `100004` / `100005` が承認済み（`2026-07-31-rakuten-fetch-mvp-fetch-plan`）。
- 常用QPS=2、安全側QPS=1（長時間・再開時等）、楽天live同時1本は既存 Human Decision / 運用方針で決定済み。
- Phase1 local cron は daily/weekly 親シェル経由（`local_cron_Phase1_crontab運用手順.md`）。キャンペーンはこれと分離する必要がある。

---

## 7. 推論

- root `0` からの BFS は、未知のジャンル全体像を段階的に把握する現実的な手段である（1回実行では直下までしか取れないため）。
- 1 Run=20 genre は、API負荷と再開単位のバランス案であり、実測で下げやすい上限値として妥当とみられる。
- weekly親全体を回すと BATCH-002以降や定常ノブまで巻き込み、地図キャンペーンの観測と定常cron観測が混線する。

---

## 8. 参照

- `docs/15_運用・改善/運用手順/楽天Fetch運用方針.md`
- `docs/15_運用・改善/運用手順/local_cron_Phase1_crontab運用手順.md`
- `docs/06_実装設計/batch/BATCH-001_楽天ジャンル同期バッチ仕様書.md`
- `ai-logs/human-decisions/2026-07-30-rakuten-fetch-ops-policy.md`
- `ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md`
- `ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md`
- `prompts/definitions/epics/batch-genre-map-campaign/epic.yaml`
- Issue #1829 / #1827 / #1811 / #1818 / #1745
