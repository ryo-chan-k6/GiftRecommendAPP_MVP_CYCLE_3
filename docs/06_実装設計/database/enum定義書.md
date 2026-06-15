# Gift Recommendation Service MVP enum定義書

## 1. ドキュメント情報

| 項目           | 内容                                       |
| -------------- | ------------------------------------------ |
| ドキュメントID | `DB-ENUM-MVP-001`                          |
| ドキュメント名 | Gift Recommendation Service MVP enum定義書 |
| 対象システム   | Gift Recommendation Service MVP            |
| MVP対象        | `yes`                                      |
| 作成日         | 2026-06-07                                 |
| 更新日         | 2026-06-12（source_api #506 反映） |

---

## 2. 概要

本ドキュメントは、Gift Recommendation Service MVP において DB 永続化およびアプリケーション横断で利用する **enum / コード値** を定義する。

物理ER §12「状態・enum連携」で列挙した項目を正本化し、機械可読定義は `packages/code-definitions/` に配置する。

---

## 3. 目的

- 物理ER・論理ER・状態遷移設計書の状態値を一意に定義する
- 後続 Task（テーブル定義書 / DDL）が参照できる正本を提供する
- DB / seed / 実装 / テストで同一のコード値意味を共有する

---

## 4. 定義方針

| 観点 | 方針 |
| ---- | ---- |
| 対象範囲 | MVP DB 関連の状態カラム・モード・Feature コード・Batch フェーズ名 |
| 正本 | 本ドキュメント + `packages/code-definitions/**` |
| 命名 | 論理 ID は snake_case。DB 物理列名は各テーブル定義に従う |
| 値の追加 | 後続 enum Task または Phase4a packages-foundation で Human Review 必須 |
| 値の変更 | 破壊的変更。migration + Contract 影響を Human Review |
| 値の削除 | MVP では原則禁止。無効化（`enabled: false`）を検討 |
| DB / API / code連携 | 同一 `code_definition.id` を shared-types / seed 生成のキーとする |

### 4.1 同一 physical 列名の分離

| physical 列名 | 論理 ID | 備考 |
| ------------- | ------- | ---- |
| `run_status` | `recommendation_run_status` | `recommendation_run` 専用 |
| `run_status` | `batch_run_status` | `batch_run_log` 専用 |
| `phase_name` | `recommendation_run_phase_name` | `owner_type` が Run 系のとき |
| `phase_name` | `batch_run_phase_name` | `owner_type = batch_run` 専用 |

DDL Task では CHECK 制約または PostgreSQL ENUM 型名に **論理 ID** を使用する。`phase_log.phase_name` は `owner_type` と組み合わせた CHECK（または同等のアプリ validation）で owner 別の値集合を許可する。

---

## 5. enum一覧

| enum名 | 物理名 | 分類 | 利用箇所 | MVP対象 | 備考 |
| ------ | ------ | ---- | -------- | ------- | ---- |
| Recommendation Run Status | `run_status` | state | Online推薦 | `yes` | id: `recommendation_run_status` |
| Recommendation Result Status | `result_status` | state | Online推薦 | `yes` | |
| Recommendation Feedback Status | `feedback_status` | state | Feedback | `yes` | |
| Phase Status | `phase_status` | state | phase_log | `yes` | Run / Batch / Evaluation 共通 |
| Batch Run Status | `run_status` | state | Batch | `yes` | id: `batch_run_status` |
| API Call Status | `call_status` | state | Batch / 外部API | `yes` | |
| Raw Import Status | `import_status` | state | Raw Metadata | `yes` | |
| Fetch Cursor Status | `cursor_status` | state | Batch | `yes` | |
| Fetch Cursor Type | `cursor_type` | batch | fetch_cursor | `yes` | id: `fetch_cursor_type`。Issue #505 |
| Source API | `source_api` | batch | raw_product_metadata / api_call_log 等 | `yes` | id: `source_api`。Issue #506 |
| Product Diff Status | `diff_status` | state | Staging / Diff | `yes` | |
| Item Active Status | `active_status` | state | Item | `yes` | |
| Item Generation Queue Status | `queue_status` | state | Batch | `yes` | |
| Evaluation Run Status | `evaluation_status` | state | Evaluation | `yes` | |
| Recommendation Request Mode | `request_mode` | application | Request | `yes` | ドメイン docs では `mode` |
| Feedback Target Type | `feedback_target_type` | application | Feedback | `yes` | |
| Log Owner Type | `owner_type` | application | phase_log / error_log | `yes` | polymorphic |
| Feature Code | `feature_code` | semantic | Feature / Meaning | `yes` | MVP 8 軸固定 |
| Item Generation Type | `generation_type` | batch | item_generation_queue | `yes` | Human Review 確定 |
| Recommendation Run Phase Name | `phase_name` | batch | phase_log | `yes` | id: `recommendation_run_phase_name` |
| Batch Run Phase Name | `phase_name` | batch | phase_log | `yes` | id: `batch_run_phase_name` |
| Input Type | `input_type` | semantic | input_type_rule / reco | `yes` | Featureルール §11.1。Issue #477 |
| Application Method | `application_method` | semantic | input_type_rule / reco | `yes` | ディスパッチ先コード。Issue #477 |
| Concept Feature Polarity | `polarity` | semantic | concept_feature_rule | `yes` | API-PUB-008。Issue #476 決定 |

---

## 6. enum値定義

### 6.1 Recommendation Run Status (`recommendation_run_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `accepted` | 受付済 | apiが推薦依頼を受け付け、reco実行対象になった状態 | Run 作成時 | `yes` | 終端状態ではない |
| `running` | 実行中 | recoが推薦処理を開始した状態 | パイプライン開始時 | `yes` | |
| `succeeded` | 成功 | 推薦処理が正常終了した状態 | Result 生成成功時 | `yes` | 終端 |
| `failed` | 失敗 | 推薦処理が異常終了した状態 | 例外・致命的エラー時 | `yes` | 終端 |
| `canceled` | 中止 | タイムアウトや明示的中断 | タイムアウト / 中断時 | `yes` | 終端。MVP では任意 |

### 6.2 Recommendation Result Status (`recommendation_result_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `generated` | 生成済 | 1件以上の推薦結果を生成 | 候補1件以上 | `yes` | 終端。原則更新しない |
| `empty` | 0件 | 推薦結果0件 | Hard Filter / Retrieval / Ranking 後0件 | `yes` | 終端 |
| `failed` | 失敗 | Result生成失敗 | 生成処理失敗時 | `yes` | 終端 |

### 6.3 Recommendation Feedback Status (`recommendation_feedback_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `submitted` | 送信済 | Feedback正常保存 | Validation 成功 | `yes` | 終端 |
| `invalid` | 無効 | Validation エラー | Validation 失敗 | `yes` | 終端 |
| `ignored` | 無視 | 重複・対象不整合 | 保存対象外判定 | `yes` | 終端 |

### 6.4 Phase Status (`phase_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `started` | 開始 | フェーズ開始 | フェーズ着手時 | `yes` | |
| `succeeded` | 成功 | フェーズ正常終了 | 正常完了時 | `yes` | 終端 |
| `failed` | 失敗 | フェーズ失敗 | 異常終了時 | `yes` | 終端 |
| `skipped` | スキップ | 実行不要 | 条件によりスキップ | `yes` | 終端 |

### 6.5 Batch Run Status (`batch_run_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `queued` | 待機 | Batch実行待ち | 起動要求時 | `yes` | |
| `running` | 実行中 | Batch実行中 | 実行開始時 | `yes` | |
| `succeeded` | 成功 | 全体正常終了 | 全処理成功 | `yes` | 終端 |
| `partially_succeeded` | 部分成功 | 一部失敗・処理可能分完了 | 部分失敗時 | `yes` | 終端 |
| `failed` | 失敗 | Batch全体失敗 | 致命的エラー | `yes` | 終端 |
| `canceled` | 中止 | 手動中断・タイムアウト | 中断時 | `yes` | 終端 |

### 6.6 API Call Status (`api_call_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `requested` | 要求済 | 外部APIリクエスト開始 | 呼び出し開始 | `yes` | |
| `succeeded` | 成功 | レスポンス取得成功 | 2xx / 正常 | `yes` | 終端 |
| `failed` | 失敗 | 取得失敗 | 通信・不正レスポンス | `yes` | 終端 |
| `rate_limited` | レート制限 | レート制限により失敗 | 429 等 | `yes` | 終端 |
| `skipped` | スキップ | 呼び出し不要 | 条件によりスキップ | `yes` | 終端 |

### 6.7 Raw Import Status (`raw_import_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `raw_saved` | Raw保存済 | Object Storage へ Raw 保存済 | Raw 保存完了 | `yes` | |
| `staged` | Staging済 | Staging 変換完了 | Staging 完了 | `yes` | |
| `imported` | Import済 | Item 系へ反映完了 | Import 完了 | `yes` | 終端 |
| `skipped` | スキップ | Import 不要 | 差分なし・対象外 | `yes` | 終端 |
| `failed` | 失敗 | Raw 以降の処理失敗 | 処理失敗 | `yes` | 終端 |

### 6.8 Fetch Cursor Status (`fetch_cursor_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `active` | 有効 | 取得対象として有効 | カーソル作成・再開 | `yes` | |
| `paused` | 一時停止 | 一時停止中 | 手動停止 / レート制限 | `yes` | |
| `exhausted` | 走査完了 | 取得範囲走査済 | 範囲完了 | `yes` | 終端 |
| `failed` | 失敗 | カーソル処理失敗 | 更新・取得失敗 | `yes` | 終端 |

### 6.9 Product Diff Status (`product_diff_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `new` | 新規 | 新規商品 | hash 比較で新規 | `yes` | 終端 |
| `updated` | 更新 | 既存商品更新 | hash 変更 | `yes` | 終端 |
| `unchanged` | 変更なし | 変更なし | hash 同一 | `yes` | 終端 |
| `unavailable` | 取得不可 | 商品取得不可 | 販売終了等 | `yes` | 終端 |

### 6.10 Item Active Status (`item_active_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `active` | 有効 | 推薦対象として有効 | 通常商品 | `yes` | |
| `inactive` | 無効 | 一時的に推薦対象外 | 一時停止 | `yes` | |
| `unavailable` | 取得不可 | 外部API上で取得不可 | API 上不存在 | `yes` | 終端 |
| `excluded` | 除外 | 運用・品質理由で除外 | 明示除外 | `yes` | 終端 |

### 6.11 Item Generation Queue Status (`item_generation_queue_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `queued` | 待機 | 生成待ち | キュー登録 | `yes` | |
| `processing` | 処理中 | 生成処理中 | 処理開始 | `yes` | |
| `succeeded` | 成功 | 生成成功 | 正常完了 | `yes` | 終端 |
| `failed` | 失敗 | 生成失敗 | 異常終了 | `yes` | 終端 |
| `skipped` | スキップ | 生成不要 | 再生成不要判定 | `yes` | 終端 |

### 6.12 Evaluation Run Status (`evaluation_run_status`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `queued` | 待機 | 評価実行待ち | 起動要求 | `yes` | |
| `running` | 実行中 | 評価実行中 | 実行開始 | `yes` | |
| `succeeded` | 成功 | 評価正常終了 | 正常完了 | `yes` | 終端 |
| `failed` | 失敗 | 評価異常終了 | 異常終了 | `yes` | 終端 |
| `canceled` | 中止 | 手動中断・タイムアウト | 中断 | `yes` | 終端 |

### 6.13 Recommendation Request Mode (`request_mode`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `ui` | UI | Web UI からの通常推薦 | 画面送信 | `yes` | |
| `evaluation` | 評価 | Evaluation Run からの評価用 | 評価 Batch | `yes` | |
| `batch` | Batch | Batch 一括実行 | Batch 評価 | `yes` | |

### 6.14 Feedback Target Type (`feedback_target_type`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `result` | 結果全体 | Result 全体への Feedback | 結果単位 | `yes` | |
| `item` | 商品 | Result Item への Feedback | 商品単位 | `yes` | |
| `reason` | 理由 | Reason への Feedback | 理由単位 | `yes` | |

### 6.15 Log Owner Type (`owner_type`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `recommendation_request` | Recommendation Request | Request を owner | phase / error log | `yes` | |
| `recommendation_run` | Recommendation Run | Run を owner | phase / error log | `yes` | |
| `recommendation_result` | Recommendation Result | Result を owner | error log | `yes` | |
| `recommendation_feedback` | Recommendation Feedback | Feedback を owner | error log | `yes` | |
| `batch_run` | Batch Run | Batch Run を owner | phase / error log | `yes` | |
| `api_call` | API Call | API Call Log を owner | error log | `yes` | |
| `raw_product_metadata` | Raw Metadata | Raw Metadata を owner | error log | `yes` | |
| `item_generation_queue` | Generation Queue | Queue を owner | error log | `yes` | |
| `evaluation_run` | Evaluation Run | Evaluation Run を owner | phase / error log | `yes` | |
| `system` | System | システム全体 | owner_id NULL 可 | `yes` | |

### 6.16 Feature Code (`feature_code`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `formality` | Formality | Social: フォーマル度 | MVP 8 軸 | `yes` | |
| `safety` | Safety | Social: 外しにくさ | MVP 8 軸 | `yes` | |
| `brand_appropriateness` | Brand Appropriateness | Social: ブランド適合 | MVP 8 軸 | `yes` | |
| `emotion` | Emotion | Symbolic: 感情訴求 | MVP 8 軸 | `yes` | |
| `novelty` | Novelty | Symbolic: 新規性 | MVP 8 軸 | `yes` | |
| `intimacy` | Intimacy | Symbolic: 親密さ | MVP 8 軸 | `yes` | |
| `symbolic_identity` | Symbolic Identity | Symbolic: 象徴的アイデンティティ | MVP 8 軸 | `yes` | |
| `story_richness` | Story Richness | Symbolic: ストーリー性 | MVP 8 軸 | `yes` | |

### 6.17 Item Generation Type (`item_generation_type`)

Human Review にて `semantic` / `feature` / `embedding` の3値を確定した。各値は **パイプライン処理開始区間** を表す。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `semantic` | Semantic | Item Semantic 生成パイプライン区間 | BATCH-010 相当 | `yes` | BATCH-009 初回キュー登録時のデフォルト（フルパイプライン入口） |
| `feature` | Feature | Item Feature 生成パイプライン区間 | BATCH-011〜013 相当 | `yes` | 部分再生成時は該当区間の値でキュー登録 |
| `embedding` | Embedding | Item Embedding 生成パイプライン区間 | BATCH-014〜015 相当 | `yes` | 部分再生成（例: `embedding_source_version` 変更時の Embedding のみ再実行） |

### 6.18 Recommendation Run Phase Name (`recommendation_run_phase_name`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `request_received` | Request Received | 推薦依頼受付 | Run 開始 | `yes` | |
| `config_resolved` | Config Resolved | Config / Version 解決 | Config 解決後 | `yes` | |
| `semantic_extracted` | Semantic Extracted | Semantic 抽出 | 抽出完了 | `yes` | |
| `user_feature_generated` | User Feature Generated | User Feature 生成 | 生成完了 | `yes` | |
| `user_meaning_projected` | User Meaning Projected | User Meaning 射影 | 射影完了 | `yes` | |
| `query_embedding_generated` | Query Embedding Generated | Query Embedding 生成 | 生成完了 | `yes` | |
| `pre_hard_filter_completed` | Pre Hard Filter Completed | Pre Hard Filter 完了 | フィルタ完了 | `yes` | |
| `retrieval_completed` | Retrieval Completed | 候補抽出完了 | Retrieval 完了 | `yes` | |
| `post_hard_filter_completed` | Post Hard Filter Completed | Post Hard Filter 完了 | フィルタ完了 | `yes` | |
| `matching_completed` | Matching Completed | Matching 完了 | Matching 完了 | `yes` | |
| `ranking_completed` | Ranking Completed | Ranking 完了 | Ranking 完了 | `yes` | |
| `result_generated` | Result Generated | Result 生成完了 | Result 生成 | `yes` | |
| `reason_generated` | Reason Generated | Reason 生成完了 | Reason 生成 | `yes` | |
| `response_built` | Response Built | Response 生成完了 | Response 構築 | `yes` | |

### 6.19 Batch Run Phase Name (`batch_run_phase_name`)

正本: ログ・Observability設計書 §10.4。`phase_log` は 1 `batch_run_id` あたり主要フェーズ単位（十数行オーダー）で記録する。`owner_type = batch_run` 時のみ許可する。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `batch_started` | Batch Started | Batch 開始 | Batch 起動 | `yes` | |
| `cursor_loaded` | Cursor Loaded | Fetch Cursor 読込 | カーソル読込完了 | `yes` | |
| `external_api_called` | External API Called | 外部 API 呼び出し | 外部 API 呼び出し | `yes` | |
| `raw_saved` | Raw Saved | Raw JSON 保存 | Raw 保存完了 | `yes` | |
| `raw_metadata_saved` | Raw Metadata Saved | Raw Metadata 保存 | Metadata 保存完了 | `yes` | |
| `staging_transformed` | Staging Transformed | Staging 変換 | Staging 変換完了 | `yes` | |
| `diff_judged` | Diff Judged | 疑似差分判定 | 差分判定完了 | `yes` | |
| `item_imported` | Item Imported | Item 反映 | Item Import 完了 | `yes` | |
| `item_image_imported` | Item Image Imported | Item Image 反映 | Image Import 完了 | `yes` | |
| `popularity_signal_imported` | Popularity Signal Imported | Popularity Signal 反映 | Signal Import 完了 | `yes` | |
| `item_feature_generated` | Item Feature Generated | Item Feature 生成 | Feature 生成完了 | `yes` | |
| `item_embedding_generated` | Item Embedding Generated | Item Embedding 生成 | Embedding 生成完了 | `yes` | |
| `feature_distribution_metric_recorded` | Feature Distribution Metric Recorded | Feature 分布メトリクス記録 | Metric 記録完了 | `yes` | |
| `summary_created` | Summary Created | Import Summary 作成 | Summary 作成完了 | `yes` | |
| `batch_completed` | Batch Completed | Batch 完了 | Batch 正常/異常終了 | `yes` | |

`evaluation_run_phase_name` は本 Task では定義しない。Evaluation 関連テーブル定義 Task（BATCH-018 前）で別途定義する。

### 6.20 Input Type (`input_type`)

正本: Featureルール定義書 §11.1。`input_type_rule` のディスパッチキー。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `relationship` | Relationship | 関係性 | Request relationship ブロック | `yes` | `application_method=relationship_rule` |
| `occasion` | Occasion | 贈答目的 | Request occasion ブロック | `yes` | `application_method=occasion_rule` |
| `preferred_condition` | Preferred Condition | 好み条件 | preferred_text 等 | `yes` | Concept Delta 加算 |
| `non_preferred_condition` | Non-Preferred Condition | 避けたい条件 | non_preferred_text 等 | `yes` | Concept Delta 反転。`invert_delta=true` |
| `ng_condition` | NG Condition | 絶対NG | ng_text 等 | `yes` | Hard Filter。Feature 統合不参加 |
| `budget_condition` | Budget Condition | 予算 | budget 条件 | `yes` | Hard Filter。Feature 統合不参加 |
| `free_text` | Free Text | 自由入力 | free_text | `yes` | Semantic 抽出後適用 |

### 6.21 Application Method (`application_method`)

正本: `input_type_rule_テーブル定義書` §5.1。reco の Rule ディスパッチ分岐キー。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `relationship_rule` | Relationship Rule | Relationship 基準値 Rule へディスパッチ | `input_type=relationship` | `yes` | |
| `occasion_rule` | Occasion Rule | Occasion 基準値 Rule へディスパッチ | `input_type=occasion` | `yes` | |
| `concept_feature_delta_add` | Concept Feature Delta Add | Concept 補正を加算 | `input_type=preferred_condition` | `yes` | |
| `concept_feature_delta_invert` | Concept Feature Delta Invert | Concept 補正を反転適用 | `input_type=non_preferred_condition` | `yes` | `invert_delta=true` 必須（CHECK） |
| `hard_filter_excluded` | Hard Filter Excluded | Feature Rule 非適用 | `input_type` が ng / budget | `yes` | |
| `semantic_extraction_then_apply` | Semantic Extraction Then Apply | 抽出後 Concept Rule 適用 | `input_type=free_text` | `yes` | |

### 6.22 Concept Feature Polarity (`polarity`)

Human Review（Issue #476）にて MVP 候補値を確定した。`feature_delta` の大きさ（0.0〜1.0）に対する符号・方向を表す。packages/code-definitions 正本化は後続 enum Task で実施する。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `positive` | Positive | Feature 値を増加方向に補正 | Concept → Feature delta | `yes` | API-PUB-008 応答例のデフォルト |
| `negative` | Negative | Feature 値を減少方向に補正 | Concept → Feature delta | `yes` | |
| `mixed` | Mixed | 文脈依存・両方向の補正 | Concept → Feature delta | `yes` | reco 適用ロジックは実装 Task で確定 |

### 6.23 Fetch Cursor Type (`fetch_cursor_type`)

Human Review（Issue #505）にて走査戦略 5 値を確定した。`fetch_cursor_テーブル定義書` §5.4 を正とする。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `genre` | Genre | ジャンル別商品検索のページ走査 | BATCH-003・`target_external_genre_id` 必須 | `yes` | |
| `keyword` | Keyword | キーワード検索のページ走査 | BATCH-003・`scope.keyword` 必須 | `yes` | |
| `update_sort` | Update Sort | 更新順ソートによる棚卸し走査 | BATCH-003 | `yes` | |
| `ranking_supplement` | Ranking Supplement | ランキング補完候補の走査 | BATCH-003・BATCH-002 後続 | `yes` | |
| `recheck` | Recheck | 既存商品再確認 | BATCH-004・**1 商品（`external_item_code`）単位** | `yes` | §17.1 No.4 |

### 6.24 Source API (`source_api`)

Human Review（Issue #506）にて外部商品データ連携設計書 §8.4 の 4 値を正本化した。Observability §15.2 の短縮表記（`ranking` / `genre`）は **本 enum を正**とし、物理 DDL では採用しない。

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `item_search` | Item Search | 楽天商品検索API | BATCH-003 / BATCH-004 等 | `yes` | fetch_cursor MVP は本値のみ（テーブル CHECK） |
| `item_ranking` | Item Ranking | 楽天ランキングAPI | BATCH-002 | `yes` | |
| `genre_search` | Genre Search | 楽天ジャンル検索API | BATCH-001 | `yes` | |
| `attribute_search` | Attribute Search | 楽天属性検索API | 将来拡張 | `yes` | MVP では Raw 保存対象外の場合あり |

---

## 7. DB利用箇所

| テーブル | カラム | enum名（論理 ID） | 制約 | 備考 |
| -------- | ------ | ----------------- | ---- | ---- |
| `recommendation_run` | `run_status` | `recommendation_run_status` | NOT NULL | |
| `recommendation_result` | `result_status` | `recommendation_result_status` | NOT NULL | |
| `recommendation_feedback` | `feedback_status` | `recommendation_feedback_status` | NOT NULL | |
| `recommendation_feedback` | `feedback_target_type` | `feedback_target_type` | NOT NULL | |
| `recommendation_request` | `request_mode` | `request_mode` | NOT NULL | |
| `phase_log` | `phase_status` | `phase_status` | NOT NULL | |
| `phase_log` | `phase_name` | `recommendation_run_phase_name` / `batch_run_phase_name` | NOT NULL | `owner_type` と組み合わせた CHECK |
| `phase_log` | `owner_type` | `owner_type` | NOT NULL | polymorphic |
| `error_log` | `owner_type` | `owner_type` | NOT NULL | polymorphic |
| `batch_run_log` | `run_status` | `batch_run_status` | NOT NULL | |
| `api_call_log` | `call_status` | `api_call_status` | NOT NULL | |
| `api_call_log` | `source_api` | `source_api` | NOT NULL | 論理ER §9.2。api_call_log 定義書（別 Task）で転記 |
| `raw_product_metadata` | `import_status` | `raw_import_status` | NOT NULL | |
| `raw_product_metadata` | `source_api` | `source_api` | NOT NULL | Issue #506 確定 |
| `item_import_summary` | `source_api` | `source_api` | NOT NULL | 論理ER §9.2 |
| `fetch_cursor` | `cursor_status` | `fetch_cursor_status` | NOT NULL | |
| `fetch_cursor` | `cursor_type` | `fetch_cursor_type` | NOT NULL | Issue #505 確定 |
| `fetch_cursor` | `source_api` | `source_api` | NOT NULL | fetch_cursor 定義書 §10。MVP CHECK は `item_search` のみ |
| `product_diff_result` | `diff_status` | `product_diff_status` | NOT NULL | `product_diff_result_テーブル定義書` §11 |
| `staging_item` | `diff_status` | `product_diff_status` | NULL可 | `staging_item_テーブル定義書` §17.1 No.4。正本は `product_diff_result`（`product_diff_result_テーブル定義書` §11.2） |
| `item` | `active_status` | `item_active_status` | NOT NULL | |
| `item_generation_queue` | `queue_status` | `item_generation_queue_status` | NOT NULL | |
| `item_generation_queue` | `generation_type` | `item_generation_type` | NOT NULL | Human Review 確定 |
| `evaluation_run` | `evaluation_status` | `evaluation_run_status` | NOT NULL | |
| `feature_definition` | `feature_code` | `feature_code` | NOT NULL | MVP 8 軸 CHECK |
| `item_feature` | `feature_code` | `feature_code` | NOT NULL | feature_definition 参照 |
| `user_feature` | `feature_code` | `feature_code` | NOT NULL | feature_definition 参照 |
| `input_type_rule` | `input_type` | `input_type` | NOT NULL | enum定義書 §6.20 |
| `input_type_rule` | `application_method` | `application_method` | NOT NULL | enum定義書 §6.21。`input_type` と組み合わせ CHECK |
| `concept_feature_rule` | `polarity` | `polarity` | NOT NULL | `chk_polarity_mvp` CHECK。enum定義書 §6.22。Issue #476 決定 |
| `concept_feature_rule` | `feature_code` | `feature_code` | NOT NULL | MVP 8 軸 CHECK |

---

## 8. API利用箇所

| API | Request / Response | 項目 | enum名 | 備考 |
| --- | ------------------ | ---- | ------ | ---- |
| API-PUB-002 等 | Request | `mode` | `request_mode` | OpenAPI 上は `mode`。DB 列名は `request_mode` |
| API-PUB-004 等 | Request | `feedback_target_type` | `feedback_target_type` | |
| - | Response | `run_status` 等 | 各 state enum | MVP 初期 API では内部状態を直接公開しない設計。Contract Task で再確認 |
| API-PUB-008 | Response | `conceptFeatureRules[].polarity` | `polarity` | 任意応答。enum定義書 §6.22 と整合 |

---

## 9. code利用箇所

| app / package | ファイル / モジュール | enum名 | 用途 | 備考 |
| ------------- | --------------------- | ------ | ---- | ---- |
| `packages/code-definitions` | `state/*.yaml` 等 | 全 state enum | 正本 | 本 Task で作成 |
| `apps/reco` | Run / Phase 記録 | `recommendation_run_status` 等 | 状態更新 | Phase4b 実装 |
| `apps/batch` | Batch / Import | `batch_run_status` 等 | 状態更新 | Phase4b 実装 |
| `apps/batch` | Fetch Cursor Manager | `fetch_cursor_type` | 走査種別判定 | Issue #505 |
| `apps/batch` | Raw Product Metadata Writer 等 | `source_api` | API 種別識別 | Issue #506 |
| `apps/api` | Feedback 保存 | `feedback_*` | Validation | Phase4b 実装 |
| `apps/reco` | User Feature 生成ディスパッチ | `input_type` / `application_method` | Rule 経路分岐 | Issue #477 |

---

## 10. 互換性・変更管理

| 変更種別 | 方針 | Human Review |
| -------- | ---- | ------------ |
| 値追加 | 後方互換。migration + docs 更新 | `yes` |
| 値名変更 | 破壊的。migration 必須 | `yes` |
| 値削除 | MVP では原則禁止 | `yes` |
| 意味変更 | 破壊的。状態遷移設計書とセットで更新 | `yes` |

### 10.1 API contract影響

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI影響 | `partial`（`mode` / `feedback_target_type` のみ直接影響） |
| Orval影響 | `false`（本 Task では OpenAPI 未変更） |
| generated影響 | `false` |
| Contract Task要否 | `false`（enum 値確定のみ。OpenAPI enum 化は後続 Contract Task） |
| 補足 | API 公開 enum と DB enum のマッピングは API Contract Task で確認 |

### 10.2 error_code 正本分担

GRS コード全件の重複定義は行わない（参照のみ）。

| レイヤ | 正本 | 担当 |
| ------ | ---- | ---- |
| 人間可読・設計 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | 既存 docs 維持 |
| 機械可読 | `packages/code-definitions/error/*.yaml` | Phase4a packages-foundation |
| DB 物理 | `error_log.error_code` | テーブル定義 / DDL Task |

DB 制約方針:

- エラーコード全件の CHECK 列挙は **行わない**
- **`error_code` 形式 CHECK のみ** を付与する（例: `^GRS-[A-Z]{3}-[0-9]{3}$`）
- 意味・retryable・HTTP status・user message 等は Phase4a YAML + CI 整合で管理する

---

## 11. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DB制約 | CHECK / ENUM 型が code-definitions と一致 | migration |
| 2 | 状態遷移 | 終端状態からの遷移が設計書と一致 | unit |
| 3 | 正本整合 | docs と packages/code-definitions の値一致 | manual |
| 4 | feature_code | MVP 8 軸以外が拒否される | migration |

---

## 12. 未決事項・後続 Task 引き継ぎ

| No | 論点 | 状態 | 判断者 | 備考 |
| --: | ---- | ---- | ------ | ---- |
| 1 | `item_generation_type`（semantic / feature / embedding） | **クローズ**（Human Review 確定） | Human | §6.17・`item_generation_type.yaml` を確定。テーブル定義 Task で意味を転記 |
| 2 | Batch 用 `phase_name`（`batch_run_phase_name`） | **クローズ**（Human Review 確定） | Human | §6.19・Observability §10.4 の15値。物理ER §12 連携済 |
| 3 | `source_type` / `embedding_source_type` | **クローズ**（Issue #516 HR。YAML 正本化は後続） | Human | §12.1・`item_embedding_テーブル定義書` §11。`user_feature.source_type` は §12.1 維持 |
| 4 | `error_code` 正本化範囲 | **クローズ**（Human Review 確定） | Human | §10.2・`error/README.md`。Phase4a へ委譲 |
| 5 | `input_type` / `application_method` | **クローズ**（Issue #477） | Human | §6.20–§6.21・`semantic/input_type.yaml`・`semantic/application_method.yaml` |
| 6 | `polarity`（Concept Feature Polarity） | **クローズ**（Issue #476） | Human | §6.22。packages/code-definitions 正本化は後続 enum Task |
| 7 | `fetch_cursor_type` | **クローズ**（Issue #505） | Human | §6.23・`batch/fetch_cursor_type.yaml`。fetch_cursor テーブル定義書で転記 |
| 8 | `source_api` | **クローズ**（Issue #506） | Human | §6.24・`batch/source_api.yaml`。raw_product_metadata テーブル定義書 §17.1 No.4 |

### 12.1 No.3 方針メモ（テーブル定義 Task 引き継ぎ）

**`user_feature.source_type` → 論理 ID: `user_feature_source_type`**

- MVP は集約1行モデル（1 Recommendation Run × 1 feature_code = 8行）
- 各行の `source_type` は **`aggregated` 固定**
- Relationship / Occasion / Concept 等の寄与分解は MVP では保存しない

**`item_embedding.embedding_source_type` → 論理 ID: `embedding_source_type`**

- `embedding_source_version`（構築ルール version ID）とは **別概念**。MVP では **DB 物理列に持たない**（Human Review #516 §17.1 No.2）
- `embedding_source_version` の変更は **batch 層の Queue 登録トリガー**（`item_generation_queue` §5.6）。永続化は `embedding_source_type` + `embedding_input_hash` + `model_version_id` で行う
- MVP 有効値は **`item_text_context` のみ**（enabled: true）
- **`item_text_with_semantic`** は enum に定義するが MVP 初期は enabled: false

**`item_embedding.embedding_input_hash`**

- 論理ER §10.2・物理ER §11・テーブル一覧 §7 の物理列名は **`embedding_input_hash`**（旧 `source_text_hash` は使用しない。Human Review #516 §17.1 No.1）
- DB 冪等キー（unique）: `item_id` + `model_version_id` + `embedding_input_hash`
- 物理列 `model_version_id` は batch 設計書の `embedding_model_version_id` と同一概念

Semantic ルールの `source_type`（`item_name`, `user_input` 等）とは **別論理 ID** とし、同名 enum の混在を避ける。

---

## 13. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §12 enum 連携 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | 状態カラム一覧 |
| 状態遷移 | `docs/05_アプリケーション設計/アプリ/状態遷移設計書.md` | 状態値・遷移 |
| code-definitions | `packages/code-definitions/` | 機械可読正本 |
| DevOps | `docs/05_アプリケーション設計/共通/DevOps方針書.md` | 運用フロー |

---

## 14. レビュー観点

- 物理ER §12・論理ER 状態一覧・状態遷移設計書と値が一致している
- `recommendation_run_status` と `batch_run_status` が論理 ID で分離されている
- MVP Feature 8 軸が固定されている
- error_code 全件を本 Task で確定していないことが明記されている（§10.2）
- `batch_run_phase_name` が Observability §10.4 と一致している
- `item_generation_type` が Human Review 判断どおり確定されている
- `input_type` / `application_method` が Featureルール §11.1・input_type_rule テーブル定義書と一致している
- `polarity` が concept_feature_rule テーブル定義書・API-PUB-008 と一致している（§6.22）
- `fetch_cursor_type` が fetch_cursor テーブル定義書 §5.4 と一致している（§6.23）
- `source_api` が raw_product_metadata テーブル定義書 §11・外部商品データ連携設計書 §8.4 と一致している（§6.24）
- `embedding_source_type` / `embedding_input_hash` が enum定義書 §12.1・`item_embedding_テーブル定義書` と一致している（Issue #516）
- packages/code-definitions のディレクトリ構成がプロジェクトディレクトリ構成定義書 §8.2 と一致している
- secret や `.env` 実値が含まれていない
