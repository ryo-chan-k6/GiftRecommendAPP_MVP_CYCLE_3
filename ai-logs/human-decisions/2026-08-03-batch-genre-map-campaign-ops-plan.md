# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-08-03-batch-genre-map-campaign-ops-plan` |
| Log種別 | `human-decision` |
| 件名 | 楽天ジャンル地図キャンペーンの運用枠（起点・1 Run上限・停止・容量ゲート・定常cron非干渉・QPS・Human live境界） |
| 発生日時 | 2026-08-03 |
| 記録日時 | 2026-08-03 |
| 更新日時 | 2026-08-03（Human採択反映: 全階層取り切り・容量 soft/hard・Slack） |
| 発生元Command | `/work-issue @prompts/definitions/tasks/batch-genre-map-campaign/ops-plan-decision.yaml` |
| 関連Issue | #1829（本Decision） / #1827（親Epic） / #1811（Phase1 cron・変更しない） / #1818（Phase2・変更しない） / #1745（統括） |
| 前提決定 | `2026-07-30-rakuten-fetch-ops-policy` / `2026-07-31-rakuten-fetch-mvp-fetch-plan` / `2026-08-01-batch-local-cron-ops-next` |
| 重要度 | `high` |
| 状態 | `decided` |

本Logは、Epic #1827 の着手ゲートとして、ジャンル地図キャンペーンの運用枠を正本化する。  
live実行・定常crontab変更・#1811/#1818完了操作・secret実値は含めない。  
AIは `--live-rakuten` を実行しない。

---

## 2. 結論（Human採択）

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | 起点・探索方式 | **root `0` からの BFS**。BATCH-001 は直下 `children` のみのため、未展開ジャンルを次 Run の `--genre-ids`（最大20）へ載せて段階同期する |
| 2 | 完了条件 | **全階層取り切り**（キュー空）。**depth 上限は置かない**（階層深さ・粒度が未知のため） |
| 3 | 1 Run あたり genre 上限 | **20 genre**（`--genre-ids` に載せる起点ID数。1応答の children 行数の上限ではない） |
| 4 | QPS | **常用QPS=2は維持**。キャンペーン BATCH-001 は安全側 **`max_qps=1`**。商品収集 cron と **同時楽天 live 禁止** |
| 5 | 容量・暴走制御 | **毎Runの人手容量確認はしない**。runner が soft/hard を自動判定（§2.3）。soft→**Slack通知**、hard→**自動停止＋Slack** |
| 6 | 停止条件 | §2.2（429 / paused / Human中断 / hard上限 / その他安全停止） |
| 7 | 定常cron非干渉 | **#1811 の daily/weekly は変更しない**。キャンペーンは葉 BATCH-001 CLI（または専用ラッパ）のみ。**weekly/daily 親全体は回さない** |
| 8 | live実行境界 | **AIは `--live-rakuten` しない**。liveは Human のみ。GHA楽天HTTP・#1607・`on.schedule` 有効化は対象外維持 |
| 9 | MVP fetch_plan 4ID | **`100000` / `100003` / `100004` / `100005` は置き換えない**。地図は後続 BATCH-002/003 計画の**拡大情報源** |

### 2.1 BFS 運用イメージ（採択）

```text
1. キューを [0] で開始
2. キュー先頭から最大 20 ID を --genre-ids に載せて BATCH-001 を 1 Run
3. 各起点について「本体＋直下 children」が DB に入る
   （root 0 を1回同期すれば、その直下 children 行はまとめて入る。0 を複数Runに分けて取る必要はない）
4. 新しく見えた非leaf（未展開）をキュー末尾へ追加
5. キュー空（全階層取り切り）または停止条件まで繰り返す
```

### 2.2 停止条件（採択）

以下のいずれかで **追加のキャンペーン Run を停止**し、Human へ通知する（Slack含む）。

1. **429が連続**（同一Runで再発、またはクールダウン後も再発）
2. **`paused` が増える**（campaign対象の同期失敗相当の滞留が増加）
3. **§2.3 hard 上限到達**（自動停止）
4. **Human中断**（明示停止）
5. egress不一致・secret漏えい疑い・想定外の同時楽天live検知（既存運用方針）

※ 「予定 Run 消化で止める」は必須条件としない（全階層取り切り優先）。予算消化は任意の運用メモとして使ってよい。

### 2.3 容量・暴走ゲート（採択・推奨初期値）

ローカル Docker PostgreSQL（Supabase local）へ INSERTする前提。ホスト空きは十分な見込みだが、毎Runの人手確認は行わず自動ゲートとする。

| ノブ | hard（100%・自動停止） | soft（80%・Slack通知・Run継続可） |
| ---- | ---------------------- | -------------------------------- |
| `max_external_genre_rows` | **100,000** | 80,000 |
| `max_api_calls` | **100,000** | 80,000 |
| `max_runs` | **5,000** | 4,000 |
| `max_raw_storage_bytes` | **5 GiB** | 4 GiB |
| `max_queue_size` | **50,000** | 40,000 |
| `max_depth` | **なし** | — |

- soft 到達: Slack通知＋ログ。Runは継続可。
- hard 到達: 自動停止＋Slack。追加 Run 禁止。
- 計測は runner が Run 前/後に実施（実装は後続 Task）。
- 初期値は非常停止用。実測後に Human が引き上げ/引き下げしてよい。

### 2.4 実行経路（採択）

| 経路 | キャンペーンでの扱い |
| ---- | -------------------- |
| 葉 BATCH-001 CLI | **推奨**（`--genre-ids` で BFS チャンクを明示） |
| 専用ラッパ（後続） | 可（dry-run可。親シェルを呼ばない。soft/hard・Slack内蔵） |
| `local_weekly_orchestrator.sh` 全体 | **禁止** |
| `local_daily_orchestrator.sh` | **禁止** |
| Phase1/Phase2 crontab 行の変更 | **禁止**（#1811 / #1818） |

### 2.5 QPS・同時実行（採択）

| 項目 | 決定 |
| ---- | ---- |
| 常用QPS | **2**（既存決定を変更しない） |
| キャンペーン BATCH-001 | **安全側 `max_qps=1`** |
| 同時楽天live | **常に1本**。daily/weekly 商品収集 cron の live と重ねない |
| CI / GHA 楽天live | **禁止**（既存方針維持） |

---

## 3. 運用上の境界

- 本枠は **ジャンル地図把握の別枠キャンペーン**に限定する。商品本格収集や定常cronを置き換えない。
- MVP fetch_plan 4IDの承認内容は変更しない。地図成果は後続の取得計画検討用。
- secret・接続文字列・token・APIキー実値は docs / Issue / PR / 本Log / Slack に記載しない。
- AI Agent は `--live-rakuten` を実行しない。dry-run・docs・Decision 同期のみ。
- チャット上の同意は本Logへ反映済みの範囲で正本とする（本更新で `decided`）。

---

## 4. Human採択記録

| 論点 | 採択 |
| ---- | ---- |
| root `0` BFS | **採択** |
| 1 Run 上限 20 | **採択** |
| 全階層取り切り（depth上限なし） | **採択**（2026-08-03） |
| soft→Slack / hard→自動停止 | **採択**（2026-08-03） |
| §2.3 hard 初期値（rows 100k / api 100k / runs 5k / raw 5GiB / queue 50k） | **採択**（2026-08-03・推奨値採用） |
| 毎Runの人手DB容量確認 | **しない**（自動ゲートに委譲） |

---

## 5. 後続アクション

| 対象 | 内容 | 状態 |
| ---- | ---- | ---- |
| #1829 | 本Decision Log・楽天Fetch運用方針同期 | 実施中（本PR） |
| inventory | external_genre 棚卸し手順・結果docs | **着手可**（本枠 decided） |
| runner | BFSラッパ（dry-run・soft/hard・Slack）。liveはHuman | 枠採択後 |
| collect-docs | Human live 結果の docs 同期 | live後 |
| #1811 / #1818 | **変更・完了操作しない** | 対象外 |
| GHA楽天live / #1607 / schedule | 本Decision外 | 対象外 |

---

## 6. 確認した事実

- BATCH-001 は起点 `--genre-ids` ＋直下 children までの同期であり、1回では全階層を取れない。
- MVP fetch_plan は `100000` / `100003` / `100004` / `100005` が承認済み。
- 常用QPS=2、安全側QPS=1、楽天live同時1本は既存決定済み。
- ローカルは Supabase `supabase_db_gift-reco-local`。確認時点でホスト空きは大きい（DBサイズは小さく、ジャンル地図でも hard 上限は非常停止用）。

---

## 7. 推論

- depth 上限なしでも、§2.3 の hard 上限があれば暴走を止められる。
- soft Slack により、hard 到達前に Human が気づける。

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
