# local薄いオーケストレータ設計・運用手順

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 設計・運用手順正本（Phase1 実装済 ＋ Phase2 配線設計） |
| 対象 | GHA親オーケストレータ相当を local で薄く再現する親シェル |
| 作成日 | 2026-08-01 |
| 関連Issue | [#1803](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1803)（Phase1設計） / [#1804](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1804)（Phase1実装） / [#1820](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1820)（Phase2配線設計） / [#1822](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1822)（Phase2実装） / [#1824](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1824)（Phase2 dry-run検証） / [#1813](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1813)（crontab運用手順） |
| 親Epic | [#1798](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1798)（本線#6） / [#1811](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1811)（local cron Phase1） / [#1818](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1818)（local cron Phase2） |
| ゲート正本 | [2026-08-01-local-batch-orchestrator-gate](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md)（`decided`） |
| 運用枠正本 | [2026-07-31-batch-data-collect-ops-plan](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md)（`decided`） |
| cron次本線 | [2026-08-01-batch-local-cron-ops-next](../../../ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md)（`decided`） |
| 状態 | Phase1 Implemented（#1804）。Phase2 配線設計は #1820。Phase2 親シェル配線実装は #1822（`--run-meaning` opt-in / 既定 Phase1 互換）。Phase2 dry-run 本記録は [local_cron_Phase2_dry-run検証結果](./local_cron_Phase2_dry-run検証結果.md)（#1824）。crontab 運用手順正本は [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md)（#1813）。Phase2 載せ替え手順は [local_cron_Phase2_crontab載せ替え手順](./local_cron_Phase2_crontab載せ替え手順.md)（Human 明示承認 B・2026-08-24）。実 crontab 登録は Human |

本書は設計・運用手順の正本である。§1〜§10 は Phase1（001〜008/+017任意）および関連資料。§11〜§15 は Phase2（009〜016 親シェル配線）。§16 は変更履歴。親シェル実装は #1804 / Phase2 配線は #1822（`scripts/batch/local_*_orchestrator.sh`）。dry-run 本記録は #1824。crontab 載せ替えは後続 cron-cutover / Human。実 crontab 登録は Human。
secret・接続文字列・token・egress IP の実値は記載しない。

---

## 2. 目的と非目的

### 2.1 目的

- GHA `batch-daily-orchestrator` / `batch-weekly-orchestrator` の **needs・排他・Run ID伝播・失敗停止** を、local 親シェルで再現する要件を確定する
- 楽天 HTTP live が **登録 egress IP の local のみ**である制約下で、本格収集（#1801）の実行制御入力を整える
- 後続 [#1804](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1804)（実装）と [#1801](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1801)（収集）への引き渡し条件を明文化する

### 2.2 非目的（本書および #1803 の out of scope）

| 対象 | 扱い |
| ---- | ---- |
| 親シェル実装本体 | [#1804](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1804) |
| local 継続収集の実行本体 | [#1801](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1801) |
| 実 crontab 登録・PC 常時起動 | **Human** |
| Airflow / Prefect 等の本格ジョブ基盤 | 非採用（ゲート範囲外） |
| #1792 schedule 有効化 / GHA `on.schedule` コメント解除 | 対象外 |
| #1607 / GHA 楽天 live | 対象外・禁止維持 |
| BATCH-009〜015 意味生成パイプラインの local 定期化 | Phase1 対象外 |
| secret 実値の表示・変更 | 禁止 |

---

## 3. Phase1 再現範囲

### 3.1 含める Batch

ゲート決定どおり、**楽天 Fetch 本線中心**とする。

| 区分 | Batch | Phase1 |
| ---- | ----- | ------ |
| 楽天 Fetch 本線 | BATCH-001 / 002 / 003 / 004 | **必須中心** |
| import 連鎖（複合子内） | BATCH-005 / 006 / 007 / 008 | **必要なら含める**（GHA `item_import` / `existing_item_pipeline` 相当） |
| import 集計 | BATCH-017 | **任意**（GHA 複合子に含まれる。観測用。失敗時扱いを実装で定義） |
| 意味生成 | BATCH-009〜015 | Phase1 **含めない**（Phase2 は §11〜§15） |
| 分布メトリクス | BATCH-016 | Phase1 **含めない**（Phase2 は §11〜§15） |
| Offline Evaluation | BATCH-018 | **含めない**（Phase2 にも載せない） |
| retry_failed_items | BATCH-系 retry | Phase1 / Phase2 とも本線自動に **含めない**（GHA daily 任意 job 相当） |

### 3.2 親シナリオ（local）

起動は **親シナリオ 1〜2 本**のみ。子 Batch の個別 cron は禁止する。

| シナリオ ID | 用途 | GHA 対応 | 推奨スクリプト名（実装は #1804） |
| ----------- | ---- | -------- | -------------------------------- |
| `local-daily` | 日次相当（月〜土） | `batch-daily-orchestrator.yml` の Phase1 部分 | `scripts/batch/local_daily_orchestrator.sh` |
| `local-weekly` | 週次相当（日。日次相当を内包） | `batch-weekly-orchestrator.yml` の Phase1 部分 | `scripts/batch/local_weekly_orchestrator.sh` |

共通ヘルパ（推奨・実装は #1804）:

| ファイル | 用途 |
| -------- | ---- |
| `scripts/batch/lib/local_orchestrator_common.sh` | flock・Run ID 生成・段階実行・ログ・終了コード規約 |
| `scripts/batch/output-local-orchestrator/locks/`（`scripts/batch/output-*/` で gitignored） | flock 用 lock ファイル置き場 |

### 3.3 Phase1 実行順序

#### local-daily（GHA daily の Phase1 切り出し）

```text
BATCH-002 ランキングスナップショット
  ↓（成功時のみ）
BATCH-003 → 005 → 006 → 007 → 008（→ 017 任意）
  ※ GHA job: ranking_snapshot → item_import
  ※ GHA の item_meaning_generation / distribution_metrics / retry_failed_items は走らない
```

#### local-weekly（GHA weekly の Phase1 切り出し）

```text
BATCH-001 ジャンル同期
  ↓
BATCH-002 ランキングスナップショット
  ↓
BATCH-003 → 005 → 006 → 007 → 008（→ 017 任意）
  ↓
BATCH-004 → 005 → 006 → 007 → 008（→ 017 任意）
  ※ GHA job: genre_sync → ranking_snapshot → item_import → existing_item_pipeline
  ※ 意味生成以降は走らない
```

週次当日は `local-daily` を別途起動しない（GHA 週次が日次を内包する方針と同旨）。

---

## 4. GHA 親 / 複合子と local 親シェルの対応表

### 4.1 親レベル

| GHA（正本） | local Phase1 | 備考 |
| ----------- | ------------ | ---- |
| `batch-daily-orchestrator.yml` | `local_daily_orchestrator.sh` | schedule 無効（B-0）維持。local は OS cron / 手動 |
| `batch-weekly-orchestrator.yml` | `local_weekly_orchestrator.sh` | 同上 |
| `concurrency.group: batch-mainline` / `cancel-in-progress: false` | 本線 flock（§5.1） | 待機または即失敗は実装で選択。既存 Run の cancel はしない |
| `jobs.needs` 直列 | 親シェルの直列実行（`set -e` 相当） | 失敗時は後続を起動しない |
| `notify_failure`（Slack） | 最低限: 終了コード非0＋ローカルログ。Slack は任意・後続可 | secret をログに出さない |
| `max_items` input | 環境変数または CLI 引数（概念名 `MAX_ITEMS`） | 楽天 Fetch 予算とは別物（[楽天Fetch運用方針](./楽天Fetch運用方針.md) §4.1） |

### 4.2 複合子・葉

| GHA workflow / job | Batch | local 対応 |
| ------------------ | ----- | ---------- |
| `batch-rakuten-genre-sync.yml` / `genre_sync` | BATCH-001 | weekly 先頭段。既存 Batch CLI（live 明示） |
| `batch-rakuten-ranking-snapshot.yml` / `ranking_snapshot` | BATCH-002 | daily / weekly |
| `batch-rakuten-item-import.yml` / `item_import` | 003→005→006→007→008→017 | 親シェル内の import 連鎖関数、または同等の直列呼び出し |
| `resolve-run-id` → `pipeline_batch_run_id` | （制御） | 親が UUID を1つ生成し全段へ伝播（§5.3） |
| `concurrency.group: batch-rakuten-item-import` | （制御） | 本線 flock ＋楽天 live 横断1本で代替（葉専用 group を OS 上に複製しない） |
| `batch-rakuten-existing-item-pipeline.yml` | 004→005→006→007→008→017 | weekly のみ。004 独立葉との同時 live 禁止 |
| `batch-item-meaning-generation.yml` 以降 | 009〜 | **Phase1 非対象** |

### 4.3 Run ID

| 概念 | GHA | local Phase1 |
| ---- | --- | ------------ |
| `pipeline_batch_run_id` | 複合子 `resolve-run-id` が UUID 生成、各葉へ `batch_run_id` 等で伝播 | **親シェルがシナリオ開始時に UUID を1つ生成**し、003 import 連鎖へ渡す |
| existing-item business ID | GHA `existing_item_pipeline` の `resolve-run-id` | weekly の 004〜017 用に **別 UUID を発行**。BATCH-004 は object_key に `job_run_id` を埋めるため、004 の `--job-run-id` と 005 以降の `--batch-run-id` を同一にする（シナリオ ID と混在させると empty staging_plan） |
| 葉ごとの `job_run_id` | 葉側で新規 UUID（意味生成連鎖の教訓どおり分離） | 003 import 側の 005〜017・007/008 等は葉 UUID＋`--batch-run-id`（業務 ID）。004 本体は business ID を `--job-run-id` に使う |
| 空入力時 | GHA が新規 UUID | local も未指定時は親が生成。手動再開時は既存 ID を明示指定可 |

参照: [BATCH import連鎖 GHA live化メモ C3](./BATCH_import連鎖_GHA_live化メモ_C3.md)

---

## 5. 排他・失敗停止・再開・観測

### 5.1 排他

| ロック | 目的 | 推奨 lock 名（実装は #1804） |
| ------ | ---- | --------------------------- |
| 本線 flock | GHA `batch-mainline` 相当。daily / weekly / 手動親の衝突防止 | `scripts/batch/output-local-orchestrator/locks/local-batch-mainline.lock` |
| 楽天 live 横断 1 本 | BATCH-001〜004 live の同時実行禁止（[楽天Fetch運用方針](./楽天Fetch運用方針.md) §6.2） | `scripts/batch/output-local-orchestrator/locks/local-rakuten-live.lock` |

要件:

1. 親シナリオ開始時に本線 lock を取得する（取得不可なら新規本線を開始しない）
2. 楽天 HTTP を行う段の直前に楽天 live lock を取得する（または本線実行中は常時保持）
3. 既存 Run がある場合は **cancel せず完了待ち**（緊急停止は Human）
4. GHA 本線と local 本線の同時運用は、B-0（GHA schedule 無効）下では通常衝突しない。将来 GHA schedule 有効化時は別途 Human 判断（本書では有効化しない）

### 5.2 失敗時の後続停止

| 事象 | 親シェルの振る舞い |
| ---- | ------------------ |
| いずれかの段が非0終了 | **後続段を起動しない**（GHA `needs` 相当） |
| 楽天 `rate_limited` / egress 不一致 / 同時 live 検知 | 当該 Run を停止し、追加の楽天 live を開始しない |
| secret 漏えい疑い | 再実行せず Human / security へエスカレーション |

失敗通知の最低ライン: 終了コード、失敗段名、`pipeline_batch_run_id`、ログパスを標準エラーまたはログファイルへ記録する（値に secret を含めない）。

### 5.3 再開単位

再開は [楽天Fetch運用方針](./楽天Fetch運用方針.md) §6.1 / §7 に従う。親オーケストレータ観点の単位は次のとおり。

| 失敗箇所 | 再開単位 | 親の扱い |
| -------- | -------- | -------- |
| BATCH-001 | 起点 genreId | 週次シナリオを当該段から手動再実行（成功済み 002 以降はスキップ可。実装でフラグ化） |
| BATCH-002 | genreId × page | 同上 |
| BATCH-003 | cursor × page（position 保持） | import 連鎖の先頭から、または 003 のみ再実行後に 005〜を継続 |
| BATCH-004 | `external_item_code` / recheck cursor | weekly の recheck 連鎖から |
| 005〜008 | 当該 Batch の入力（同一 `pipeline_batch_run_id`） | 連鎖の途中再開を許容（実装で段スキップ） |

`paused` / `failed` cursor の自動 `active` 化は行わない（手動確認後。運用方針 §7.4）。

本格収集キャンペーンの期間/Run 上限到達時は、[運用枠 Decision](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) に従い **追加 Run を停止**し Human へ通知する（cursor position は保持）。

### 5.4 観測（ログ / DB）

親シナリオ Run ごとに、少なくとも次を追跡可能にする（実装は #1804、収集時の確認は #1801）。

| 観点 | 参照先（例） |
| ---- | ------------ |
| シナリオ開始/終了・失敗段 | 親シェルログ（`scripts/batch/output-local-orchestrator/` 想定・gitignored） |
| `pipeline_batch_run_id` | ログ先頭および各 Batch へ渡した ID |
| Batch 成否 | `batch_run_log` |
| 楽天 API | `api_call_log`（`succeeded` / `failed` / `rate_limited`） |
| cursor | `fetch_cursor`（`active` / `paused` / `exhausted` / `failed`） |
| エラー | `error_log`（secret なし） |

監視閾値・停止基準の数値正本は [楽天Fetch運用方針](./楽天Fetch運用方針.md) §5.3.5 / §9。実測見直しは #1801。

---

## 6. 安全要件（egress・live・QPS・secret）

Phase1 local 親シェルおよびそれが起動する Batch は、次を満たすこと。

| 要件 | 内容 |
| ---- | ---- |
| egress 照合 | 楽天 HTTP 前に期待 egress と観測値を照合。不一致・未設定なら楽天 HTTP しない |
| 明示 live | `--live-rakuten` または承認済み環境変数（例: `BATCH_RAKUTEN_LIVE`）の明示がない実行を楽天 HTTP へフォールスルーさせない |
| 常用 QPS | **2**（ハードキャップ 10）。長時間 / 003・004 / 429 後は安全側 QPS=1（運用方針 §3 / §10） |
| secret | 実値を docs / Issue / PR / ログ / Summary に出さない。環境変数名のみ扱う |
| 実行場所 | **local / 登録 egress IP のみ**。GHA からの楽天 live は禁止 |
| dry-run | 実装（#1804）は live なしで順序・flock・Run ID 伝播を確認できるモードを持つ |

詳細正本: [楽天Fetch運用方針](./楽天Fetch運用方針.md) §3 / §6 / §8 / §9。疎通ハーネス慣例: [scripts/batch/README.md](../../../scripts/batch/README.md)。

---

## 7. crontab 例と Human 境界

**Phase1 定常運用の正本**は [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md)（#1813）とする。
本節は親シェル設計側の要約・参照入口であり、定常ノブ・Human 登録チェックリスト・verify 着手条件はそちらを正とする。

### 7.1 例（登録しない・参考のみ）

タイムゾーンはホストの cron 設定に依存する。以下は **JST 想定の例**であり、GHA UTC cron（`30 15 * * 0-5` 等）の移植ではない。
Phase1 定常では `--live-rakuten` とノブ（`pages_per_run=60` / `max_qps=1` / Ranking `100005` / ジャンル1本）を明示する（詳細は crontab運用手順 §4〜§5）。

```cron
# 【例】実登録は Human。AI / Task は登録しない。
# リポジトリルートで実行する前提。パス・ユーザは環境に合わせる。
# 親シェル経由のみ。葉 Batch の個別 cron は禁止。

# local-daily: 月曜〜土曜 00:30 JST
30 0 * * 1-6  cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-daily.log 2>&1

# local-weekly: 日曜 00:30 JST（当日は daily を入れない）
30 0 * * 0    cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_weekly_orchestrator.sh --live-rakuten --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-weekly.log 2>&1
```

手動起動例（概念）:

```bash
# dry-run（#1804）
./scripts/batch/local_daily_orchestrator.sh --dry-run

# live（明示フラグ必須。secret は .env 等から読み、値をエコーしない）
# Phase1 定常ノブ例（ジャンルは1本ローテ。詳細は crontab運用手順）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100005 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

### 7.2 Human 境界

| 作業 | 担当 |
| ---- | ---- |
| 親シェル実装・dry-run 確認 | #1804（AI 可） |
| crontab 例・設計側要約 | 本書 / #1803 |
| crontab 運用手順正本・定常ノブ同期 | [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) / #1813 |
| **実 crontab 登録** | **Human** |
| **PC / WSL 常時起動・電源・ネットワーク維持** | **Human** |
| 本格収集キャンペーンの開始・段階進行・停止判断 | #1801 ＋ Human（運用枠 Decision） |
| GHA schedule 有効化（#1792） | Human・別 Task（本書対象外） |

AI Agent および Task #1803 / #1804 / #1813 は、実 crontab へ書き込まない。`--live-rakuten` 実行も #1813 では AI が行わない。
---

## 8. 後続 Task への引き渡し条件

### 8.1 #1804（local-orchestrator-impl）

着手・完了の入力として、次が満たされていること。

| No | 条件 |
| --: | ---- |
| 1 | ゲート Log `2026-08-01-local-batch-orchestrator-gate` が `decided` |
| 2 | 本書がレビュー可能な状態で、Phase1 範囲・対応表・排他・失敗停止・安全要件・crontab Human 境界が記載されている |
| 3 | 推奨スクリプト配置名が確定している（軽微な命名調整は実装前に可） |
| 4 | 実装 scope に 009〜015 定期化・実 crontab 登録・#1792・#1607・GHA 楽天 live・secret 実値が含まれない |

#1804 の成果物期待（設計側からの要求）:

- `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh`（および common）
- flock・`pipeline_batch_run_id`・失敗停止・dry-run
- egress / 明示 live / QPS=2 前提の配線（secret 非記載）
- `scripts/batch/README.md` と本書の実装反映更新

### 8.2 #1801（local-collect-and-monitor）

| No | 条件 |
| --: | ---- |
| 1 | #1804 が完了し、親シェル経由で段階収集を起動できる |
| 2 | 運用枠 Decision（段階1→4・最大7日または BATCH-003 累計20 Run・停止条件）に従う |
| 3 | **オーケストレータ経由**で収集する（子の個別 cron やアドホック並列 live で代替しない） |
| 4 | §5.3.5 実測見直しを docs へ反映する（維持も可） |
| 5 | #1804 完了まで本作業（収集実行）は停止（ゲート決定） |

### 8.3 明示的に引き渡さないもの

- #1792 / B-1 schedule 有効化
- #1607 / GHA 楽天 live
- Airflow 等の基盤導入

---

## 9. 実装配置（推奨名・#1804 向け）

```text
scripts/batch/
├─ README.md                          # 実装後に親オーケストレータ節を追加
├─ local_daily_orchestrator.sh        # 新規（#1804）
├─ local_weekly_orchestrator.sh       # 新規（#1804）
├─ lib/
│  └─ local_orchestrator_common.sh    # 新規（#1804）推奨
├─ output-local-orchestrator/         # ログ＋locks（gitignored: scripts/batch/output-*/）
├─ rakuten_live_verify.py             # 既存疎通ハーネス
└─ object_storage_live_verify.py      # 既存
```

CLI 慣例（実装で確定してよい）:

| フラグ / 環境変数（概念） | 意味 |
| ------------------------- | ---- |
| `--dry-run` | 外部副作用なしで順序・lock・Run ID を確認 |
| `--live-rakuten` | 楽天 HTTP live 明示 |
| `--from-step=<name>` | 再開時の開始段（任意） |
| `--pipeline-batch-run-id=<uuid>` | 既存 ID の継続（省略時は新規） |
| `--genre-ids` | BATCH-003（および weekly BATCH-001）向け。段階3で拡大する側（既定 `100005`）。**第1波拡大（案B）でも常に1本**（[手動実行手順](./fetch_plan拡大_第1波_1ジャンル手動実行手順.md)） |
| `--ranking-genre-ids` | BATCH-002 Ranking 向け（既定 `100005`。#1765: Ranking 非対応ジャンルと分離）。第1波拡大の Ranking は親連続起動ではなく **別 Run（葉）** |
| `MAX_ITEMS` | 005〜008 件数上限（GHA `max_items` 相当） |
| Run 予算ノブ | BATCH-003 は運用枠・§5.3.4（段階1は初期 live 相当）。新ID初回は smoke `pages_per_run=1` 推奨 |

シナリオ名・ファイル名の最終採否は Human 判断点（軽微な調整は実装前に可）。

#### 9.1 第1波 fetch_plan 拡大（#1846）との接続

| 項目 | 扱い |
| ---- | ---- |
| Decision | [拡大候補 Log](../../../ai-logs/human-decisions/2026-08-04-batch-fetch-plan-expansion-candidates.md)（`decided`・案B） |
| 手順正本 | [fetch_plan拡大_第1波_1ジャンル手動実行手順](./fetch_plan拡大_第1波_1ジャンル手動実行手順.md) |
| Item Run | 親 daily を `--from-step item_pseudo_diff` で手動起動（Ranking 段を踏まない） |
| Ranking Run | 葉 BATCH-002 を **別起動**。親 daily 先頭からの 002→003 連続は第1波拡大では使わない |
| 親シェル | **無断変更しない** |
| 定常crontab（#1811 / #1818） | **変更しない**。案Bを cron 行へ載せない（別Task・Human承認） |
| AI `--live-rakuten` | **禁止**。dry-run のみ可 |

---

## 10. 関連資料

| 資料 | 用途 |
| ---- | ---- |
| [local薄いオーケストレータ導入ゲート](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md) | Issue 分割・Phase1・cron 境界 |
| [local cron 次本線 Decision](../../../ai-logs/human-decisions/2026-08-01-batch-local-cron-ops-next.md) | local cron・Phase1 定常ノブ |
| [local_cron_Phase1_crontab運用手順](./local_cron_Phase1_crontab運用手順.md) | crontab 運用手順正本（#1813） |
| [本格収集運用枠 Decision](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) | 段階・期間/Run 上限・停止 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) | QPS・egress・同時 live・監視 |
| [fetch_plan拡大_第1波_1ジャンル手動実行手順](./fetch_plan拡大_第1波_1ジャンル手動実行手順.md) | #1846。案B・1ジャンル手動起動・切替ゲート（親シェル無断変更なし） |
| [バッチ実行スケジュール設計書](../../05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) | GHA 親子・needs・concurrency |
| [BATCH import連鎖 GHA live化メモ C3](./BATCH_import連鎖_GHA_live化メモ_C3.md) | `pipeline_batch_run_id` |
| [scripts/batch/README.md](../../../scripts/batch/README.md) | 既存ハーネス・配置 |
| `.github/workflows/batch-daily-orchestrator.yml` | 日次親正本 |
| `.github/workflows/batch-weekly-orchestrator.yml` | 週次親正本 |
| `.github/workflows/batch-rakuten-item-import.yml` | import 複合子正本 |
| `.github/workflows/batch-item-meaning-generation.yml` | 意味生成複合子正本（Phase2） |
| `.github/workflows/batch-distribution-metrics.yml` | 分布メトリクス正本（Phase2） |
| Epic #1818 / Task #1820 | local cron Phase2（009〜016 親シェル配線） |

---

## 11. Phase2 再現範囲と daily / weekly 配置

本章は Decision `2026-08-01-batch-local-cron-ops-next` の Phase2（Epic #1818 / Task #1820）の**配線設計**である。
実装本体・dry-run 本記録・実 crontab 載せ替えは後続 Task。本節は設計のみ。

### 11.1 目的と非目的

#### 目的

- GHA `batch-daily-orchestrator` / `batch-weekly-orchestrator` の **import 連鎖後 → `item_meaning_generation` → `distribution_metrics`** を、local 親シェルへ載せる要件を確定する
- daily / weekly のどちらに BATCH-009〜016 を載せるかを明記し、後続 impl が迷わない状態にする
- Phase1 観測（#1811）と並行しても濁さない **互換モード / 非干渉境界** を設計に含める

#### 非目的（#1820 および Phase2 設計の out of scope）

| 対象 | 扱い |
| ---- | ---- |
| 親シェル実装本体（009〜016 配線コード） | #1822（実装済。本節は設計正本） |
| dry-run 実行結果の運用 docs 本記録 | 後続 dry-run-verify Task |
| 実 crontab 変更・載せ替え | **cron-cutover / Human ゲート**（観測中は禁止） |
| AI による `--live-rakuten` / Phase2 追加 live | **禁止**（観測濁し防止） |
| BATCH-018 / 019 | 自動運用対象外維持 |
| GHA `on.schedule` 有効化（#1792） / #1607 / GHA 楽天 live | 対象外・先送り |
| `retry_failed_items` の local 本線自動 | Phase2 本線に含めない（GHA 任意 job 相当。必要なら別途 Human / manual） |
| Phase1 #1811 の再開・完了扱い | 分離維持（本設計では操作しない） |
| secret 実値の表示・変更 | 禁止 |

### 11.2 Phase2 で親シェルに載せる Batch

| 区分 | Batch | Phase2 |
| ---- | ----- | ------ |
| 意味生成連鎖 | BATCH-009 → 010 → 011 → 012 → 013 → 014 → 015 | **必須**（GHA `batch-item-meaning-generation` 相当） |
| 意味連鎖末尾集計 | BATCH-017（meaning 複合子末尾） | **任意**（GHA 複合子に含まれる。`--skip-meaning-summary` 等で省略可。実装で確定） |
| 分布メトリクス | BATCH-016 | **必須**（GHA `batch-distribution-metrics` / `trigger_mode: chain` 相当） |
| Offline Evaluation | BATCH-018 | **載せない** |
| Feedback | BATCH-019 | **載せない** |
| retry | retry_failed_items | **載せない**（本線自動外） |

Phase1 の 001〜008（+017 import 側任意）は維持する。Phase2 はそれら**の後**に 009〜016 を直列で追加する。

### 11.3 推奨配置（daily / weekly）— 設計推奨案

GHA 正本（[バッチ実行スケジュール設計書](../../05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) §6 / §12）に合わせ、**009〜016 は daily にも weekly にも載せる**。

| シナリオ | 009〜015 | 016 | 備考 |
| -------- | -------- | --- | ---- |
| `local-daily` | **載せる**（import 連鎖成功後） | **載せる**（意味生成成功後） | GHA daily: `item_import` → `item_meaning_generation` → `distribution_metrics` |
| `local-weekly` | **載せる**（existing 連鎖成功後に **1回のみ**） | **載せる**（意味生成成功後） | GHA weekly: `existing_item_pipeline` → `item_meaning_generation` → `distribution_metrics`。import 後と existing 後の二重実行はしない |
| 日曜 | weekly のみ | weekly のみ | Phase1 同様、週次当日は `local-daily` を別途起動しない |

**採用しない案（参考）:**

| 案 | 内容 | 不採用理由 |
| -- | ---- | ---------- |
| A' | 016 のみ weekly | GHA daily が 016 を日次で回す方針と不一致 |
| B' | 009〜016 を weekly のみ | GHA daily の needs 再現にならない |
| C' | 葉 Batch の個別 cron | Decision / Phase1 方針違反（親シェル経由のみ） |

最終採択は Human 判断点（Issue #1820）。本設計の**推奨は上表（GHA 同型）**とする。

### 11.4 Phase2 実行順序

#### local-daily（GHA daily 相当・Phase2）

```text
BATCH-002 ランキングスナップショット
  ↓（成功時のみ）
BATCH-003 → 005 → 006 → 007 → 008（→ 017 import 任意）
  ↓（成功時のみ。かつ --run-meaning 時）
BATCH-009 → 010 → 011 → 012 → 013 → 014 → 015（→ 017 meaning 任意）
  ↓（成功時のみ）
BATCH-016 分布メトリクス（trigger_mode=chain 相当）
  ※ retry_failed_items / 018 / 019 は走らない
```

#### local-weekly（GHA weekly 相当・Phase2）

```text
BATCH-001 ジャンル同期
  ↓
BATCH-002 ランキングスナップショット
  ↓
BATCH-003 → 005 → 006 → 007 → 008（→ 017 import 任意）
  ↓
BATCH-004 → 005 → 006 → 007 → 008（→ 017 existing 任意）
  ↓（成功時のみ。かつ --run-meaning 時）
BATCH-009 → 010 → 011 → 012 → 013 → 014 → 015（→ 017 meaning 任意）
  ↓（成功時のみ）
BATCH-016 分布メトリクス
  ※ 018 Offline Evaluation は走らない（GHA 任意も Phase2 非対象）
```

---

## 12. Phase2 の GHA needs 対応表

### 12.1 親レベル

| GHA（正本） | local Phase2 | 備考 |
| ----------- | ------------ | ---- |
| `batch-daily-orchestrator.yml` | `local_daily_orchestrator.sh` | schedule 無効（B-0）維持。local は OS cron / 手動 |
| `batch-weekly-orchestrator.yml` | `local_weekly_orchestrator.sh` | 同上。018 は載せない |
| `jobs.item_import` → `item_meaning_generation` | import 連鎖成功後に意味生成連鎖 | daily |
| `jobs.existing_item_pipeline` → `item_meaning_generation` | existing 連鎖成功後に意味生成連鎖 | weekly（import 直後には意味生成しない） |
| `jobs.item_meaning_generation` → `distribution_metrics` | 意味生成成功後に BATCH-016 | daily / weekly 共通 |
| `concurrency.group: batch-mainline` | 本線 flock（§5.1。Phase2 でも共用） | 009〜016 実行中も本線 lock を保持 |
| `concurrency.group: batch-item-meaning-generation` | 本線 flock で代替 | OS 上に葉専用 group を複製しない（Phase1 §4.2 と同旨） |
| `retry_failed_items` / `offline_evaluation` | **非実装** | Phase2 out of scope |
| `notify_failure` | Phase1 同様（終了コード＋ローカルログ。Slack 任意） | secret をログに出さない |

### 12.2 複合子・葉（Phase2 追加分）

| GHA workflow / job | Batch | local 対応（#1822） |
| ------------------ | ----- | ------------------------ |
| `batch-item-meaning-generation.yml` | 009→010→011→012→013→014→015→017 | `lor_run_meaning_chain`（直列）。起動は親のみ。`--run-meaning` 必須 |
| `resolve-run-id`（meaning） | （制御） | 意味連鎖開始時に新規 UUID（`--meaning-pipeline-batch-run-id` で継続可） |
| `batch-distribution-metrics.yml` | BATCH-016 | `lor_run_distribution_metrics`（`--trigger-mode chain`） |
| 葉ごとの `job_run_id` | （制御） | 各葉で新規 UUID。業務 ID（pipeline）と混在させない |

### 12.3 Phase1 境界との接続

| 境界 | 方針 |
| ---- | ---- |
| import / existing 連鎖の終端 | Phase1 どおり 008（+017任意）まで。ここで一旦成功判定 |
| 意味生成の開始条件 | 直前連鎖が成功 **かつ** `--run-meaning`（§14） |
| 意味生成失敗時 | 016 を起動しない（needs 相当） |
| 001〜008 失敗時 | 009〜016 を起動しない |
| 個別 cron | **禁止**（009〜016 を crontab に直接載せない） |

---

## 13. Phase2 の排他・失敗停止・Run ID

Phase1 §5 を継承し、009〜016 追加時も次を満たす。

### 13.1 排他（flock）

| ロック | Phase2 での扱い |
| ------ | --------------- |
| 本線 `local-batch-mainline.lock` | daily / weekly / 手動親の衝突防止。意味生成・016 実行中も保持 |
| 楽天 live `local-rakuten-live.lock` | 001〜004 live 段のみ。009〜016 は楽天 HTTP しない前提（取得不要） |
| 意味生成専用 OS lock | **必須としない**（本線 flock で足りる）。将来並行手動が必要になったら別途 Human 判断 |

要件（Phase1 §5.1 に加え）:

1. Phase2 段も本線 lock 取得後にのみ実行する
2. 既存 Run がある場合は cancel せず完了待ち
3. GHA schedule 有効化はしない（#1792 先送り）。将来の GHA×local 同時運用は別 Human 判断

### 13.2 失敗時の後続停止

| 事象 | 親シェルの振る舞い |
| ---- | ------------------ |
| 001〜008 系が非0 | 009〜016 を起動しない |
| 009〜015 のいずれかが非0 | **後続（残り意味段および 016）を起動しない** |
| 016 が非0 | シナリオ失敗終了（018 は無い） |
| secret 漏えい疑い | 再実行せず Human / security へエスカレーション |

失敗通知の最低ラインは Phase1 §5.2 と同じ（終了コード、失敗段名、関連 Run ID、ログパス。secret なし）。

### 13.3 Run ID 伝播

| 概念 | GHA | local Phase2（設計） |
| ---- | --- | -------------------- |
| import 連鎖の `pipeline_batch_run_id` | item-import 複合子 | Phase1 どおり親がシナリオ開始時に1つ生成し 003 連鎖へ |
| existing 連鎖の business ID | existing-item 複合子 | Phase1 どおり weekly で別 UUID（004 `--job-run-id` と 005 以降 `--batch-run-id` を同一） |
| meaning 連鎖の `pipeline_batch_run_id` | meaning 複合子の `resolve-run-id` | **意味連鎖開始時に新規 UUID を1つ発行**し 009〜015（+017）へ伝播。import / existing の ID と混在させない |
| 016 の葉 `job_run_id` | distribution-metrics 葉 | 葉側で新規 UUID（pipeline と分離） |
| 空入力時 | GHA が新規 UUID | local も未指定時は親が生成。手動再開時は明示指定可 |

実装 CLI（#1822 確定 / #1866 追記）:

| フラグ | 意味 |
| ------ | ---- |
| `--run-meaning` | 009〜016 を実行（既定はスキップ） |
| `--skip-meaning` | 009〜016 を明示スキップ（既定と同義。`--run-meaning` と排他） |
| `--skip-meaning-summary` | 意味連鎖末尾 BATCH-017 を省略 |
| `--meaning-pipeline-batch-run-id=<uuid>` | 意味連鎖の既存 ID 継続 |
| `--source=<name>` | 意味生成 source（既定 `rakuten`） |
| `--from-step=<name>` | Phase1 段に加え `item_generation_queue` … `meaning_summary` / `distribution_metrics` を許容 |
| `--live-embedding` | BATCH-015（`item_embedding`）のみ OpenAI Embedding live（既定 OFF）。`OPENAI_API_KEY` 必須。未指定時は scaffold Embedding。後方互換で環境変数 `BATCH_EMBEDDING_LIVE=1` も可 |

> **注意**: `--live-embedding` は楽天 `--live-rakuten` とは独立。意味連鎖 live embedding は Human 専用（課金）。AI Agent は付けない。
---

## 14. Phase1 互換モードと観測非干渉

### 14.1 Phase1 互換モード（必須）

Phase1 観測中に Phase2 実装が親シェルへ入っても、**既定動作は 001〜008（+017任意）のみ**とする。

| 項目 | 設計推奨 |
| ---- | -------- |
| 既定 | **009〜016 をスキップ**（Phase1 互換） |
| 有効化 | 明示フラグ **`--run-meaning`**（名称は impl で微調整可。同義の環境変数を置く場合は opt-in のみ） |
| 無効化の別名 | `--skip-meaning` を残す場合は「既定 skip と矛盾しない」こと（例: `--run-meaning` が無い＝skip。両方指定時はエラー） |
| crontab（観測中） | **変更しない**。フラグなし／`--run-meaning` なしのまま Phase1 挙動を維持 |
| cutover 後 | Human が cron 行へ `--run-meaning` を追加（cron-cutover Task / Human ゲート） |

**Human 判断点:** 既定を skip（本推奨）とするか、既定 run + `--skip-meaning` 必須とするか。
観測非干渉の観点では **既定 skip / `--run-meaning` opt-in** を推奨する（impl マージ直後に crontab 未変更でも濁さない）。

### 14.2 Phase1 観測非干渉（必須）

| ルール | 内容 |
| ------ | ---- |
| 実 crontab 載せ替え禁止 | Phase1 観測完了または Human 明示承認まで、009〜016 live を crontab に載せない |
| AI live 禁止 | AI Agent は `--live-rakuten` および Phase2 追加の実 Batch live を実行しない |
| 追加 live 禁止 | Phase2 検証は `--dry-run` 中心。観測を濁す追加 live を本 Epic で行わない |
| #1811 分離 | Phase1 Epic の再開・完了・verify 判断を本設計 / Phase2 Task で行わない |
| 個別 cron 禁止 | 009〜016 を含む葉の個別 crontab 登録をしない |

### 14.3 crontab 例（登録しない・Phase2 cutover 後の参考）

以下は **Human ゲート通過後**の参考例である。#1820 / impl / dry-run-verify では登録しない。

```cron
# 【例】Phase2 cutover 後。実登録は Human。AI は登録しない。
# Phase1 ノブを維持したうえで --run-meaning を追加するイメージ。

# local-daily: 月曜〜土曜 00:30 JST
30 0 * * 1-6  cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_daily_orchestrator.sh --live-rakuten --run-meaning --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-daily.log 2>&1

# local-weekly: 日曜 00:30 JST（当日は daily を入れない）
30 0 * * 0    cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_weekly_orchestrator.sh --live-rakuten --run-meaning --genre-ids 100005 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1 >> scripts/batch/output-local-orchestrator/cron-weekly.log 2>&1
```

観測中の Phase1 行からは `--run-meaning` を付けない（または親シェル既定 skip のまま）。

### 14.4 安全要件（Phase2 追加観点）

Phase1 §6 に加え:

| 要件 | 内容 |
| ---- | ---- |
| 意味生成・016 | 楽天 HTTP を行わない。egress / 楽天 live lock は不要（取得しない） |
| Embedding（015）等の外部 API | 既存 Batch の live / stub 方針に従う。secret をログ・docs に出さない |
| dry-run | impl は `--dry-run` で 009〜016 の順序・flock・Run ID・`--run-meaning` 分岐を確認できること |
| GHA | workflow の schedule コメント解除・楽天 live 化はしない |

---

## 15. Phase2 後続 Task への引き渡し

### 15.1 impl（親シェル 009〜016 実装）— #1822

| No | 条件 |
| --: | ---- |
| 1 | 本書 §11〜§14 がレビュー可能な状態である |
| 2 | daily / weekly 配置推奨（GHA 同型）と Phase1 互換（既定 skip / `--run-meaning`）が明記されている |
| 3 | 実装 scope に実 crontab 変更・AI live・018/019・#1792・#1607・GHA 楽天 live・secret 実値が含まれない |
| 4 | exclusive 競合に注意（`local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` / common） |

実装成果物（#1822）:

- `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` / `lib/local_orchestrator_common.sh` への 009〜016 配線
- `--dry-run` で意味連鎖・016・互換モードを確認可能
- `--run-meaning`（既定 skip）による Phase1 互換
- `scripts/batch/README.md` の最小更新
- 本書との実装差分の最小同期

### 15.2 dry-run-verify — #1824

| No | 条件 |
| --: | ---- |
| 1 | AI live なしで dry-run 結果を docs へ本記録する |
| 2 | Phase2 配線 ON（`--run-meaning`）と Phase1 互換スキップ（既定）の双方を記録する |
| 3 | Phase1 観測を濁さない（実 crontab 変更・追加 live なし） |
| 4 | cron-cutover は Human ゲートである旨を再確認記載する |

検証成果物（#1824）:

- 正本: [local_cron_Phase2_dry-run検証結果](./local_cron_Phase2_dry-run検証結果.md)
- daily / weekly ×（既定 skip / `--run-meaning`）の `--dry-run` がいずれも exit 0 / SUCCEEDED
- secret 実値なし。`--live-rakuten` / 実 crontab 変更なし

### 15.3 cron-cutover（Human ゲート）

| 条件 | 内容 |
| ---- | ---- |
| 着手条件 | Phase1 観測完了 **または** Human 明示承認 |
| ゲート状態（2026-08-24） | **(B) Human 明示承認**で充足。[cutover ゲート Decision](../../../ai-logs/human-decisions/2026-08-24-batch-local-cron-phase2-cutover-gate.md) |
| 実施者 | **Human**（AI は実 crontab を変更しない） |
| 内容 | cron 行へ `--run-meaning` 追加等。Phase1 ノブ・親シェル経由・個別 cron 禁止を維持 |
| 禁止 | 観測中の勝手な載せ替え、AI `--live-rakuten`、018/019 混入、案B genre 無断反映、`--live-embedding` 既定 ON |
| 前提材料 | #1824 dry-run 本記録済み |
| 手順正本 | [local_cron_Phase2_crontab載せ替え手順](./local_cron_Phase2_crontab載せ替え手順.md) |

### 15.4 明示的に引き渡さないもの

- #1792 / B-1 schedule 有効化
- #1607 / GHA 楽天 live
- BATCH-018 / 019 の自動運用
- Phase1 #1811 の完了判断
- Airflow 等の基盤導入

---

## 16. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版（#1803）。Phase1 範囲、GHA↔local 対応表、排他・失敗停止・再開・観測、安全要件、crontab 例と Human 境界、#1804 / #1801 引き渡し、推奨スクリプト名 |
| 2026-08-01 | #1804 実装反映。`local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` / `lib/local_orchestrator_common.sh` を配置。`--dry-run` で順序・flock・Run ID 確認可 |
| 2026-08-01 | #1808。`--genre-ids` / `--ranking-genre-ids` 分離を CLI 表へ反映 |
| 2026-08-01 | #1808。weekly existing 連鎖の business run ID 分離（004 object_key ↔ 005 選定）を追記 |
| 2026-08-01 | #1813。§7 を Phase1 定常ノブ付き例へ更新し、crontab運用手順正本への参照を追加 |
| 2026-08-01 | #1820。§11〜§15 を追加（Phase2: 009〜016 配線設計、GHA needs 対応、Phase1互換・観測非干渉、後続 Task 引き渡し）。変更履歴を §16 へ移動 |
| 2026-08-02 | #1822。親シェルへ 009〜016 配線実装（`--run-meaning` opt-in）。§1 / §12.2 / §13.3 CLI / §15.1 を実装差分で最小同期 |
| 2026-08-02 | #1824。Phase2 dry-run 双方モード検証を本記録化（[local_cron_Phase2_dry-run検証結果](./local_cron_Phase2_dry-run検証結果.md)）。§1 / §15.2 / §15.3 を最小同期 |
| 2026-08-04 | #1846。§9 / §10 に第1波 fetch_plan 拡大（案B・1ジャンル手動実行手順）への接続を追加。親シェル・crontab 無断変更なし |
| 2026-08-07 | #1866。親シェルへ `--live-embedding`（BATCH-015 のみ・既定 OFF）を伝播。§13.3 CLI 表を最小追記 |
| 2026-08-24 | §15.3。Human 明示承認 B による cutover 着手と載せ替え手順正本への参照を追記 |
