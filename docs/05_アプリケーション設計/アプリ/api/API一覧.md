# API一覧

## 1. 概要

### 1.1 目的

本ドキュメントは、Gift Recommendation Service MVP における API 一覧を定義する。

API一覧では、以下を整理する。

- Public API
- Internal API
- External API連携
- Storage連携
- 後続フェーズAPI
- APIごとの責務
- 関連画面
- 関連機能
- 関連リソース
- Request / Response概要
- 主なエラーコード
- trace_id / ログ / メトリクス対象
- MVP対象有無

本ドキュメントは、後続の API仕様書.md、OpenAPI定義、API実装、APIテスト設計のインプットとする。

---

## 2. 利用したインプット成果物

利用したインプット成果物は以下です。

- API設計方針書.md
- 認証・認可設計書.md
- エラーコード定義書.md
- ログ・Observability設計書.md
- リソース一覧.md
- リソース責務定義表.md
- 正本定義表.md
- 論理ER図.md
- 状態遷移設計書.md
- テーブル一覧.md
- 処理構成定義書.md
- 外部商品データ連携設計書.md
- 機能一覧.md
- モジュール一覧.md
- 機能×モジュール対応表.md
- Recoモジュール一覧.md
- 画面一覧.md
- 画面遷移図.md
- RecommendationRequest定義書.md
- RecommendationResult定義書.md
- RecommendationFeedback定義書.md
- Reason生成定義書.md
- Retrieval定義書.md
- Matching定義書.md
- Ranking定義書.md
- Evaluation評価定義書.md
- Feature定義書.md
- Gift Meaning Space定義書.md
- Semantic Concept定義書.md
- Featureルール定義書.md
- Semanticルール定義書.md

---

## 3. API一覧の整理方針

### 3.1 今回の修正反映事項

前回版のAPI一覧では、Python + GitHub Actions で実行するバッチ処理を、以下のような本サービス内Internal APIとして定義していた。

```text
POST /internal/v1/item-features/generation-jobs
POST /internal/v1/item-embeddings/generation-jobs
GET  /internal/v1/batch/health
```

しかし、MVPではバッチ処理は以下の前提で実装する。

```
バッチ処理 = Pythonスクリプトとして実装
実行基盤 = GitHub Actions
```

そのため、バッチ処理そのものはHTTP APIとして定義しない。

本API一覧では、以下のように整理する。

| 区分             | 扱い                                                              |
| ---------------- | ----------------------------------------------------------------- |
| Public API       | webからapiへ呼び出す本サービス提供APIとして定義する               |
| Internal API     | apiからrecoへ呼び出す内部APIとして定義する                        |
| External API連携 | batch / reco が楽天APIやLLM APIを呼び出す外部連携として整理する   |
| Storage連携      | batchがObject StorageへRaw JSONを保存・読取する連携として整理する |
| Pythonバッチ処理 | API一覧ではなく、バッチ設計書・処理構成定義書側で管理する         |

---

### 3.2 API分類一覧

| API分類          | 概要                            | 呼び出し元   | 呼び出し先          | MVP対象 |
| ---------------- | ------------------------------- | ------------ | ------------------- | ------- |
| Public API       | webから呼び出されるAPI          | web          | api                 | 対象    |
| Internal API     | サービス内部コンポーネント間API | api          | reco                | 対象    |
| External API連携 | 外部サービスAPI呼び出し         | batch / reco | 楽天API / LLM API   | 対象    |
| Storage連携      | Object StorageへのRaw保存・読取 | batch        | object storage      | 対象    |
| Admin API        | 管理画面・評価画面向けAPI       | 管理画面     | api                 | 後続    |
| Auth API         | 認証・会員管理API               | web          | api / auth provider | 後続    |

---

### 3.3 APIではなくバッチ設計で管理するもの

以下はAPI一覧ではなく、バッチ設計書または処理構成定義書で管理する。

| 処理                            | 理由                                                 |
| ------------------------------- | ---------------------------------------------------- |
| 楽天商品取得バッチ              | GitHub ActionsからPythonスクリプトとして実行するため |
| Raw保存バッチ                   | HTTP APIではなくbatch内処理として実行するため        |
| Rawメタデータ保存処理           | DB登録処理であり、本サービス提供APIではないため      |
| Staging変換バッチ               | batch内のPython処理として実行するため                |
| Item反映バッチ                  | batch内のPython処理として実行するため                |
| Item Image反映バッチ            | batch内のPython処理として実行するため                |
| Popularity Signal反映バッチ     | batch内のPython処理として実行するため                |
| Item Feature生成バッチ          | batch内のPythonモジュール / jobとして扱うため        |
| Item Embedding生成バッチ        | batch内のPythonモジュール / jobとして扱うため        |
| Feature分布メトリクス集計バッチ | batch内のPython処理として実行するため                |
| 正規化分布メトリクス集計バッチ  | batch内のPython処理として実行するため                |

---

## 4. API設計上の重要方針

| 方針                                     | 内容                                                                                          |
| ---------------------------------------- | --------------------------------------------------------------------------------------------- |
| URLは責務境界を分かりやすく表現する      | Public API / Internal API / 外部連携など、呼び出し元から見た責務が分かるURL設計にする         |
| コンポーネント名の利用は許容する         | `reco` や `batch` などの名称は、API名前空間や内部境界を明確にする目的で利用してよい           |
| ただしAPIでない処理をAPI化しない         | GitHub Actionsで実行するPythonバッチ処理は、無理にInternal APIとして定義しない                |
| URLはリソース指向を基本にする            | `recommendations`、`items`、`recommendation-results`、`masters` などのリソース名を優先する     |
| Command APIを許容する                    | レコメンド実行など、単純なCRUDで表現しづらい処理はCommand APIとして扱う                       |
| GET / POSTを基本にする                   | MVPではPUT / PATCH / DELETEは原則使用しない                                                   |
| 0件結果はエラーにしない                  | レコメンド0件は `200 OK` + empty result として扱う                                            |
| trace_idを伝播する                       | web / api / reco / batch を横断して追跡できるようにする                                       |
| 内部情報は必要以上にPublic APIへ返さない | score_breakdown、model_version_id、reason_basis等は原則Public APIの通常レスポンスには含めない |
| 商品画像URLを扱う                        | 楽天API由来の `mediumImageUrls` / `smallImageUrls` を商品画像参照データとして扱う             |
| MVPでは認証なし                          | 会員登録・ログイン・ユーザー別履歴はMVP対象外                                                 |

---

## 5. MVP対象 Public API一覧

| API ID      | API名             | API分類    | Method | Path                                                 | 呼び出し元     | 呼び出し先 | 関連画面                                                                                          | 関連機能         | 関連リソース                                                                                              | Request概要                                                             | Response概要                                                                | 主なエラーコード                                     | trace_id対象 | ログ対象                        | メトリクス対象                                                                                     | MVP対象 | 備考                                                |
| ----------- | ----------------- | ---------- | ------ | ---------------------------------------------------- | -------------- | ---------- | ------------------------------------------------------------------------------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------------------------------------------------------------- | ---------------------------------------------------- | ------------ | ------------------------------- | -------------------------------------------------------------------------------------------------- | ------- | --------------------------------------------------- |
| API-PUB-001 | APIヘルスチェック | Public API | GET    | `/api/v1/health`                                     | web / 運用確認 | api        | なし                                                                                              | システム稼働確認 | Health                                                                                                    | なし                                                                    | API稼働状態                                                                 | `GRS-COM-*`                                          | 任意         | access                          | api_request_count / api_error_count                                                                | 対象    | 監視・疎通確認用途                                  |
| API-PUB-002 | レコメンド実行    | Public API | POST   | `/api/v1/recommendations`                            | web            | api        | レコメンド条件入力画面 / レコメンド実行中表示 / レコメンド結果一覧画面 / 0件結果表示 / エラー表示 | レコメンド実行   | Recommendation Request / Recommendation Run / Recommendation Result / Recommendation Result Item / Reason | 贈答条件、予算、好み、避けたい条件、NG条件、表示件数等                  | 推薦結果一覧、推薦理由、商品表示情報、外部EC URL、traceId                   | `GRS-REQ-*` / `GRS-REC-*` / `GRS-DB-*` / `GRS-LLM-*` | 必須         | access / phase / error / metric | recommendation_run_count / recommendation_empty_rate / recommendation_latency_ms / candidate_count | 対象    | MVPの中核API。0件は正常系として扱う                 |
| API-PUB-003 | 商品詳細取得      | Public API | GET    | `/api/v1/items/{itemId}`                             | web            | api        | 商品詳細画面 / レコメンド結果一覧画面                                                             | 商品詳細表示     | Item / Item Image / External Item Reference / Popularity Signal                                           | itemId                                                                  | 商品名、商品説明、キャッチコピー、価格、画像URL、外部EC URL、レビュー情報等 | `GRS-ITM-*` / `GRS-DB-*`                             | 必須         | access / error                  | item_detail_request_count / item_not_found_count                                                   | 対象    | 楽天商品ページへの外部遷移に必要な情報を返す        |
| API-PUB-004 | Feedback送信      | Public API | POST   | `/api/v1/recommendation-results/{resultId}/feedback` | web            | api        | Feedback入力表示 / レコメンド結果一覧画面 / 推薦理由詳細表示                                      | Feedback登録     | Recommendation Feedback / Recommendation Result / Recommendation Result Item / Reason                     | resultId、resultItemId、feedbackType、rating、reasonFeedback、comment等 | Feedback受付結果、traceId                                                   | `GRS-FDB-*` / `GRS-REQ-*` / `GRS-DB-*`               | 必須         | access / error / metric         | feedback_count / feedback_error_count / positive_feedback_count / negative_feedback_count          | 対象    | MVPでは匿名Feedbackとして扱う                       |
| API-PUB-005 | Relationshipマスタ取得 | Public API | GET    | `/api/v1/masters/relationships`                        | web            | api        | レコメンド条件入力画面                                                                            | 入力選択肢表示   | Relationship Master / Relationship Rule                                                                 | なし                                                                    | relationship選択肢一覧                                                      | `GRS-CFG-*` / `GRS-DB-*`                             | 任意         | access / error                  | masters_relationships_request_count / masters_relationships_error_count                          | 対象    | 入力画面初期表示で他マスタAPIと並列取得可。Pair情報はPublic API応答に含めず、Reco内部処理またはInternal API側で利用する |
| API-PUB-006 | Occasionマスタ取得     | Public API | GET    | `/api/v1/masters/occasions`                          | web            | api        | レコメンド条件入力画面                                                                            | 入力選択肢表示   | Occasion Master / Occasion Rule                                                                         | なし                                                                    | occasion選択肢一覧                                                          | `GRS-CFG-*` / `GRS-DB-*`                             | 任意         | access / error                  | masters_occasions_request_count / masters_occasions_error_count                                  | 対象    | 同上                                                                                                           |
| API-PUB-007 | Semantic設定取得       | Public API | GET    | `/api/v1/masters/semantic-configs`                   | web            | api        | レコメンド条件入力画面                                                                            | 入力選択肢表示   | Semantic Config                                                                                         | なし                                                                    | Semantic設定スナップショット                                                | `GRS-CFG-*` / `GRS-DB-*`                             | 任意         | access / error                  | masters_semantic_configs_request_count / masters_semantic_configs_error_count                    | 対象    | 同上                                                                                                           |
| API-PUB-008 | Featureルール取得      | Public API | GET    | `/api/v1/masters/feature-rules`                      | web            | api        | レコメンド条件入力画面                                                                            | 入力選択肢表示   | Feature Rule                                                                                            | なし                                                                    | Featureルール一覧                                                           | `GRS-CFG-*` / `GRS-DB-*`                             | 任意         | access / error                  | masters_feature_rules_request_count / masters_feature_rules_error_count                            | 対象    | 同上                                                                                                           |

---

## 6. MVP対象 Internal API一覧

### 6.1 Internal APIの位置づけ

Internal APIは、サービス内部コンポーネント間で呼び出すAPIである。

MVPでは、apiコンポーネントからrecoコンポーネントへオンライン推薦実行を依頼するために利用する。

一方で、batchコンポーネントはPythonスクリプトとしてGitHub Actionsから実行するため、batch自体をHTTP APIとしては定義しない。

---

### 6.2 Internal API一覧

| API ID      | API名              | API分類      | Method | Path                                    | 呼び出し元     | 呼び出し先 | 関連画面                                                               | 関連機能               | 関連リソース                                                                                                                                | Request概要                                                      | Response概要                                                                                         | 主なエラーコード                       | trace_id対象 | ログ対象               | メトリクス対象                                                                         | MVP対象 | 備考                                          |
| ----------- | ------------------ | ------------ | ------ | --------------------------------------- | -------------- | ---------- | ---------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------- | ------------ | ---------------------- | -------------------------------------------------------------------------------------- | ------- | --------------------------------------------- |
| API-INT-001 | Recoヘルスチェック | Internal API | GET    | `/internal/reco/v1/health`              | api / 運用確認 | reco       | なし                                                                   | Reco稼働確認           | Health                                                                                                                                      | なし                                                             | Reco稼働状態                                                                                         | `GRS-COM-*` / `GRS-REC-*`              | 任意         | access                 | reco_health_check_count                                                                | 対象    | recoをFastAPI等の常駐サービスとして動かす前提 |
| API-INT-002 | Reco推薦実行       | Internal API | POST   | `/internal/reco/v1/recommendations/run` | api            | reco       | レコメンド条件入力画面 / レコメンド実行中表示 / レコメンド結果一覧画面 | Recoオンライン推薦実行 | Recommendation Request / Recommendation Run / User Feature / User Meaning / Candidate / Matching / Ranking / Reason / Recommendation Result | 正規化済みRecommendation Request、traceId、requestId、実行mode等 | recommendationRunId、recommendationResultId、resultItems、candidateCounts、warnings、metricSummary等 | `GRS-REC-*` / `GRS-LLM-*` / `GRS-DB-*` | 必須         | phase / error / metric | recommendation_latency_ms / phase_duration_ms / candidate_count / feature_distribution | 対象    | apiからrecoへ推薦パイプライン実行を依頼する。06_実装設計の個別API仕様書（`docs/06_実装設計/api/API-INT-002_Reco推薦実行API仕様書.md`）の正本は本API（API-PUB-002は別Task） |

---

### 6.3 Internal APIとして定義しないもの

以下はMVPではInternal APIとして定義しない。

| 対象                                           | 判断       | 理由                                                                            |
| ---------------------------------------------- | ---------- | ------------------------------------------------------------------------------- |
| `/internal/batch/v1/health`                    | 定義しない | batchはGitHub Actions実行のPythonスクリプトであり、常駐HTTPサービスではないため |
| `/internal/v1/item-features/generation-jobs`   | 定義しない | Item Feature生成はbatch内のPythonジョブとして実行するため                       |
| `/internal/v1/item-embeddings/generation-jobs` | 定義しない | Item Embedding生成はbatch内のPythonジョブとして実行するため                     |
| `/internal/batch/v1/import-runs`               | 定義しない | バッチ起動はGitHub Actionsで管理し、HTTP APIでは受け付けないため                |
| `/internal/batch/v1/rakuten-fetch-runs`        | 定義しない | 楽天API取得はbatchジョブとして実行するため                                      |

---

## 7. External API連携一覧

### 7.1 External API連携の位置づけ

External API連携は、本サービスが外部サービスを呼び出す処理である。

これらは本サービスが提供するAPIではないが、外部依存・エラー・ログ・メトリクス設計上、API一覧で管理対象とする。

---

### 7.2 External API連携一覧

| API ID      | 連携名                        | API分類          | Method | 接続先                 | 呼び出し元   | 呼び出し先 | 関連機能                                 | 関連リソース                                             | Request概要                             | Response概要                                                             | 主なエラーコード                        | trace_id対象 | ログ対象                  | メトリクス対象                                                        | MVP対象 | 備考                                                     |
| ----------- | ----------------------------- | ---------------- | ------ | ---------------------- | ------------ | ---------- | ---------------------------------------- | -------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------------------------ | --------------------------------------- | ------------ | ------------------------- | --------------------------------------------------------------------- | ------- | -------------------------------------------------------- |
| API-EXT-001 | 楽天商品検索API呼び出し       | External API連携 | GET    | 楽天市場商品検索API    | batch        | 楽天API    | 外部商品データ取得                       | External Item / Raw Product / Item / Item Image          | keyword、genreId、page、sort等          | 商品名、商品説明、キャッチコピー、価格、画像URL、商品URL、レビュー情報等 | `GRS-EXT-*` / `GRS-RAW-*` / `GRS-BAT-*` | 必須         | api_call / error / metric | rakuten_item_search_call_count / timeout_count / rate_limit_count     | 対象    | 商品情報の正本取得元                                     |
| API-EXT-002 | 楽天商品ランキングAPI呼び出し | External API連携 | GET    | 楽天商品ランキングAPI  | batch        | 楽天API    | 人気補助シグナル取得                     | Popularity Signal / Ranking Signal / Raw Product         | genreId、period、page等                 | ranking順位、商品識別子、ランキング関連情報                              | `GRS-EXT-*` / `GRS-BAT-*`               | 必須         | api_call / error / metric | rakuten_ranking_call_count / ranking_import_count                     | 対象    | 商品名等は正本取得元にしない。人気補助シグナルとして利用 |
| API-EXT-003 | 楽天ジャンル検索API呼び出し   | External API連携 | GET    | 楽天ジャンル検索API    | batch        | 楽天API    | 外部ジャンル取得                         | External Genre / Genre Mapping / Raw Genre               | genreId等                               | ジャンルID、ジャンル名、親子関係                                         | `GRS-EXT-*` / `GRS-BAT-*`               | 必須         | api_call / error / metric | rakuten_genre_call_count / genre_import_count                         | 対象    | ジャンル階層・商品カテゴリ補助に利用                     |
| API-EXT-004 | OpenAI Embedding API呼び出し  | External API連携 | POST   | OpenAI Embedding API等 | reco / batch | LLM API    | Query Embedding生成 / Item Embedding生成 | Query Embedding / Item Embedding / Model Version         | text、model、metadata等                 | embedding vector                                                         | `GRS-LLM-*` / `GRS-REC-*` / `GRS-BAT-*` | 必須         | error / metric            | embedding_call_count / embedding_failure_count / embedding_latency_ms | 対象    | embedding値そのものはPublic APIに返さない                |
| API-EXT-005 | LLM Semantic抽出API呼び出し   | External API連携 | POST   | LLM API                | reco         | LLM API    | Semantic抽出                             | Semantic Concept / User Feature / Recommendation Request | ユーザー入力テキスト、抽出指示、model等 | 抽出されたsemantic、補助情報                                             | `GRS-LLM-*` / `GRS-REC-*`               | 必須         | error / metric            | llm_call_count / llm_parse_failure_count / llm_latency_ms             | 対象    | MVPでLLM利用範囲を限定する場合はルールベース代替も許容   |

---

## 8. Storage連携一覧

### 8.1 Storage連携の位置づけ

Storage連携は、batchがObject StorageへRaw JSON本体を保存・読取する処理である。

Raw JSON本体はDBではなくObject Storageに保存する。DBには object key / hash / 取得日時 / 取込状態 などのRaw Metadataを保存する。

---

### 8.2 Storage連携一覧

| API ID      | 連携名       | API分類     | Method     | 接続先         | 呼び出し元 | 呼び出し先     | 関連機能                    | 関連リソース                                                | Request概要                   | Response概要        | 主なエラーコード          | trace_id対象 | ログ対象               | メトリクス対象                          | MVP対象 | 備考                                         |
| ----------- | ------------ | ----------- | ---------- | -------------- | ---------- | -------------- | --------------------------- | ----------------------------------------------------------- | ----------------------------- | ------------------- | ------------------------- | ------------ | ---------------------- | --------------------------------------- | ------- | -------------------------------------------- |
| API-STG-001 | Raw JSON保存 | Storage連携 | PUT / POST | Object Storage | batch      | object storage | Raw商品データ保存           | Raw Product Object / Raw Product Metadata                   | Raw JSON、objectKey、metadata | 保存結果、objectKey | `GRS-RAW-*` / `GRS-BAT-*` | 必須         | phase / error / metric | raw_save_count / raw_save_failure_count | 対象    | Raw JSON本体はDBではなくObject Storageへ保存 |
| API-STG-002 | Raw JSON読取 | Storage連携 | GET        | Object Storage | batch      | object storage | Rawデータ読取 / Staging変換 | Raw Product Object / Raw Product Metadata / Staging Product | objectKey                     | Raw JSON            | `GRS-RAW-*` / `GRS-BAT-*` | 必須         | phase / error / metric | raw_read_count / raw_read_failure_count | 対象    | Staging変換時に利用                          |

---

## 9. Pythonバッチ処理との関係

### 9.1 バッチ実行方式

MVPでは、バッチ処理はGitHub ActionsからPythonスクリプトとして実行する。

```
GitHub Actions
  ↓
Python batch script
  ↓
楽天API取得
  ↓
Raw JSON保存
  ↓
Raw Metadata保存
  ↓
Staging変換
  ↓
疑似差分判定
  ↓
Item反映
  ↓
Item Image反映
  ↓
Popularity Signal反映
  ↓
Item Feature生成
  ↓
Item Embedding生成
  ↓
分布メトリクス集計
```

---

### 9.2 API一覧とバッチ処理一覧の分担

| 成果物                       | 管理対象                                                                      |
| ---------------------------- | ----------------------------------------------------------------------------- |
| API一覧.md                   | web→api、api→reco、batch→外部API、batch→Storage のAPI/連携                    |
| バッチ設計方針書.md          | バッチ実行方式、GitHub Actions、ジョブ分割、再実行、排他制御                  |
| バッチ一覧.md                | 楽天商品取得、Staging変換、Item反映、Feature生成、Embedding生成等のジョブ一覧 |
| 処理構成定義書.md            | 各処理モジュールの先行関係、入出力、責務                                      |
| ログ・Observability設計書.md | batch_run_log、api_call_log、phase_log、error_log、メトリクス                 |

---

### 9.3 バッチ処理が利用する連携

| バッチ処理               | 利用するAPI / 連携          |
| ------------------------ | --------------------------- |
| 楽天商品取得バッチ       | 楽天商品検索API             |
| 楽天ランキング取得バッチ | 楽天商品ランキングAPI       |
| 楽天ジャンル取得バッチ   | 楽天ジャンル検索API         |
| Raw保存処理              | Object Storage Raw JSON保存 |
| Raw読取処理              | Object Storage Raw JSON読取 |
| Item Feature生成バッチ   | 必要に応じてLLM API         |
| Item Embedding生成バッチ | OpenAI Embedding API        |
| 分布メトリクス集計バッチ | DB参照・DB保存              |

---

## 10. 後続フェーズ Public API一覧

| API ID      | API名                      | API分類    | Method | Path                                                        | 呼び出し元 | 呼び出し先 | 関連画面                              | 関連機能           | 関連リソース                                                | Request概要                    | Response概要       | 主なエラーコード                        | trace_id対象 | ログ対象                | メトリクス対象                                   | MVP対象           | 備考                                |
| ----------- | -------------------------- | ---------- | ------ | ----------------------------------------------------------- | ---------- | ---------- | ------------------------------------- | ------------------ | ----------------------------------------------------------- | ------------------------------ | ------------------ | --------------------------------------- | ------------ | ----------------------- | ------------------------------------------------ | ----------------- | ----------------------------------- |
| API-FUT-001 | レコメンド履歴一覧取得     | Public API | GET    | `/api/v1/recommendation-history`                            | web        | api        | レコメンド履歴画面                    | レコメンド履歴表示 | Recommendation Result / Recommendation Request / User       | limit、cursor等                | 過去の推薦結果一覧 | `GRS-AUTH-*` / `GRS-RES-*` / `GRS-DB-*` | 必須         | access / error / metric | recommendation_history_request_count             | 後続              | 認証導入後。トップ画面から遷移      |
| API-FUT-002 | レコメンド履歴詳細取得     | Public API | GET    | `/api/v1/recommendation-results/{resultId}`                 | web        | api        | レコメンド結果一覧画面                | 過去推薦結果表示   | Recommendation Result / Recommendation Result Item / Reason | resultId                       | 過去の推薦結果詳細 | `GRS-AUTH-*` / `GRS-RES-*` / `GRS-DB-*` | 必須         | access / error / metric | recommendation_result_detail_count               | 後続              | 履歴画面から結果一覧へ遷移する用途  |
| API-FUT-003 | ユーザーお気に入り登録     | Public API | POST   | `/api/v1/favorite-items`                                    | web        | api        | 商品詳細画面 / レコメンド結果一覧画面 | お気に入り管理     | User / Favorite Item / Item                                 | itemId                         | 登録結果           | `GRS-AUTH-*` / `GRS-ITM-*` / `GRS-DB-*` | 必須         | access / error / metric | favorite_item_count                              | 後続              | 認証導入後                          |
| API-FUT-004 | ユーザーお気に入り一覧取得 | Public API | GET    | `/api/v1/favorite-items`                                    | web        | api        | お気に入り画面                        | お気に入り表示     | User / Favorite Item / Item                                 | limit、cursor等                | お気に入り商品一覧 | `GRS-AUTH-*` / `GRS-DB-*`               | 必須         | access / error / metric | favorite_item_list_count                         | 後続              | 認証導入後                          |
| API-FUT-005 | 外部ECクリック記録         | Public API | POST   | `/api/v1/recommendation-results/{resultId}/external-clicks` | web        | api        | レコメンド結果一覧画面 / 商品詳細画面 | 外部EC遷移計測     | Recommendation Result / Result Item / External Click Event  | resultId、resultItemId、itemId | 記録結果           | `GRS-REQ-*` / `GRS-DB-*`                | 必須         | access / metric         | external_ec_click_count / external_ec_click_rate | 後続またはMVP任意 | MVPで計測したい場合は対象化してよい |

---

## 11. 後続フェーズ Admin / Evaluation API一覧

| API ID      | API名                  | API分類   | Method | Path                                                  | 呼び出し元 | 呼び出し先 | 関連画面               | 関連機能           | 関連リソース                                                                                  | Request概要                              | Response概要                         | 主なエラーコード                        | trace_id対象 | ログ対象                | メトリクス対象                      | MVP対象 | 備考                         |
| ----------- | ---------------------- | --------- | ------ | ----------------------------------------------------- | ---------- | ---------- | ---------------------- | ------------------ | --------------------------------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------ | --------------------------------------- | ------------ | ----------------------- | ----------------------------------- | ------- | ---------------------------- |
| API-ADM-001 | 人手評価タスク一覧取得 | Admin API | GET    | `/api/v1/admin/evaluation-tasks`                      | 管理画面   | api        | 人手評価タスク一覧画面 | 人手評価タスク管理 | Evaluation Task / Recommendation Result                                                       | status、limit、cursor等                  | 評価対象タスク一覧                   | `GRS-AUTH-*` / `GRS-EVL-*` / `GRS-DB-*` | 必須         | access / error / metric | evaluation_task_list_count          | 後続    | 管理者認証が必要             |
| API-ADM-002 | 人手評価入力登録       | Admin API | POST   | `/api/v1/admin/evaluation-tasks/{taskId}/evaluations` | 管理画面   | api        | 人手評価入力画面       | 人手評価登録       | Evaluation Task / Evaluation Result                                                           | taskId、評価結果、コメント等             | 登録結果                             | `GRS-AUTH-*` / `GRS-EVL-*` / `GRS-DB-*` | 必須         | access / error / metric | human_evaluation_count              | 後続    | 管理者認証が必要             |
| API-ADM-003 | Reco品質メトリクス取得 | Admin API | GET    | `/api/v1/admin/reco-metrics`                          | 管理画面   | api        | 管理ダッシュボード画面 | Reco品質監視       | Feature Distribution Metric / Meaning Distribution Metric / Normalization Distribution Metric | dateRange、metricType、featureCode等     | Feature分布、Meaning分布、正規化分布 | `GRS-AUTH-*` / `GRS-MET-*` / `GRS-DB-*` | 必須         | access / error / metric | reco_metric_dashboard_request_count | 後続    | MVP初期はSQL確認で代替       |
| API-ADM-004 | エラーログ検索         | Admin API | GET    | `/api/v1/admin/error-logs`                            | 管理画面   | api        | 管理ダッシュボード画面 | エラーログ確認     | Error Log                                                                                     | traceId、errorCode、service、dateRange等 | エラーログ一覧                       | `GRS-AUTH-*` / `GRS-OBS-*` / `GRS-DB-*` | 必須         | access / error          | error_log_search_count              | 後続    | 内部情報を含むため管理者限定 |
| API-ADM-005 | Batch実行履歴取得      | Admin API | GET    | `/api/v1/admin/batch-runs`                            | 管理画面   | api        | 管理ダッシュボード画面 | Batch監視          | Batch Run Log / Item Import Summary                                                           | batchName、status、batchType、startedAtFrom/startedAtTo（dateRange） | BatchRunSummary[]（batchRunId、batchName、batchType、runStatus、startedAt、completedAt、durationMs、successCount、failedCount、skippedCount、errorSummary※） | `GRS-AUTH-*` / `GRS-BAT-*` / `GRS-DB-*` | 必須         | access / error / metric | batch_run_history_count             | 後続    | 管理者認証必須。公開項目は `batch_run_log_テーブル定義書` §5.6 決定。※errorSummary は failed/partially_succeeded 時のみ（最大500文字）。Import 内訳は詳細 API `importSummaries`（§5.6.2）。OpenAPI は #469 |

---

## 12. Auth API一覧

初回MVPでは認証・認可機能は対象外である。

そのため、以下のAPIは後続フェーズで検討する。

| API ID      | API名            | API分類  | Method | Path                    | 呼び出し元 | 呼び出し先          | 関連画面       | 関連機能         | 関連リソース   | Request概要       | Response概要     | 主なエラーコード | trace_id対象 | ログ対象               | メトリクス対象                       | MVP対象 | 備考      |
| ----------- | ---------------- | -------- | ------ | ----------------------- | ---------- | ------------------- | -------------- | ---------------- | -------------- | ----------------- | ---------------- | ---------------- | ------------ | ---------------------- | ------------------------------------ | ------- | --------- |
| API-AUT-001 | 会員登録         | Auth API | POST   | `/api/v1/auth/sign-up`  | web        | api / auth provider | 会員登録画面   | 認証             | User           | email、password等 | 登録結果         | `GRS-AUTH-*`     | 必須         | access / error / audit | sign_up_count                        | 後続    | MVP対象外 |
| API-AUT-002 | ログイン         | Auth API | POST   | `/api/v1/auth/sign-in`  | web        | api / auth provider | ログイン画面   | 認証             | User / Session | email、password等 | token、user情報  | `GRS-AUTH-*`     | 必須         | access / error / audit | sign_in_count / sign_in_failed_count | 後続    | MVP対象外 |
| API-AUT-003 | ログアウト       | Auth API | POST   | `/api/v1/auth/sign-out` | web        | api / auth provider | ログアウト導線 | 認証             | User / Session | token等           | ログアウト結果   | `GRS-AUTH-*`     | 必須         | access / error / audit | sign_out_count                       | 後続    | MVP対象外 |
| API-AUT-004 | 認証ユーザー取得 | Auth API | GET    | `/api/v1/me`            | web        | api                 | 各画面         | ユーザー情報取得 | User           | なし              | 認証ユーザー情報 | `GRS-AUTH-*`     | 必須         | access / error         | me_request_count                     | 後続    | MVP対象外 |

---

## 13. MVP主導線とAPI対応

### 13.1 画面遷移とAPI呼び出し

| 画面 / 状態            | 主なユーザー操作 | 呼び出すAPI                                               | 備考                                                 |
| ---------------------- | ---------------- | --------------------------------------------------------- | ---------------------------------------------------- |
| トップ画面             | レコメンド開始   | API呼び出しなし                                           | 入力画面へ遷移                                       |
| レコメンド条件入力画面 | 初期表示         | `GET /api/v1/masters/relationships` ほかマスタ系GETを並列呼び出し | `masters` 名前空間で Relationship / Occasion / Semantic Config / Feature Rule を取得する（RESTのPathはフロントURL案 `/recommendations/...` とは別） |
| レコメンド条件入力画面 | レコメンド実行   | `POST /api/v1/recommendations`                            | 入力条件をRecommendation Requestとして送信する       |
| レコメンド実行中表示   | API応答待ち      | `POST /api/v1/recommendations`                            | ローディング状態                                     |
| レコメンド結果一覧画面 | 推薦結果表示     | `POST /api/v1/recommendations` のResponse                 | 結果一覧は実行APIのResponseで表示                    |
| 推薦理由詳細表示       | 理由詳細確認     | API呼び出しなし                                           | Response内のreasonDetailを表示                       |
| 商品詳細画面           | 商品詳細確認     | `GET /api/v1/items/{itemId}`                              | Result内の情報で足りる場合は省略可                   |
| 外部EC商品ページ       | 外部EC遷移       | API呼び出しなし                                           | 楽天商品ページへ外部遷移                             |
| Feedback入力表示       | Feedback送信     | `POST /api/v1/recommendation-results/{resultId}/feedback` | 匿名Feedback                                         |
| 0件結果表示            | 再検索           | API呼び出しなし                                           | 入力画面へ戻る                                       |
| エラー表示             | 再試行           | 対象APIを再実行                                           | traceIdを画面表示候補                                |

---

### 13.2 レコメンド実行API内部連携

> 06_実装設計 個別API仕様書 Task（`prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml`）は、本連携の **ステップ5（API-INT-002）** を正本とする。ステップ1（API-PUB-002）は別Taskで仕様化する。

| ステップ | 処理                                                              | API / 連携                                   |
| -------- | ----------------------------------------------------------------- | -------------------------------------------- |
| 1        | webからapiへレコメンド実行依頼                                    | `POST /api/v1/recommendations`               |
| 2        | apiでRequest Validation                                           | API内部処理                                  |
| 3        | apiでtrace_id / request_id生成                                    | API内部処理                                  |
| 4        | apiでRecommendation Request保存                                   | DB連携                                       |
| 5        | apiからrecoへ推薦実行依頼                                         | `POST /internal/reco/v1/recommendations/run` |
| 6        | recoでRecommendation Run作成                                      | DB連携                                       |
| 7        | recoでSemantic抽出・Feature生成・Retrieval・Matching・Ranking実行 | Reco内部処理                                 |
| 8        | recoでResult / Reason生成                                         | DB連携                                       |
| 9        | recoからapiへ内部結果返却                                         | Internal API Response                        |
| 10       | apiでPublic API Response整形                                      | API内部処理                                  |
| 11       | webへ推薦結果返却                                                 | Public API Response                          |

---

## 14. API別関連リソース一覧

| API ID      | API名                         | 関連リソース                                                                                                                                                             |
| ----------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API-PUB-001 | APIヘルスチェック             | Health                                                                                                                                                                   |
| API-PUB-002 | レコメンド実行                | Recommendation Request / Recommendation Run / Recommendation Result / Recommendation Result Item / Reason / User Feature / User Meaning / Candidate / Matching / Ranking |
| API-PUB-003 | 商品詳細取得                  | Item / Item Image / External Item Reference / Popularity Signal / Genre                                                                                                  |
| API-PUB-004 | Feedback送信                  | Recommendation Feedback / Recommendation Result / Recommendation Result Item / Reason                                                                                    |
| API-PUB-005 | Relationshipマスタ取得        | Relationship Master / Relationship Rule                                                                                                                                 |
| API-PUB-006 | Occasionマスタ取得            | Occasion Master / Occasion Rule                                                                                                                                          |
| API-PUB-007 | Semantic設定取得              | Semantic Config                                                                                                                                                          |
| API-PUB-008 | Featureルール取得             | Feature Rule                                                                                                                                                             |
| API-INT-001 | Recoヘルスチェック            | Health                                                                                                                                                                   |
| API-INT-002 | Reco推薦実行                  | Recommendation Request / Recommendation Run / User Feature / User Meaning / Query Embedding / Candidate / Matching / Ranking / Reason / Recommendation Result            |
| API-EXT-001 | 楽天商品検索API呼び出し       | External Item / Raw Product / Raw Product Metadata / Staging Product / Item / Item Image                                                                                 |
| API-EXT-002 | 楽天商品ランキングAPI呼び出し | Popularity Signal / Ranking Signal / Raw Product Metadata                                                                                                                |
| API-EXT-003 | 楽天ジャンル検索API呼び出し   | External Genre / Genre Mapping                                                                                                                                           |
| API-EXT-004 | OpenAI Embedding API呼び出し  | Query Embedding / Item Embedding / Model Version                                                                                                                         |
| API-EXT-005 | LLM Semantic抽出API呼び出し   | Semantic Concept / User Feature / Recommendation Request                                                                                                                 |
| API-STG-001 | Raw JSON保存                  | Raw Product Object / Raw Product Metadata                                                                                                                                |
| API-STG-002 | Raw JSON読取                  | Raw Product Object / Staging Product                                                                                                                                     |

---

## 15. API別エラーコード方針

| API ID      | API名                         | 主なエラーコード分類                                 | 備考                       |
| ----------- | ----------------------------- | ---------------------------------------------------- | -------------------------- |
| API-PUB-001 | APIヘルスチェック             | `GRS-COM-*`                                          | システム稼働確認           |
| API-PUB-002 | レコメンド実行                | `GRS-REQ-*` / `GRS-REC-*` / `GRS-LLM-*` / `GRS-DB-*` | 0件結果はエラーにしない    |
| API-PUB-003 | 商品詳細取得                  | `GRS-ITM-*` / `GRS-DB-*`                             | 商品が存在しない場合は404  |
| API-PUB-004 | Feedback送信                  | `GRS-FDB-*` / `GRS-REQ-*` / `GRS-DB-*`               | 重複Feedbackは409候補      |
| API-PUB-005 | Relationshipマスタ取得        | `GRS-CFG-*` / `GRS-DB-*`                             | マスタ未設定時は空配列等   |
| API-PUB-006 | Occasionマスタ取得            | `GRS-CFG-*` / `GRS-DB-*`                             | 同上                       |
| API-PUB-007 | Semantic設定取得              | `GRS-CFG-*` / `GRS-DB-*`                             | 同上                       |
| API-PUB-008 | Featureルール取得             | `GRS-CFG-*` / `GRS-DB-*`                             | 同上                       |
| API-INT-001 | Recoヘルスチェック            | `GRS-COM-*` / `GRS-REC-*`                            | Reco稼働確認               |
| API-INT-002 | Reco推薦実行                  | `GRS-REC-*` / `GRS-LLM-*` / `GRS-DB-*`               | Reco内部失敗を追跡         |
| API-EXT-001 | 楽天商品検索API呼び出し       | `GRS-EXT-*` / `GRS-RAW-*` / `GRS-BAT-*`              | Rate Limit / Timeoutを観測 |
| API-EXT-002 | 楽天商品ランキングAPI呼び出し | `GRS-EXT-*` / `GRS-BAT-*`                            | 人気補助シグナル取得失敗   |
| API-EXT-003 | 楽天ジャンル検索API呼び出し   | `GRS-EXT-*` / `GRS-BAT-*`                            | ジャンル取得失敗           |
| API-EXT-004 | OpenAI Embedding API呼び出し  | `GRS-LLM-*`                                          | Embedding生成失敗          |
| API-EXT-005 | LLM Semantic抽出API呼び出し   | `GRS-LLM-*` / `GRS-REC-*`                            | LLM応答Parse失敗を含む     |
| API-STG-001 | Raw JSON保存                  | `GRS-RAW-*` / `GRS-BAT-*`                            | Raw保存失敗                |
| API-STG-002 | Raw JSON読取                  | `GRS-RAW-*` / `GRS-BAT-*`                            | Raw読取失敗                |

---

## 16. API別ログ・Observability方針

| API ID      | API名                         | access_log | phase_log | error_log | api_call_log | metric | 備考                                        |
| ----------- | ----------------------------- | ---------- | --------- | --------- | ------------ | ------ | ------------------------------------------- |
| API-PUB-001 | APIヘルスチェック             | ○          | -         | △         | -            | ○      | 通常は軽量ログ                              |
| API-PUB-002 | レコメンド実行                | ○          | ○         | ○         | -            | ○      | 候補数、0件率、Feature分布、Score分布を観測 |
| API-PUB-003 | 商品詳細取得                  | ○          | -         | ○         | -            | ○      | 商品なし、画像なしを観測                    |
| API-PUB-004 | Feedback送信                  | ○          | -         | ○         | -            | ○      | positive / negative / reason feedbackを観測 |
| API-PUB-005 | Relationshipマスタ取得        | ○          | -         | ○         | -            | ○      | マスタ参照の失敗率を観測                    |
| API-PUB-006 | Occasionマスタ取得            | ○          | -         | ○         | -            | ○      | 同上                                        |
| API-PUB-007 | Semantic設定取得              | ○          | -         | ○         | -            | ○      | 同上                                        |
| API-PUB-008 | Featureルール取得             | ○          | -         | ○         | -            | ○      | 同上                                        |
| API-INT-001 | Recoヘルスチェック            | ○          | -         | △         | -            | ○      | Reco接続確認                                |
| API-INT-002 | Reco推薦実行                  | ○          | ○         | ○         | -            | ○      | Reco内部フェーズを記録                      |
| API-EXT-001 | 楽天商品検索API呼び出し       | -          | ○         | ○         | ○            | ○      | 外部API呼び出し単位で記録                   |
| API-EXT-002 | 楽天商品ランキングAPI呼び出し | -          | ○         | ○         | ○            | ○      | 外部API呼び出し単位で記録                   |
| API-EXT-003 | 楽天ジャンル検索API呼び出し   | -          | ○         | ○         | ○            | ○      | 外部API呼び出し単位で記録                   |
| API-EXT-004 | OpenAI Embedding API呼び出し  | -          | △         | ○         | △            | ○      | LLM API用の呼び出しログを検討               |
| API-EXT-005 | LLM Semantic抽出API呼び出し   | -          | △         | ○         | △            | ○      | LLM API用の呼び出しログを検討               |
| API-STG-001 | Raw JSON保存                  | -          | ○         | ○         | -            | ○      | raw_product_metadataと連携                  |
| API-STG-002 | Raw JSON読取                  | -          | ○         | ○         | -            | ○      | Staging変換と連携                           |

凡例：

| 記号 | 意味                 |
| ---- | -------------------- |
| ○    | 原則記録する         |
| △    | 必要に応じて記録する |
| -    | 原則記録しない       |

---

## 17. API仕様書作成対象の優先順位

### 17.1 MVPで必ず詳細化するAPI

| 優先度 | API ID      | API名              | 理由                                                                  |
| ------ | ----------- | ------------------ | --------------------------------------------------------------------- |
| 1      | API-PUB-002 | レコメンド実行     | MVP中核APIであり、Request / Response / Error / Reco連携の詳細化が必須 |
| 2      | API-INT-002 | Reco推薦実行       | api→reco間の内部契約として重要。試作Task Definition `api-int-002-reco-recommendation-run/api-spec.yaml` の対象 |
| 3      | API-PUB-004 | Feedback送信       | 品質改善データの入口であり、Validationと保存方針が重要                |
| 4      | API-PUB-003 | 商品詳細取得       | 商品詳細画面・外部EC遷移に必要                                        |
| 5      | API-PUB-001 | APIヘルスチェック  | 実装は軽いが運用上必要                                                |
| 6      | API-INT-001 | Recoヘルスチェック | api→reco接続確認に必要                                                |
| 7      | API-PUB-005〜008 | マスタ参照群   | 入力画面初期表示。実装は軽いがOpenAPI契約の固定に必要                  |

---

### 17.2 外部連携として詳細化する対象

| 優先度 | API ID      | 連携名                        | 理由                         |
| ------ | ----------- | ----------------------------- | ---------------------------- |
| 1      | API-EXT-001 | 楽天商品検索API呼び出し       | 商品情報の正本取得元         |
| 2      | API-EXT-002 | 楽天商品ランキングAPI呼び出し | 人気補助シグナル取得元       |
| 3      | API-EXT-003 | 楽天ジャンル検索API呼び出し   | ジャンル情報取得元           |
| 4      | API-STG-001 | Raw JSON保存                  | Raw保存方針の中核            |
| 5      | API-STG-002 | Raw JSON読取                  | Staging変換の前提            |
| 6      | API-EXT-004 | OpenAI Embedding API呼び出し  | Query / Item Embedding生成   |
| 7      | API-EXT-005 | LLM Semantic抽出API呼び出し   | Semantic抽出の実装方式に依存 |

---

### 17.3 後続で詳細化するAPI

| 優先度 | API ID      | API名                      | 理由                          |
| ------ | ----------- | -------------------------- | ----------------------------- |
| 後続   | API-FUT-001 | レコメンド履歴一覧取得     | 認証導入後                    |
| 後続   | API-FUT-002 | レコメンド履歴詳細取得     | 認証導入後                    |
| 後続   | API-FUT-003 | ユーザーお気に入り登録     | 認証導入後                    |
| 後続   | API-FUT-004 | ユーザーお気に入り一覧取得 | 認証導入後                    |
| 後続   | API-FUT-005 | 外部ECクリック記録         | MVPで計測要件が強ければ対象化 |
| 後続   | API-ADM-\*  | Admin / Evaluation API     | 管理・評価機能導入後          |
| 後続   | API-AUT-\*  | Auth API                   | 認証導入後                    |

---

## 18. MVP APIスコープ

### 18.1 MVP対象API

MVPで実装対象とするAPIは以下。

| API ID      | API名                         | Method     | Path / 接続先                                        |
| ----------- | ----------------------------- | ---------- | ---------------------------------------------------- |
| API-PUB-001 | APIヘルスチェック             | GET        | `/api/v1/health`                                     |
| API-PUB-002 | レコメンド実行                | POST       | `/api/v1/recommendations`                            |
| API-PUB-003 | 商品詳細取得                  | GET        | `/api/v1/items/{itemId}`                             |
| API-PUB-004 | Feedback送信                  | POST       | `/api/v1/recommendation-results/{resultId}/feedback` |
| API-PUB-005 | Relationshipマスタ取得        | GET        | `/api/v1/masters/relationships`                        |
| API-PUB-006 | Occasionマスタ取得            | GET        | `/api/v1/masters/occasions`                          |
| API-PUB-007 | Semantic設定取得              | GET        | `/api/v1/masters/semantic-configs`                   |
| API-PUB-008 | Featureルール取得             | GET        | `/api/v1/masters/feature-rules`                      |
| API-INT-001 | Recoヘルスチェック            | GET        | `/internal/reco/v1/health`                           |
| API-INT-002 | Reco推薦実行                  | POST       | `/internal/reco/v1/recommendations/run`              |
| API-EXT-001 | 楽天商品検索API呼び出し       | GET        | 楽天市場商品検索API                                  |
| API-EXT-002 | 楽天商品ランキングAPI呼び出し | GET        | 楽天商品ランキングAPI                                |
| API-EXT-003 | 楽天ジャンル検索API呼び出し   | GET        | 楽天ジャンル検索API                                  |
| API-EXT-004 | OpenAI Embedding API呼び出し  | POST       | OpenAI Embedding API等                               |
| API-EXT-005 | LLM Semantic抽出API呼び出し   | POST       | LLM API                                              |
| API-STG-001 | Raw JSON保存                  | PUT / POST | Object Storage                                       |
| API-STG-002 | Raw JSON読取                  | GET        | Object Storage                                       |

---

### 18.2 MVP対象外API

MVP対象外とするAPIは以下。

| API種別          | 対象外API                                           | 理由                                                    |
| ---------------- | --------------------------------------------------- | ------------------------------------------------------- |
| Auth API         | 会員登録 / ログイン / ログアウト / 認証ユーザー取得 | MVPでは認証機能を対象外とするため                       |
| History API      | レコメンド履歴一覧 / 履歴詳細                       | 認証なしではユーザー別履歴管理ができないため            |
| Favorite API     | お気に入り登録 / 一覧取得                           | 認証導入後の機能であるため                              |
| Admin API        | 管理ダッシュボード / ログ検索 / メトリクス取得      | MVP初期では管理画面を対象外とするため                   |
| Evaluation API   | 人手評価タスク / 人手評価入力                       | 評価運用フェーズで追加するため                          |
| Purchase API     | 購入 / 決済 / 配送                                  | 本サービスのMVP対象外であるため                         |
| Delete API       | 削除系API                                           | MVPでは削除操作を提供しないため                         |
| Batch起動API     | HTTP経由のバッチ起動API                             | MVPではGitHub ActionsからPythonスクリプトを実行するため |
| Batch Health API | `/internal/batch/v1/health` 等                      | batchは常駐HTTPサービスではないため                     |

---

## 19. レビュー観点

| 観点             | 確認内容                                                                         |
| ---------------- | -------------------------------------------------------------------------------- |
| MVP範囲          | MVP対象APIと後続APIが分離されているか                                            |
| API分類          | Public API / Internal API / External API連携 / Storage連携が分離されているか     |
| バッチ整理       | Python + GitHub Actions実行のバッチ処理をInternal APIとして誤定義していないか    |
| URL設計          | API利用者・運用者から見て責務が分かるURLになっているか                           |
| コンポーネント名 | `reco` などの名称を使う場合、API境界・責務境界を表す意味のある名前になっているか |
| HTTPメソッド     | GET / POST中心になっているか                                                     |
| 画面対応         | MVP必須画面から必要なAPIが不足していないか                                       |
| リソース対応     | リソース一覧・リソース責務定義表と対応しているか                                 |
| Reco接続         | api→recoの内部APIが定義されているか                                              |
| 商品画像         | 商品詳細取得・レコメンド結果で画像URLを扱えるか                                  |
| 外部EC遷移       | 楽天商品ページURLを返せるか                                                      |
| Feedback         | Feedback入力表示から保存APIへ接続できるか                                        |
| 0件結果          | 0件結果をエラーではなく正常系として扱えているか                                  |
| Error            | エラーコード定義書と接続できているか                                             |
| Observability    | trace_id、ログ、メトリクス対象が整理されているか                                 |
| External API     | 楽天商品検索API、ランキングAPI、ジャンルAPI、LLM APIが整理されているか           |
| Storage連携      | Raw JSON保存・読取がDB保存ではなくObject Storage連携として整理されているか       |
| 後続拡張         | 認証、履歴、管理、評価APIを後続扱いとして拡張できるか                            |

---

## 20. まとめ

MVPで中心となるAPIは以下である。

| API / 連携                                                | 位置づけ                                         |
| --------------------------------------------------------- | ------------------------------------------------ |
| `GET /api/v1/health`                                      | 監視・疎通確認用Public API                       |
| `GET /api/v1/masters/relationships` 等（API-PUB-005〜008） | レコメンド条件入力画面のマスタ・設定参照       |
| `POST /api/v1/recommendations`                            | ユーザー入力から推薦結果を生成する中核Public API |
| `POST /internal/reco/v1/recommendations/run`              | apiからrecoへ推薦実行を依頼する中核Internal API  |
| `GET /api/v1/items/{itemId}`                              | 商品詳細画面用API                                |
| `POST /api/v1/recommendation-results/{resultId}/feedback` | 推薦品質改善のためのFeedback API                 |
| 楽天商品検索API                                           | 商品情報の正本取得元                             |
| 楽天商品ランキングAPI                                     | 人気補助シグナル取得元                           |
| 楽天ジャンル検索API                                       | ジャンル情報取得元                               |
| OpenAI Embedding API                                      | Query / Item Embedding生成元                     |
| Object Storage Raw保存 / 読取                             | Raw JSON本体の保存・再処理用連携                 |

重要な設計判断は以下である。

| 判断             | 内容                                                                             |
| ---------------- | -------------------------------------------------------------------------------- |
| Public API       | フロントエンドから見た自然なリソース名・操作名を優先する                         |
| Internal API     | api→recoの内部境界を明確にするため、`/internal/reco/v1/...` の名前空間を許容する |
| Batch API        | MVPでは定義しない。batchはGitHub ActionsからPythonスクリプトとして実行する       |
| External API連携 | 楽天API、LLM APIは本サービス外部依存としてAPI一覧で管理する                      |
| Storage連携      | Raw JSON本体はObject Storageへ保存し、DBにはMetadataを保存する                   |
| MVP認証          | 認証なし。ただしInternal APIは保護する                                           |
| 0件結果          | `200 OK` + empty result                                                          |
| 商品画像         | 楽天API由来の画像URLを商品画像参照データとして扱う                               |
| Feedback         | MVPでは匿名Feedbackとして扱う                                                    |
| 後続拡張         | 履歴・お気に入り・管理・評価・認証APIを後続で追加する                            |
