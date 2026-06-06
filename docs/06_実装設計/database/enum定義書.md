# Gift Recommendation Service MVP enum定義書

## 1. ドキュメント情報

| 項目           | 内容                                       |
| -------------- | ------------------------------------------ |
| ドキュメントID | `DB-ENUM-MVP-001`                          |
| ドキュメント名 | Gift Recommendation Service MVP enum定義書 |
| 対象システム   | Gift Recommendation Service MVP            |
| MVP対象        | `yes`                                      |
| 作成日         | 2026-06-07                                 |
| 更新日         | 2026-06-07                                 |

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

DDL Task では CHECK 制約または PostgreSQL ENUM 型名に **論理 ID** を使用する。

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
| Product Diff Status | `diff_status` | state | Staging / Diff | `yes` | |
| Item Active Status | `active_status` | state | Item | `yes` | |
| Item Generation Queue Status | `queue_status` | state | Batch | `yes` | |
| Evaluation Run Status | `evaluation_status` | state | Evaluation | `yes` | |
| Recommendation Request Mode | `request_mode` | application | Request | `yes` | ドメイン docs では `mode` |
| Feedback Target Type | `feedback_target_type` | application | Feedback | `yes` | |
| Log Owner Type | `owner_type` | application | phase_log / error_log | `yes` | polymorphic |
| Feature Code | `feature_code` | semantic | Feature / Meaning | `yes` | MVP 8 軸固定 |
| Item Generation Type | `generation_type` | batch | item_generation_queue | `yes` | 暫定定義（§12） |
| Recommendation Run Phase Name | `phase_name` | batch | phase_log | `yes` | フェーズ識別子 |

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

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
| `semantic` | Semantic | Item Semantic 生成 | BATCH-010 相当 | `yes` | 暫定定義 |
| `feature` | Feature | Item Feature 生成 | BATCH-011〜013 相当 | `yes` | 暫定定義 |
| `embedding` | Embedding | Item Embedding 生成 | BATCH-014〜015 相当 | `yes` | 暫定定義 |

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
| `phase_log` | `phase_name` | `recommendation_run_phase_name` 等 | NOT NULL | Batch フェーズ名は後続拡張 |
| `phase_log` | `owner_type` | `owner_type` | NOT NULL | polymorphic |
| `error_log` | `owner_type` | `owner_type` | NOT NULL | polymorphic |
| `batch_run_log` | `run_status` | `batch_run_status` | NOT NULL | |
| `api_call_log` | `call_status` | `api_call_status` | NOT NULL | |
| `raw_product_metadata` | `import_status` | `raw_import_status` | NOT NULL | |
| `fetch_cursor` | `cursor_status` | `fetch_cursor_status` | NOT NULL | |
| `product_diff_result` | `diff_status` | `product_diff_status` | NOT NULL | |
| `staging_item` | `diff_status` | `product_diff_status` | NULL可 | |
| `item` | `active_status` | `item_active_status` | NOT NULL | |
| `item_generation_queue` | `queue_status` | `item_generation_queue_status` | NOT NULL | |
| `item_generation_queue` | `generation_type` | `item_generation_type` | NOT NULL | 暫定 |
| `evaluation_run` | `evaluation_status` | `evaluation_run_status` | NOT NULL | |
| `feature_definition` | `feature_code` | `feature_code` | NOT NULL | MVP 8 軸 CHECK |
| `item_feature` | `feature_code` | `feature_code` | NOT NULL | feature_definition 参照 |
| `user_feature` | `feature_code` | `feature_code` | NOT NULL | feature_definition 参照 |

---

## 8. API利用箇所

| API | Request / Response | 項目 | enum名 | 備考 |
| --- | ------------------ | ---- | ------ | ---- |
| API-PUB-002 等 | Request | `mode` | `request_mode` | OpenAPI 上は `mode`。DB 列名は `request_mode` |
| API-PUB-004 等 | Request | `feedback_target_type` | `feedback_target_type` | |
| - | Response | `run_status` 等 | 各 state enum | MVP 初期 API では内部状態を直接公開しない設計。Contract Task で再確認 |

---

## 9. code利用箇所

| app / package | ファイル / モジュール | enum名 | 用途 | 備考 |
| ------------- | --------------------- | ------ | ---- | ---- |
| `packages/code-definitions` | `state/*.yaml` 等 | 全 state enum | 正本 | 本 Task で作成 |
| `apps/reco` | Run / Phase 記録 | `recommendation_run_status` 等 | 状態更新 | Phase4b 実装 |
| `apps/batch` | Batch / Import | `batch_run_status` 等 | 状態更新 | Phase4b 実装 |
| `apps/api` | Feedback 保存 | `feedback_*` | Validation | Phase4b 実装 |

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

---

## 11. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DB制約 | CHECK / ENUM 型が code-definitions と一致 | migration |
| 2 | 状態遷移 | 終端状態からの遷移が設計書と一致 | unit |
| 3 | 正本整合 | docs と packages/code-definitions の値一致 | manual |
| 4 | feature_code | MVP 8 軸以外が拒否される | migration |

---

## 12. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `item_generation_type` の暫定値（semantic / feature / embedding） | 入力 docs に明示値が不足 | Human | テーブル定義 Task 前 | Batch パイプラインから推論 |
| 2 | Batch 用 `phase_name` 一覧 | 物理ER §12 未記載 | Human | DDL Task 前 | Run phase のみ本 Task で定義 |
| 3 | `source_type` / `embedding_source_type` | user_feature / item_embedding 列だが物理ER §12 外 | Human | テーブル定義 Task | 本 Task では未定義 |
| 4 | `error_code` 正本化範囲 | Phase4a packages-foundation との分担 | Human | Phase4a 着手前 | error/ は README のみ |

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
- error_code 全件を本 Task で確定していないことが明記されている
- packages/code-definitions のディレクトリ構成がプロジェクトディレクトリ構成定義書 §8.2 と一致している
- secret や `.env` 実値が含まれていない
