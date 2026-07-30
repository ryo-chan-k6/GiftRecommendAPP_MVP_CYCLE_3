# DB系葉workflow GHA live化結果（C3）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1750](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1750) |
| 関連 Task | [#1751](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1751) / [#1762](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1762) |
| 対象 | BATCH-009 / 010 / 011 / 012 / 013 / 014 / 016 |
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

> 本節は `#1751` 実施時点の記録である。後続 `#1762` では、010を実LLMなしの
> Rule-first DB liveへ変更し、015のみscaffold維持とした。詳細は §6.8.2 を参照する。

## 4. Phase C: meaning複合整合

`batch-item-meaning-generation.yml` では、共有 `pipeline_batch_run_id` を
各葉の `job_run_id` として渡さないよう変更した。

- 009 / 011〜014: 各live葉で新規UUIDを生成
- 010 / 015: scaffoldを維持し、各葉の既定Run IDを使用
- 017: 集計対象として共有 `pipeline_batch_run_id` のみ受け取り、
  自身の `job_run_id` は新規UUIDを生成

上記も `#1751` 実施時点の構成であり、`#1762` 後は010がRule-first DB live、
015がscaffold維持となる。

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

### 6.5 Attempt 3（Object Storage設定修復後）

Attempt 2 の準備不足に対し、Human が以下を実施した。

| 対象 | 内容 |
| ---- | ---- |
| Supabase stg | プロジェクト再作成に伴い Storage バケット `raw-products` を新規作成 |
| Environment `stg` Secret | `OBJECT_STORAGE_ACCESS_KEY` / `OBJECT_STORAGE_SECRET_KEY` を再発行・更新 |
| Environment `stg` Variable | `OBJECT_STORAGE_ENDPOINT` を新プロジェクトへ更新 |

`OBJECT_STORAGE_ENDPOINT` が旧（削除済み）プロジェクトを指していたため、import連鎖の BATCH-003 が
`GRS-RAW-001 object storage put failed (HTTP 410)` で失敗していた。旧エンドポイントは `Project removed.` を返す。

#### import連鎖（データ準備・#1751 scope外の運用行為）

| 項目 | 内容 |
| ---- | ---- |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30550557260 |
| inputs | `max_items=1` |
| conclusion | **success**（全7 job） |
| pipeline `batch_run_id` | `4822002d-ffb5-44a8-af84-f5ecf9535460` |

| Batch | 結果 |
| ----- | ---- |
| BATCH-003 | `status=succeeded storage_backend=http succeeded=2 failed=0` |
| BATCH-005 | `status=succeeded staging_items=1 staging_images=2` |
| BATCH-006 | `status=succeeded upserts=1`（009 が使う `product_diff_result` を生成） |
| BATCH-007 | `status=succeeded upserts=1` |
| BATCH-008 | `status=succeeded`（更新対象なし） |
| BATCH-017 | `status=succeeded insert_applied=True` |

Object Storage の署名リージョンはコード上 `us-east-1` 固定だが、Supabase（`ap-northeast-1`）で
`SignatureDoesNotMatch` は発生せず、live PUT に成功した。region 対応のコード変更は不要と確認できた。

#### meaning複合（009 live 成功 / 011 で停止）

| 項目 | 内容 |
| ---- | ---- |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30550920741 |
| inputs | `max_items=1` |
| conclusion | failure（011 で停止） |

| Job | conclusion | ログ要約 |
| --- | ---------- | -------- |
| `item_generation_queue`（009） | **success** | `BATCH-009 status=succeeded db_reader=postgres db_writer=postgres inserted=1 semantic=1` |
| `item_semantic`（010） | success | `BATCH-010 scaffold demo status=succeeded`（scaffold維持のため live書込なし） |
| `feature_input_hash`（011） | **failure** | `BATCH-011 status=failed hashed=0 skipped=0 failed=0 phases=plan,finalize` |
| 012〜017 | skipped | — |

#### distribution-metrics（016 / UUID問題は解消・別要因で失敗）

| 項目 | 内容 |
| ---- | ---- |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30551184593 |
| inputs | `semantic_config_version_id=a1111111-1111-4111-8111-111111111102`（master seed の固定UUID） |
| conclusion | failure |

ログ要約（secretなし）:

- `InvalidTextRepresentation`（scaffold文字列のUUID非互換）は**解消**
- FK も通過したため、stg DB に master seed / test-data seed が適用済みであることを確認
- 新たに `CheckViolation: new row for relation "feature_distribution_metric" violates check constraint "chk_fdm_normalized_version_when_layer"`

### 6.6 Attempt 3 で判明した構造的課題（事実 / 推論）

| 区分 | 内容 |
| ---- | ---- |
| 事実 | 009 は live で成功し、`item_generation_queue` に `generation_type=semantic` / `queue_status=queued` を1件登録した |
| 事実 | 011 の対象条件は `semantic`+`processing`（主）または `feature`+`queued`（副）である |
| 事実 | 010 は本Task方針により scaffold 維持のため、live DB の queue 状態を `processing` へ進めない |
| 推論 | 010 が scaffold である限り、複合経路で 011 は常に empty plan となる（構造的制約） |
| 事実 | 011 の `resolve_config_version` は `semantic_config_version_id="scaffold-semantic-config-v1"` を固定で返す |
| 事実 | 書込先 `item_feature_input.semantic_config_version_id` は `uuid NOT NULL` + FK である |
| 推論 | 011 は仮にデータがあっても、scaffold 固定値のため live 書込に失敗する |
| 事実 | 同種の scaffold 固定値は 012 / 013（`__main__.py` の `version`）、014（`DEFAULT_EMBEDDING_MODEL_VERSION`）にも存在する |
| 事実 | 016 の `aggregate_feature_metrics` は `value_layer="normalized"` の行を生成する際に `feature_normalization_version_id` を設定していない |
| 事実 | 同ファイルの `aggregate_meaning_metrics` / `aggregate_normalization_metrics` は同項目を伝播している |
| 推論 | 016 の失敗はアプリケーション側の不具合であり、GHA配線とは独立している |

該当箇所:

```105:126:apps/batch/src/batch/application/distribution_metrics/aggregator.py
    for code in MVP_FEATURE_CODES:
        for layer, buckets in (("raw", raw_by_code), ("normalized", norm_by_code)):
            values = buckets.get(code, [])
            if not values:
                continue
            stats = compute_distribution_stats(values)
            rows.append(
                MetricUpsertRow(
                    table="feature_distribution_metric",
                    batch_run_id=batch_run_id,
                    semantic_config_version_id=version,
                    aggregation_scope=agg_scope,
                    aggregation_key=agg_key,
                    value_layer=layer,
                    feature_code=code,
                    sample_count=stats.sample_count,
                    mean=stats.mean,
                    stddev=stats.stddev,
                    min_value=stats.min_value,
                    max_value=stats.max_value,
                )
            )
```

### 6.7 残リスク / 次アクション

| 優先 | 内容 | 担当 |
| ---- | ---- | ---- |
| 完了 | stg に import 連鎖差分（`product_diff_result`）を用意 | Human / AI |
| 完了 | Object Storage 設定を新 Supabase プロジェクトへ追随 | Human |
| 完了 | 016 用の実 UUID `semantic_config_version_id` を特定（master seed 固定値） | Human / AI |
| 完了 | 016 の `feature_normalization_version_id` 未伝播の扱いを判断 → 別Issue化（Human判断 2026-07-30） | Human |
| 完了 | 011〜014 の scaffold 固定 version 撤廃の扱いを判断 → 別Issue化（Human判断 2026-07-30） | Human |
| note | 上記2件はいずれも apps/batch のアプリ実装変更であり、本Task（GHA live 配線）の scope 外 | — |

### 6.8 Human判断結果と後続Issue

2026-07-30、Human により以下を決定した。

| 論点 | 決定 | 後続Issue |
| ---- | ---- | --------- |
| 016 の `aggregate_feature_metrics` 不具合 | 別Issue化する。本Taskは配線検証完了として Human Review へ進む | `#1761` |
| 011〜014 の scaffold 固定 version / 010 scaffold 依存 | 別Issue化する。本Taskでは「GHA配線は live、実行成功は後続」と文書化する | `#1762` |

| Issue | title |
| ----- | ----- |
| `#1761` | `[Task]batch-live-db-lane:BATCH-016 normalized層のfeature_normalization_version_id未伝播修正` |
| `#1762` | `[Task]batch-live-db-lane:BATCH-011〜014 scaffold固定versionの撤廃とlive経路成立` |

いずれも Parent Epic は `#1750`、初期状態は `no-branch` とし、着手時期は Human が判断する。

### 6.8.1 `#1761` 修正・stg live再検証結果

2026-07-30、`#1761` で BATCH-016 の `aggregate_feature_metrics` を修正した。

- `feature_distribution_metric` の raw 層は `feature_normalization_version_id=NULL` のまま、`feature_code` 単位で集計する
- normalized 層は入力 `ItemFeatureRow.feature_normalization_version_id` を出力行へ伝播する
- 同一 `semantic_config_version_id` / `feature_code` の normalized 対象で複数 version が混在した場合、または normalized 値に version がない場合は、DB 書込前に `FeatureMetricAggregationError` で停止する
- Job 層は同例外を既存の入力検証と同じ `GRS-VAL-001` として扱い、`error_log` 記録・`status=failed` で終了する（DB CHECK 違反まで遅延させない）
- 対象 unit test は `32 passed`
- batch unit test 全体は `743 passed`

| 項目 | 内容 |
| ---- | ---- |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30554021305 |
| ref | `fix/task-1761-batch-016-fdm-norm-version` |
| input | master seed の `semantic_config_version_id`（実 UUID） |
| conclusion | **success** |
| BATCH-016 | **success**（CHECK 制約違反を解消し、live DB 書込成功） |
| BATCH-017 | **success** |

### 6.8.2 `#1762` local実装・unit test結果

2026-07-31、BATCH-010〜014 の live 経路で使用する version を
`DbReader` 経由で current master から解決する実装へ変更した。

- Semantic は `semantic_config.config_name=mvp_semantic_config` かつ active な系列を一意に特定し、
  同系列の `semantic_config_version.is_current=true` を解決する
- Feature Normalization は `normalization_method=sigmoid` かつ
  `feature_normalization_version.is_current=true` を解決し、対象 Semantic version に対する
  active `normalization_rule` binding も検証する
- Embedding は `model_version.model_type=embedding` かつ `is_current=true` を解決する
- current の欠落、複数、非UUID、Normalization binding 欠落は、DB書込前に
  `GRS-CFG-001` / `GRS-CFG-002` / `GRS-CFG-003` へ変換して失敗させる
- scaffold固定versionは `--scaffold-demo` 経路に限定し、live Job は解決済みUUIDを使用する
- BATCH-010 workflow は `environment: stg`、`STG_DATABASE_URL`、UUID `job_run_id` を使用し、
  `--scaffold-demo` を付けずにRule-first generatorを実行する。実LLMは呼び出さない
- BATCH-015 は `#1768` まで scaffold を維持する

#### Human判断（2026-07-31）と master seed 追加

AI Review / Test Review で、`normalization_rule` が master seed に存在せず
`resolve_normalization` が stg で必ず失敗する点を Blocker として検出した。
これに対し Human が以下を決定した（[Issue #1762 コメント](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1762#issuecomment-5133050157)）。

| 論点 | 決定 |
| ---- | ---- |
| seed 追加の扱い | DDL 変更なしの最小・冪等 master seed 追加を `#1762` に含める |
| binding 対象 | current semantic config version と current sigmoid feature normalization version を `normalization_rule` で結ぶ |
| fallback | 採用しない。current が解決できない場合は DB 書込前に失敗させる |

これに従い、`supabase/seeds/masters/09_config_versions.sql` へ
`normalization_rule` の binding 登録を追加した。

| 観点 | 内容 |
| ---- | ---- |
| ID 解決 | 固定 UUID をハードコードせず、`semantic_config` / `semantic_config_version` / `feature_normalization_version` の current 行を SELECT で解決する |
| 冪等性 | `ON CONFLICT ON CONSTRAINT uq_normalization_rule_version DO UPDATE` により version あたり 1 行を維持する |
| 非破壊 | 既存 `normalization_rule` 行を DELETE しない。既存行は再 binding のみ行う |
| 追随性 | current `feature_normalization_version` が更新された後の再実行で binding が新 current へ追随する |
| DDL | `supabase/migrations/**` / `db/ddl/**` に差分なし |

local確認結果:

| 確認 | 結果 |
| ---- | ---- |
| BATCH-010〜014 + current resolver + DbReader unit test | `198 passed` |
| `apps/batch/tests/unit` 全体 | `782 passed` |
| 変更workflow 2件のYAML parse | 成功 |
| 使い捨て PostgreSQL 17 + pgvector への migration 適用 | 成功（Supabase Storage 依存の bucket migration のみ local 非適用） |
| 同 DB への master seed 3回適用 | 全ファイル成功 |
| 3回適用後の `normalization_rule` | 1行・`is_active=true`・current sigmoid version を binding |
| 同 DB での resolver 相当 SELECT 5種 | いずれも 1 行を返す |
| 同 DB に対する `PostgresDbReader` + `CurrentVersionResolver` 実行 | semantic / normalization / embedding の 3 UUID を解決できることを確認 |

local DB 検証で、既存 seed の副作用を1件検出した（本Task差分に起因しない）。

| 区分 | 内容 |
| ---- | ---- |
| 事実 | `09_config_versions.sql` の sigmoid `feature_normalization_version` は、`is_current=false` へ落としてから `is_current=true` 行が無い場合に INSERT する構造のため、再実行のたびに新しい version 行が1行増える |
| 事実 | 3回適用後、`feature_normalization_version` は3行、うち current は1行だった |
| 事実 | 追加した `normalization_rule` binding は 3回適用後も1行のまま、最新の current version を指していた |
| 推論 | seed 再実行を繰り返すと未参照の旧 normalization version 行が蓄積する。current 解決と binding には影響しないが、seed の行冪等性としては課題が残る |
| 判断 | 本Taskの out of scope（`normalization_rule` binding 以外の seed 変更）のため、別Issue候補として記録するに留める |

#### `#1762` stg live再検証結果

PR #1772（`fix/task-1762-batch-011-014-live-version`）上で、stgへ
`09_config_versions.sql` を明示適用した後、010〜014を `max_items=1` で順次実行した。

| Batch | Run URL | conclusion | 要約 |
| ----- | ------- | ---------- | ---- |
| 010 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30560538588 | **success** | seed適用成功。`claimed=1 generated=1`（Rule-first、実LLMなし） |
| 011 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30560607388 | **success** | `hashed=1`（empty plan解消） |
| 012 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30560696028 | **success** | `generated=1 item_feature_writes=8` |
| 013 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30560767398 | **success** | `normalized=1 normalized_updates=8 item_meaning_upserts=1` |
| 014 | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30560829983 | **success** | `hashed=1` |

seed適用はBATCH-010葉の opt-in 入力 `apply_config_master_seed=true` でのみ行い、
通常の複合呼出や既定実行では無効のままとした。secret実値は記録していない。
`apply_config_master_seed` step は `postgresql-client` を明示インストールしてから `psql` を実行する
（AI Review should指摘対応）。

meaning複合（009→014一括）の再実行は未実施だが、010〜014の葉liveはすべて成功した。
複合一括の追加実行要否は Human Review で確認する。

### 6.9 本Taskの到達点

| 対象 | 状態 |
| ---- | ---- |
| 対象6葉の `--scaffold-demo` 除去 | 完了 |
| 対象6葉の `environment: stg` / `STG_DATABASE_URL` 配線 | 完了 |
| 葉 `job_run_id` の UUID 化（複合IDとの分離） | 完了 |
| BATCH-009 の stg live 実行 | **成功** |
| 既live BATCH-005〜008 / 017 の回帰 | 影響なし（import連鎖で live 成功を再確認） |
| BATCH-010〜014 の current UUID解決・local unit test | 完了（`#1762`、782 passed） |
| `normalization_rule` binding の master seed 追加 | 完了（`#1762`、local/stgで適用確認） |
| BATCH-010〜014 の stg live 実行 | **成功**（`#1762`、010〜014各1件） |
| BATCH-016 の stg live 実行 | **成功**（`#1761`、run `30554021305`） |

本Taskのworkflow差分（scaffold解除・stg配線・UUID分離）は、009 の live 成功および import連鎖6本の
live 成功によって配線として妥当であることを確認した。
010〜014 の live 書込成功は `#1762` / PR #1772 で確認した。

## 7. 段階完了状況

| Phase | 状態 | 結果 |
| ----- | ---- | ---- |
| A | 完了 | scaffold / Environment / Run ID差分を確認 |
| B | 完了 | 対象6葉をstg live化 |
| C | 完了 | meaning / retry複合のRun IDを整合 |
| D | 完了 | 005〜008 / 017に意図しない差分なし |
| E | 実施済 | 009 / 010〜014 / 016 live 成功。015 liveは `#1768` へ分離 |

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版。Phase A〜D完了、Phase EはHuman判断待ち |
| 2026-07-30 | Phase E Attempt 1。DB接続失敗を記録 |
| 2026-07-30 | `STG_DATABASE_URL` 更新後 Attempt 2 を記録（PARTIAL） |
| 2026-07-30 | Object Storage設定修復後 Attempt 3 を記録。009 live 成功、011・016 の構造的課題を特定 |
| 2026-07-30 | Human判断により 011・016 の課題を `#1761` / `#1762` へ分離し、本Taskの到達点を確定 |
| 2026-07-30 | `#1761` の修正・unit test・stg live 再実行成功を追記 |
| 2026-07-31 | `#1762` のcurrent version resolver、010 Rule-first DB live配線、local unit test結果を追記。stg実行は未実施 |
| 2026-07-31 | `#1762` のAI / Test Review指摘対応。`normalization_rule` master seed追加のHuman判断、local DB検証、unit test件数更新を追記。stg実行は未実施 |
| 2026-07-31 | `#1762` / PR #1772 のstg検証。config seed適用後にBATCH-010〜014が各1件success |
| 2026-07-31 | AI Review指摘対応。`apply_config_master_seed` に `postgresql-client` 導入を追加。meaning複合は葉successを必須証跡とし追加確認は任意と明記 |
