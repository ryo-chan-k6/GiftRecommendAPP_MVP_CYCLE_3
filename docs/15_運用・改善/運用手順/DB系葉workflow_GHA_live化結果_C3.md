# DB系葉workflow GHA live化結果（C3）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1750](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1750) |
| 関連 Task | [#1751](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1751) |
| 対象 | BATCH-009 / 011 / 012 / 013 / 014 / 016 |
| 環境 | GitHub Environment `stg` |
| DB Secret | `STG_DATABASE_URL` を job env `DATABASE_URL` へ割り当て |
| 記録日 | 2026-07-30 |

本結果に secret、token、DB接続文字列の実値は含めない。

## 2. Phase A: 現状調査

変更前は、対象6葉が `--scaffold-demo` を指定し、`job_run_id` の未指定時に
`gha-<run_id>-<run_attempt>` 形式の非UUIDを生成していた。

meaning複合 `batch-item-meaning-generation.yml` は、共有
`pipeline_batch_run_id` を BATCH-009〜015 の各 `job_run_id` として渡していた。
この構造は、pipeline IDと葉の tracker / `batch_run_log` PKを分離する方針と
一致していなかった。

既liveの BATCH-005〜008 / 017 では、次のパターンを使用していることを確認した。

- jobに `environment: stg` を指定する
- `DATABASE_URL: ${{ secrets.STG_DATABASE_URL }}` を設定する
- 葉の `job_run_id` を新規UUIDとして生成する
- pipeline IDと葉の `job_run_id` を分離する

## 3. Phase B: 葉live化

009 → 011 → 012 → 013 → 014 → 016 の順で、次を反映した。

- `--scaffold-demo` を削除
- `environment: stg` を追加
- `STG_DATABASE_URL` を `DATABASE_URL` へ割り当て
- `job_run_id` の既定値を新規UUIDへ変更
- step名とコメントをstg live経路へ同期

BATCH-016末尾のBATCH-017もlive経路へ揃え、017の新規 `job_run_id` と
集計対象である016の `job_run_id` を分離した。010 / 015のAI経路は変更していない。

## 4. Phase C: meaning複合整合

`batch-item-meaning-generation.yml` では、共有 `pipeline_batch_run_id` を
各葉の `job_run_id` として渡さないよう変更した。

- 009 / 011〜014: 各live葉で新規UUIDを生成
- 010 / 015: scaffoldを維持し、各葉の既定Run IDを使用
- 017: 集計対象として共有 `pipeline_batch_run_id` のみ受け取り、
  自身の `job_run_id` は新規UUIDを生成

`batch-retry-failed-items.yml` でも、live化した011〜014へ共有Run IDを渡さず、
各葉で新規UUIDを生成するよう整合した。

## 5. Phase D: 既live葉の回帰確認

BATCH-005 / 006 / 007 / 008 / 017 のworkflowに差分がないことを確認した。
既存の `environment: stg`、`STG_DATABASE_URL`、UUID生成、pipeline ID分離は
変更していない。

次のout of scopeにも差分はない。

- BATCH-001〜004の楽天live経路
- BATCH-010 / 015のAI live経路
- 親workflowの `on.schedule`
- BATCH-018 / 019
- OpenAPI / Orval / generated
- DDL / migration

## 6. Phase E: stg手動検証

Human判断（2026-07-30）:

1. `max_items=1` でのstg書込を許可
2. 低件数・葉/複合単位の手動のみ許容
3. Environment `stg` required reviewers は解除済み（承認待ちなし）
4. BATCH-016末尾→017接続は維持

### 6.1 実施サマリ

| 項目 | 内容 |
| ---- | ---- |
| ref | `feature/task-1751-db-leaf-workflow-live`（検証時点 HEAD `39341b46`） |
| 判定 | **PARTIAL**（DB接続は復旧。業務前提不足で葉実行は未成功） |

#### Attempt 1（Secret更新前）

| Workflow | Run URL | conclusion | 失敗種別 |
| -------- | ------- | ---------- | -------- |
| meaning複合 `max_items=1` | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30545806388 | failure | DB接続（tenant ENOTFOUND） |
| distribution-metrics | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30545808936 | failure | DB接続（tenant ENOTFOUND） |

#### Attempt 2（`STG_DATABASE_URL` 更新後・再dispatch）

| Workflow | inputs | Run URL | conclusion | 失敗種別 |
| -------- | ------ | ------- | ---------- | -------- |
| meaning複合 | `max_items=1`, `source=rakuten` | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30547134883 | failure | 009 empty plan（DB接続は成功） |
| distribution-metrics | `trigger_mode=dispatch` | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30547137306 | failure | scaffold semantic_config を UUID 列へ書込 |
| 009単独 | `max_items=1` + 既存 import の `diff_batch_run_id` | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30547356166 | failure | empty plan（eligible diff 0件） |

### 6.2 Attempt 2 Job結果（事実）

#### meaning複合（30547134883）

| Job | conclusion |
| --- | ---------- |
| `resolve-run-id` | success |
| `item_generation_queue / item-generation-queue` | **failure**（`Run BATCH-009 live`） |
| 後続（010〜017） | skipped |

ログ要約（secretなし）:

- `db_reader=postgres` / `db_writer=postgres`（**接続成功**）
- `BATCH-009 status=failed ... succeeded=0 failed=0 skipped=0 inserted=0`
- 実装上、処理対象0件かつ skipもない場合は `GRS-BAT-001`（empty registration plan）で failed

#### distribution-metrics（30547137306）

| Job / step | conclusion |
| ---------- | ---------- |
| Setup〜`Resolve job_run_id` | success（葉 `job_run_id` は UUID） |
| `Run BATCH-016 live` | **failure** |
| `Run BATCH-017 Import Summary live` | skipped |

ログ要約（secretなし）:

- DB接続後に `InvalidTextRepresentation: invalid input syntax for type uuid: "scaffold-semantic-config-v1"`
- アプリ既定値 `DEFAULT_SEMANTIC_CONFIG_VERSION = "scaffold-semantic-config-v1"` が live UUID 列に入らない
- Environment Variable `BATCH_DISTRIBUTION_METRICS_SEMANTIC_CONFIG_VERSION_ID` は未設定

### 6.3 解釈（事実 / 推論）

| 区分 | 内容 |
| ---- | ---- |
| 事実 | Attempt 1 の接続障害は、Human による `STG_DATABASE_URL` 更新後に解消 |
| 事実 | live step（`--scaffold-demo` なし）・UUID `job_run_id`・Environment `stg` は動作している |
| 事実 | 009 は接続成功後も eligible な `product_diff_result` が0件で failed |
| 事実 | 016 は scaffold 文字列の semantic_config 既定値が UUID 型と非互換で failed |
| 推論 | 更新後DBに import 連鎖の差分データが無い、または別DBへ切り替わった可能性 |
| 推論 | 016 成功には実在する `semantic_config_version_id`（UUID）の入力または Env Variable が必要 |

secret / 接続文字列の実値は記載しない。

### 6.4 代替確認（成功）

- 対象workflowのYAML構文確認
- 対象6葉の `environment: stg` / `STG_DATABASE_URL` / UUID生成の静的確認
- 対象6葉に `--scaffold-demo` が残っていないことの確認
- meaning複合とretry複合がlive葉へ共有pipeline IDを渡さないことの確認
- 既live BATCH-005〜008 / 017に差分がないことの確認
- Attempt 2 で postgres backend までの到達を確認

### 6.5 残リスク / 次アクション

| 優先 | 内容 | 担当 |
| ---- | ---- | ---- |
| high | stg に import 連鎖差分（`product_diff_result`）を用意する、または検証用 `diff_batch_run_id` を指定して 009 を再実行 | Human / AI |
| high | 016 用に実 UUID の `semantic_config_version_id` を用意（workflow input または `BATCH_DISTRIBUTION_METRICS_SEMANTIC_CONFIG_VERSION_ID`） | Human |
| medium | 上記準備後に meaning複合 / distribution-metrics を再dispatchし、本節を SUCCESS 更新 | AI |
| note | apps/batch の scaffold 既定値撤廃は別判断（本Taskは GHA live 配線が主。必要なら scope確認） | Human |

本Taskのworkflow差分（scaffold解除・stg配線・UUID分離）と DB 接続復旧は確認済み。
実データ前提つきの書込成功は上記 high 対応後に再検証する。

## 7. 段階完了状況

| Phase | 状態 | 結果 |
| ----- | ---- | ---- |
| A | 完了 | scaffold / Environment / Run ID差分を確認 |
| B | 完了 | 対象6葉をstg live化 |
| C | 完了 | meaning / retry複合のRun IDを整合 |
| D | 完了 | 005〜008 / 017に意図しない差分なし |
| E | 実施済・PARTIAL | Secret更新後に再dispatch。接続OK。009 empty plan / 016 scaffold UUID で未成功 |

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版。Phase A〜D完了、Phase EはHuman判断待ち |
| 2026-07-30 | Phase E Attempt 1。DB接続失敗を記録 |
| 2026-07-30 | `STG_DATABASE_URL` 更新後 Attempt 2 を記録（PARTIAL） |
