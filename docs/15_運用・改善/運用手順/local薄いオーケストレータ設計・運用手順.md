# local薄いオーケストレータ設計・運用手順

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | 設計・運用手順正本（Phase1） |
| 対象 | GHA親オーケストレータ相当を local で薄く再現する親シェル |
| 作成日 | 2026-08-01 |
| 関連Issue | [#1803](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1803)（本設計） / [#1804](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1804)（実装） / [#1801](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1801)（収集） |
| 親Epic | [#1798](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1798) |
| ゲート正本 | [2026-08-01-local-batch-orchestrator-gate](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md)（`decided`） |
| 運用枠正本 | [2026-07-31-batch-data-collect-ops-plan](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md)（`decided`） |
| 状態 | Draft（Human Review前） |

本書は設計・運用手順の正本である。親シェル実装本体・収集実行・実 crontab 登録は含まない。
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
| 意味生成 | BATCH-009〜015 | **含めない** |
| 分布メトリクス | BATCH-016 | **含めない** |
| Offline Evaluation | BATCH-018 | **含めない** |
| retry_failed_items | BATCH-系 retry | **含めない**（GHA daily の任意 job 相当） |

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
| `scripts/batch/locks/`（gitignored 想定） | flock 用 lock ファイル置き場 |

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
| `pipeline_batch_run_id` | 複合子 `resolve-run-id` が UUID 生成、各葉へ `batch_run_id` 等で伝播 | **親シェルがシナリオ開始時に UUID を1つ生成**し、各 Batch CLI / 連鎖段へ渡す |
| 葉ごとの `job_run_id` | 葉側で新規 UUID（意味生成連鎖の教訓どおり分離） | Phase1 では親の `pipeline_batch_run_id` を業務紐付けの主キーとする。葉固有 ID が CLI 必須なら親が段ごとに派生 UUID を発行してよい（実装で確定） |
| 空入力時 | GHA が新規 UUID | local も未指定時は親が生成。手動再開時は既存 ID を明示指定可 |

参照: [BATCH import連鎖 GHA live化メモ C3](./BATCH_import連鎖_GHA_live化メモ_C3.md)

---

## 5. 排他・失敗停止・再開・観測

### 5.1 排他

| ロック | 目的 | 推奨 lock 名（実装は #1804） |
| ------ | ---- | --------------------------- |
| 本線 flock | GHA `batch-mainline` 相当。daily / weekly / 手動親の衝突防止 | `scripts/batch/locks/local-batch-mainline.lock` |
| 楽天 live 横断 1 本 | BATCH-001〜004 live の同時実行禁止（[楽天Fetch運用方針](./楽天Fetch運用方針.md) §6.2） | `scripts/batch/locks/local-rakuten-live.lock` |

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

### 7.1 例（登録しない・参考のみ）

タイムゾーンはホストの cron 設定に依存する。以下は **JST 想定の例**であり、GHA UTC cron（`30 15 * * 0-5` 等）の移植ではない。

```cron
# 【例】実登録は Human。AI / Task は登録しない。
# リポジトリルートで実行する前提。パス・ユーザは環境に合わせる。

# local-daily: 月曜〜土曜 00:30 JST
30 0 * * 1-6  cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_daily_orchestrator.sh >> scripts/batch/output-local-orchestrator/cron-daily.log 2>&1

# local-weekly: 日曜 00:30 JST（当日は daily を入れない）
30 0 * * 0    cd /path/to/GiftRecommendAPP_MVP_CYCLE_3 && ./scripts/batch/local_weekly_orchestrator.sh >> scripts/batch/output-local-orchestrator/cron-weekly.log 2>&1
```

手動起動例（概念）:

```bash
# dry-run（#1804 実装後）
./scripts/batch/local_daily_orchestrator.sh --dry-run

# live（明示フラグ必須。secret は .env 等から読み、値をエコーしない）
./scripts/batch/local_daily_orchestrator.sh --live-rakuten
```

### 7.2 Human 境界

| 作業 | 担当 |
| ---- | ---- |
| 親シェル実装・dry-run 確認 | #1804（AI 可） |
| crontab 例・運用手順の文書化 | 本書 / #1803 |
| **実 crontab 登録** | **Human** |
| **PC / WSL 常時起動・電源・ネットワーク維持** | **Human** |
| 本格収集キャンペーンの開始・段階進行・停止判断 | #1801 ＋ Human（運用枠 Decision） |
| GHA schedule 有効化（#1792） | Human・別 Task（本書対象外） |

AI Agent および Task #1803 / #1804 は、実 crontab へ書き込まない。

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
├─ locks/                             # flock 用（gitignored 推奨）
├─ output-local-orchestrator/         # ログ（gitignored 推奨）
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
| `MAX_ITEMS` | 005〜008 件数上限（GHA `max_items` 相当） |
| Run 予算ノブ | BATCH-003 は運用枠・§5.3.4（段階1は初期 live 相当） |

シナリオ名・ファイル名の最終採否は Human 判断点（軽微な調整は実装前に可）。

---

## 10. 関連資料

| 資料 | 用途 |
| ---- | ---- |
| [local薄いオーケストレータ導入ゲート](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md) | Issue 分割・Phase1・cron 境界 |
| [本格収集運用枠 Decision](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) | 段階・期間/Run 上限・停止 |
| [楽天Fetch運用方針](./楽天Fetch運用方針.md) | QPS・egress・同時 live・監視 |
| [バッチ実行スケジュール設計書](../../05_アプリケーション設計/アプリ/batch/バッチ実行スケジュール設計書.md) | GHA 親子・needs・concurrency |
| [BATCH import連鎖 GHA live化メモ C3](./BATCH_import連鎖_GHA_live化メモ_C3.md) | `pipeline_batch_run_id` |
| [scripts/batch/README.md](../../../scripts/batch/README.md) | 既存ハーネス・配置 |
| `.github/workflows/batch-daily-orchestrator.yml` | 日次親正本 |
| `.github/workflows/batch-weekly-orchestrator.yml` | 週次親正本 |
| `.github/workflows/batch-rakuten-item-import.yml` | import 複合子正本 |

---

## 11. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版（#1803）。Phase1 範囲、GHA↔local 対応表、排他・失敗停止・再開・観測、安全要件、crontab 例と Human 境界、#1804 / #1801 引き渡し、推奨スクリプト名 |
