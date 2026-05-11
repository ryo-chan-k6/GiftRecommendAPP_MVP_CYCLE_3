# API設計方針書

## 1. 概要

### 1.1 目的

本ドキュメントは、Gift Recommendation Service MVP における API 設計方針を定義する。

本サービスでは、以下のコンポーネントが API を介して連携する。

- web
- api
- reco
- batch
- database
- object storage
- 外部商品API
- LLM / Embedding API

API設計では、単にエンドポイントを定義するだけではなく、以下を明確にする。

- APIの責務範囲
- Public API / Internal API / External API連携の区分
- URL設計方針
- HTTPメソッド利用方針
- Request / Response設計方針
- Error Response設計方針
- trace_id / request_id の伝播方針
- 認証・認可との接続方針
- ログ・Observabilityとの接続方針
- 後続のAPI一覧、API仕様書、実装設計への引き継ぎ事項

---

## 2. 利用したインプット成果物

利用したインプット成果物は以下です。

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

現時点では、API設計方針書の作成にあたり追加連携が必須となるインプット成果物はない。

ただし、後続で API一覧.md / API仕様書.md を作成する際には、以下の最新版を参照することが望ましい。

- 画面一覧.md
- 画面遷移図.md
- RecommendationRequest定義書.md
- RecommendationResult定義書.md
- RecommendationFeedback定義書.md
- エラーコード定義書.md
- ログ・Observability設計書.md

---

## 3. API設計の基本方針

### 3.1 基本方針

| 方針                               | 内容                                                                      |
| ---------------------------------- | ------------------------------------------------------------------------- |
| Resourceを基準に設計する           | APIパスは原則としてリソース一覧で定義したリソースを基準に設計する         |
| Command APIを許容する              | レコメンド実行など、単純なCRUDでは表現しづらい処理はCommand APIとして扱う |
| MVPではAPI数を増やしすぎない       | 初期MVPでは必要なAPIに絞り、管理系・履歴系は後続扱いとする                |
| Public APIとInternal APIを分離する | webから呼ばれるAPIと、api→reco等の内部APIを明確に分ける                   |
| HTTPメソッドを制限する             | GET / POST を基本とし、PUT / PATCH / DELETE は原則使用しない              |
| Request / Response形式を統一する   | JSON形式、命名規則、エラー形式、traceIdを統一する                         |
| エラーコードを必ず返す             | エラー時はエラーコード定義書の `GRS-*` を返す                             |
| trace_idを伝播する                 | web / api / reco / batch を横断して処理追跡できるようにする               |
| UI表示項目と内部項目を分ける       | score_breakdown等の内部検証項目は原則Public APIで返さない                 |
| 認証なしMVPを前提にする            | 初回MVPではログイン・会員別履歴APIを対象外とする                          |
| 後続拡張を阻害しない               | 認証追加、履歴追加、管理API追加を見据えた設計にする                       |

---

### 3.2 API設計で優先すること

| 優先度 | 内容                                                            |
| ------ | --------------------------------------------------------------- |
| 高     | MVP画面から必要なAPIを確実に定義する                            |
| 高     | Recommendation Request / Result / Feedback の入出力を明確にする |
| 高     | Reco内部APIとの接続責務を明確にする                             |
| 高     | エラーコード・traceId・ログ記録方針を統一する                   |
| 中     | APIバージョン管理を最初から入れる                               |
| 中     | 後続の履歴機能・認証機能に拡張できる余地を残す                  |
| 低     | 管理ダッシュボード用APIをMVP初期から作り込む                    |

---

## 4. API分類

### 4.1 API分類一覧

| API分類             | 呼び出し元             | 呼び出し先               | MVP対象  | 例                                                      |
| ------------------- | ---------------------- | ------------------------ | -------- | ------------------------------------------------------- |
| Public API          | web                    | api                      | 対象     | レコメンド実行、商品詳細取得、Feedback送信              |
| Internal API        | api                    | reco                     | 対象     | 推薦パイプライン実行                                    |
| Batch Internal API  | batch / GitHub Actions | api / database / storage | 一部対象 | 商品データ取込、Feature生成                             |
| External API        | batch                  | 楽天API                  | 対象     | 楽天商品検索API、楽天ランキングAPI、楽天ジャンル検索API |
| LLM / Embedding API | reco / batch           | OpenAI等                 | 対象     | Embedding生成、Semantic抽出                             |
| Admin API           | 管理画面               | api                      | 後続     | 管理ダッシュボード、評価タスク管理                      |
| Auth API            | web                    | api / auth provider      | 後続     | ログイン、会員登録、ログアウト                          |

---

### 4.2 Public API

Public APIは、webフロントエンドから呼び出されるAPIである。

MVPでは以下を主対象とする。

| API領域        | 内容                                             |
| -------------- | ------------------------------------------------ |
| Recommendation | ユーザー入力条件を受け取り、推薦結果を返す       |
| Item           | 推薦結果から商品詳細を表示する                   |
| Feedback       | 推薦結果または推薦商品に対するFeedbackを保存する |
| Health         | API稼働確認を行う                                |

MVPでは以下は対象外とする。

| 対象外API                  | 理由                                           |
| -------------------------- | ---------------------------------------------- |
| Login API                  | 認証機能がMVP対象外のため                      |
| User Profile API           | ユーザー別管理を行わないため                   |
| Recommendation History API | 認証なしではユーザー別履歴を安全に扱えないため |
| Purchase API               | 購入・決済・配送は対象外のため                 |
| Admin API                  | 管理ダッシュボードは後続扱いのため             |

---

### 4.3 Internal API

Internal APIは、apiコンポーネントからrecoコンポーネントなど、サービス内部のコンポーネント間で利用するAPIである。

MVPでは特に以下が重要である。

| Internal API                | 用途                                                     |
| --------------------------- | -------------------------------------------------------- |
| api → reco 推薦実行API      | Recommendation RequestをRecoへ渡し、Result生成を依頼する |
| batch → reco Feature生成API | 必要に応じて商品FeatureやEmbedding生成を依頼する         |
| api / batch → storage       | Raw JSON保存・読取を行う                                 |

Internal APIはPublic APIではないため、外部ユーザーから直接呼び出されない前提とする。

---

### 4.4 External API

External APIは、本サービス外のAPIを呼び出す処理である。

MVPでは楽天市場APIを外部商品データの取得元とする。

| External API          | 用途                             |
| --------------------- | -------------------------------- |
| 楽天商品検索API       | 商品情報の正本取得               |
| 楽天商品ランキングAPI | 人気・ランキング補助シグナル取得 |
| 楽天ジャンル検索API   | ジャンル情報取得                 |
| LLM / Embedding API   | Semantic抽出、Embedding生成      |

External APIは本サービスのAPI仕様として外部公開するものではないが、api_call_log / error_log / batch_run_log の観測対象とする。

---

## 5. URL設計方針

### 5.1 Base URL

APIはバージョンを含むBase Pathを持つ。

| API分類            | Base Path            |
| ------------------ | -------------------- |
| Public API         | `/api/v1`            |
| Internal API       | `/internal/v1`       |
| Reco Internal API  | `/internal/reco/v1`  |
| Batch Internal API | `/internal/batch/v1` |
| Health Check       | `/api/v1/health`     |

---

### 5.2 URL命名規則

| 項目           | 方針                   | 例                                      |
| -------------- | ---------------------- | --------------------------------------- |
| リソース名     | 複数形を基本とする     | `/items`                                |
| 単語区切り     | kebab-case             | `/recommendation-results`               |
| ID指定         | path parameter         | `/items/{itemId}`                       |
| 複雑な検索条件 | POST + request body    | `/recommendations`                      |
| 単純な参照条件 | GET + query parameter  | `/items/{itemId}`                       |
| 内部API        | `/internal` 配下に配置 | `/internal/reco/v1/recommendations/run` |

---

### 5.3 URL設計例

| 用途           | URL例                                                     | 備考                     |
| -------------- | --------------------------------------------------------- | ------------------------ |
| レコメンド実行 | `POST /api/v1/recommendations`                            | MVPの主要API             |
| 商品詳細取得   | `GET /api/v1/items/{itemId}`                              | 商品詳細画面用           |
| Feedback送信   | `POST /api/v1/recommendation-results/{resultId}/feedback` | 推薦結果に対するFeedback |
| API Health     | `GET /api/v1/health`                                      | 稼働確認                 |
| Reco内部実行   | `POST /internal/reco/v1/recommendations/run`              | api→reco内部API          |
| Batch Health   | `GET /internal/batch/v1/health`                           | 後続候補                 |

---

## 6. HTTPメソッド利用方針

### 6.1 利用方針

MVPでは、HTTPメソッドを増やしすぎず、GET / POST を基本とする。

| HTTPメソッド | 利用方針                           | 理由                                      |
| ------------ | ---------------------------------- | ----------------------------------------- |
| GET          | 参照系APIで利用する                | 商品詳細取得、Health Checkなど            |
| POST         | 登録・実行・複雑条件検索で利用する | レコメンド実行、Feedback送信など          |
| PUT          | 原則使用しない                     | 全置換更新のユースケースがMVPで少ないため |
| PATCH        | 原則使用しない                     | 部分更新APIは状態管理が複雑化しやすいため |
| DELETE       | 原則使用しない                     | MVPでは削除操作を提供しないため           |

---

### 6.2 GETを使うケース

GETは、副作用のない参照処理に限定する。

| ケース                   | 例                                   |
| ------------------------ | ------------------------------------ |
| 商品詳細を取得する       | `GET /api/v1/items/{itemId}`         |
| API稼働状態を確認する    | `GET /api/v1/health`                 |
| 後続で履歴一覧を取得する | `GET /api/v1/recommendation-history` |

GETでは、リクエストボディを使わない。

---

### 6.3 POSTを使うケース

POSTは、以下のような処理で利用する。

| ケース                           | 例                 |
| -------------------------------- | ------------------ |
| 新しい処理を実行する             | レコメンド実行     |
| 新しいリソースを作成する         | Feedback登録       |
| 複雑な条件を渡す                 | レコメンド条件入力 |
| Internal APIとして処理を依頼する | api→reco 推薦実行  |

レコメンド実行は、内部的に Recommendation Request / Run / Result を作成するため、POSTを利用する。

---

### 6.4 PUT / PATCH / DELETEを原則使わない理由

| メソッド | 使わない理由                                                 |
| -------- | ------------------------------------------------------------ |
| PUT      | 全体置換が必要なユースケースがMVPにない                      |
| PATCH    | 部分更新は状態整合性・権限管理・監査が複雑になる             |
| DELETE   | MVPではユーザー操作による削除を提供しない                    |
| DELETE   | 物理削除よりも is_active / status による論理管理が中心になる |

後続で管理APIを作成する場合も、削除は原則として物理削除ではなく、無効化・非表示化・状態変更で扱う。

---

## 7. Request設計方針

### 7.1 共通方針

| 方針                      | 内容                                             |
| ------------------------- | ------------------------------------------------ |
| JSON形式を基本とする      | Request Bodyは `application/json` とする         |
| camelCaseを使う           | APIの外部IFではcamelCaseを基本とする             |
| 内部DB名とAPI名を分離する | DB列名がsnake_caseでもAPIではcamelCaseに変換する |
| 必須項目を明確にする      | API仕様書で required を明記する                  |
| enum値を明確にする        | relationship / occasion等は許容値を明記する      |
| 自由入力は文字数制限する  | preferredText / ngText等は最大文字数を設定する   |
| SecretはRequestに含めない | Public APIではAPI Key等を受け取らない            |
| traceIdは原則Headerで扱う | BodyではなくHeader伝播を基本とする               |

---

### 7.2 Request Header方針

| Header               | 用途             | MVP方針                          |
| -------------------- | ---------------- | -------------------------------- |
| `Content-Type`       | Request形式      | `application/json`               |
| `Accept`             | Response形式     | `application/json`               |
| `X-Trace-Id`         | 横断追跡ID       | 任意。未指定ならapi側で生成      |
| `X-Request-Id`       | APIリクエストID  | 任意。未指定ならapi側で生成      |
| `Authorization`      | 認証情報         | MVP Public APIでは原則使用しない |
| `X-Internal-Api-Key` | Internal API保護 | Internal APIで使用候補           |
| `Idempotency-Key`    | 冪等性制御       | MVPでは任意。後続検討            |

---

### 7.3 Request Body方針

| 項目      | 方針                                   |
| --------- | -------------------------------------- |
| 命名      | camelCase                              |
| 日時      | ISO 8601文字列                         |
| 金額      | JPY整数を基本とする                    |
| Feature値 | 0.0〜1.0のnumber                       |
| 配列      | 空配列を許容するかAPIごとに明記        |
| nullable  | 原則避ける。未指定は省略を優先         |
| 自由入力  | 最大文字数、禁止文字、空文字扱いを定義 |
| enum      | 仕様書で許容値を定義                   |
| 内部ID    | Public APIに出すIDは必要最小限にする   |

---

### 7.4 Query Parameter方針

Query Parameterは、単純な参照・絞り込みに限定する。

| 用途         | 例                 |
| ------------ | ------------------ |
| ページング   | `limit`, `cursor`  |
| 表示件数     | `limit`            |
| ソート       | `sort`             |
| 単純フィルタ | `status`, `source` |

複雑な条件指定は、Query ParameterではなくPOST + JSON Bodyで扱う。

---

### 7.5 Path Parameter方針

Path Parameterは、特定リソースを識別する場合に利用する。

| 用途             | 例                                            |
| ---------------- | --------------------------------------------- |
| 商品詳細         | `/items/{itemId}`                             |
| 推薦結果Feedback | `/recommendation-results/{resultId}/feedback` |
| 後続の履歴詳細   | `/recommendation-results/{resultId}`          |

Path Parameterには、自由入力や複雑条件を含めない。

---

## 8. Response設計方針

### 8.1 共通Response方針

| 方針                           | 内容                                              |
| ------------------------------ | ------------------------------------------------- |
| JSON形式を基本とする           | Response Bodyは `application/json`                |
| 成功時と失敗時の形式を統一する | data / error / meta の構造を基本とする            |
| traceIdを返す                  | エラー調査のためResponseにtraceIdを含める         |
| 内部詳細を返さない             | stack trace、SQL、内部設定値は返さない            |
| UI表示対象を明確にする         | Public APIでは画面表示に必要な項目を中心に返す    |
| 内部スコアは原則隠す           | finalScore等はMVP画面に表示しないため原則返さない |
| 必要に応じてmetaを返す         | 件数、traceId、version等はmetaへ配置する          |

---

### 8.2 成功Response形式

成功時の基本形式は以下とする。

| 項目  | 内容                                          |
| ----- | --------------------------------------------- |
| data  | APIの主データ                                 |
| meta  | traceId、requestId、件数、version等の補足情報 |
| error | 成功時は返さない、またはnull                  |

例：概念形式

| 項目             | 内容                     |
| ---------------- | ------------------------ |
| data             | recommendationResultなど |
| meta.traceId     | 横断追跡ID               |
| meta.requestId   | APIリクエストID          |
| meta.generatedAt | 生成日時                 |

---

### 8.3 エラーResponse形式

エラー時の基本形式は以下とする。

| 項目           | 内容                                               |
| -------------- | -------------------------------------------------- |
| error.code     | エラーコード定義書の `GRS-*`                       |
| error.message  | ユーザーまたはフロントエンド向けの安全なメッセージ |
| error.details  | Validationエラー等の安全な補足情報                 |
| meta.traceId   | 横断追跡ID                                         |
| meta.requestId | APIリクエストID                                    |

内部向け詳細は、Responseには返さず、error_logへ記録する。

---

### 8.4 Responseで返さない情報

Public APIでは、以下を原則返さない。

| 項目                 | 理由                                             |
| -------------------- | ------------------------------------------------ |
| DB内部IDの過剰な露出 | 内部構造への依存を避けるため                     |
| stack trace          | セキュリティリスクがあるため                     |
| SQL文                | セキュリティリスクがあるため                     |
| API Key / Secret     | 秘密情報のため                                   |
| score_breakdown      | MVP画面では表示しないため                        |
| model_version_id     | UI表示対象ではないため                           |
| reason_basis         | 内部推論根拠であり、そのまま表示対象ではないため |
| feature詳細値        | MVP画面では表示しないため                        |
| embedding値          | 内部処理専用のため                               |

---

## 9. Status Code方針

### 9.1 HTTP Status Code一覧

| Status | 用途                 | 例                                       |
| ------ | -------------------- | ---------------------------------------- |
| 200    | 正常に参照・処理成功 | 商品詳細取得、レコメンド成功             |
| 201    | リソース作成成功     | Feedback作成。ただしMVPでは200でも可     |
| 202    | 非同期受付           | 後続の非同期Batch API等                  |
| 400    | Request不正          | Validationエラー                         |
| 401    | 未認証               | 後続の認証導入後                         |
| 403    | 権限なし             | 後続の認可導入後                         |
| 404    | リソースなし         | 商品が見つからない                       |
| 409    | 競合                 | Feedback重複など                         |
| 422    | 意味的Validation失敗 | 入力条件はJSONとして正しいが業務的に不正 |
| 429    | Rate Limit           | API呼び出し制限                          |
| 500    | 内部サーバエラー     | 予期しないエラー                         |
| 502    | 外部依存先エラー     | reco / 外部API / LLM失敗                 |
| 503    | 一時利用不可         | DB障害、外部依存停止                     |
| 504    | Timeout              | Reco、LLM、外部APIのTimeout              |

---

### 9.2 0件結果の扱い

レコメンド結果が0件の場合は、原則としてエラーではない。

| 状況                         | Status    | 扱い                   |
| ---------------------------- | --------- | ---------------------- |
| 条件に合う商品がない         | 200       | empty resultとして返す |
| NG条件で全件除外された       | 200       | empty resultとして返す |
| 予算条件が厳しすぎる         | 200       | empty resultとして返す |
| Retrieval処理自体が失敗した  | 500 / 502 | エラーとして返す       |
| DB接続失敗により候補取得不可 | 503       | エラーとして返す       |

0件結果の場合も、traceIdを返し、recommendation_empty_count / recommendation_empty_rate の観測対象とする。

---

## 10. Error設計方針

### 10.1 基本方針

| 方針                                  | 内容                                                |
| ------------------------------------- | --------------------------------------------------- |
| GRSエラーコードを必ず利用する         | エラーコード定義書に従う                            |
| HTTP Statusと業務エラーコードを分ける | HTTPは通信・プロトコル、GRSは業務・内部分類         |
| ユーザー向け文言と内部ログを分ける    | Responseには安全なmessageのみ返す                   |
| traceIdを必ず返す                     | 問い合わせ・調査に利用する                          |
| error_logへ記録する                   | 重要エラーはログ・Observability設計書に従い保存する |

---

### 10.2 エラー分類

| 分類                | 例                           | 代表Status      |
| ------------------- | ---------------------------- | --------------- |
| Validation Error    | 入力不足、型不正、文字数超過 | 400             |
| Business Rule Error | 業務的に受け付けられない条件 | 422             |
| Not Found           | 商品・推薦結果が存在しない   | 404             |
| Conflict            | Feedback重複など             | 409             |
| Auth Error          | 未認証・権限なし             | 401 / 403       |
| Reco Error          | 推薦処理失敗                 | 500 / 502       |
| External API Error  | 楽天API、LLM API失敗         | 502 / 503 / 504 |
| DB Error            | DB接続・書込失敗             | 500 / 503       |
| Rate Limit          | 呼び出し制限                 | 429             |
| Unknown Error       | 予期しないエラー             | 500             |

---

### 10.3 Validation Error方針

Validation Errorでは、ユーザーまたはフロントエンドが修正可能な情報を返す。

返してよい情報は以下。

| 項目             | 例                                                |
| ---------------- | ------------------------------------------------- |
| 対象フィールド   | `budgetMax`                                       |
| エラー種別       | required / invalid_type / too_long / out_of_range |
| 安全なメッセージ | `budgetMax must be greater than budgetMin.`       |

返さない情報は以下。

| 項目                       | 理由               |
| -------------------------- | ------------------ |
| 内部Validatorのstack trace | 不要かつ危険       |
| DB制約名                   | 内部実装依存       |
| SQL                        | セキュリティリスク |

---

## 11. 認証・認可方針

### 11.1 MVP方針

初回MVPでは、認証機能は対象外とする。

そのため、以下はMVP対象外である。

- 会員登録
- ログイン
- ログアウト
- ユーザー別履歴管理
- ユーザー別お気に入り管理
- ユーザー別推薦結果保存表示
- ユーザー権限管理

---

### 11.2 Public APIの扱い

MVPではPublic APIは匿名ユーザーからの呼び出しを許容する。

ただし、以下の最低限の保護は行う。

| 保護            | 内容                                         |
| --------------- | -------------------------------------------- |
| CORS制御        | 許可Originを制限する                         |
| Rate Limit      | 過剰呼び出しを防ぐ                           |
| 入力Validation  | 不正入力・過大入力を防ぐ                     |
| Secret非公開    | webにSecretを持たせない                      |
| ログマスキング  | 自由入力やSecretをログへ出さない             |
| 外部API Key保護 | 楽天API KeyやLLM API Keyはサーバ側で保持する |

---

### 11.3 Internal APIの扱い

Internal APIは、Public APIより強く保護する。

| 方針                       | 内容                                                      |
| -------------------------- | --------------------------------------------------------- |
| 外部公開しない             | Reco Internal APIは外部ユーザーから直接呼べない構成にする |
| Internal API Keyを利用する | `X-Internal-Api-Key` 等で簡易認証する                     |
| Network制限を検討する      | デプロイ環境で可能な範囲で制限する                        |
| Secretをログ出力しない     | HeaderやTokenはログに出さない                             |
| traceIdを伝播する          | Internal APIでもtraceIdを引き継ぐ                         |

---

### 11.4 後続認証導入時の拡張

後続で認証を導入する場合、以下を追加する。

| 項目                       | 内容                       |
| -------------------------- | -------------------------- |
| Authorization Header       | Bearer Token等             |
| User ID                    | 認証済みユーザー識別子     |
| Recommendation History API | ユーザー別履歴取得         |
| Feedback所有者管理         | ユーザー単位のFeedback管理 |
| Rate Limit強化             | IP単位からUser単位へ拡張   |
| Access Control             | 管理APIと一般APIの分離     |

---

## 12. trace_id / request_id 方針

### 12.1 基本方針

APIは、全ての主要リクエストに trace_id / request_id を付与する。

| ID                    | 粒度                          | 用途                               |
| --------------------- | ----------------------------- | ---------------------------------- |
| trace_id              | 1ユーザー操作または1Batch実行 | web / api / reco / batchの横断追跡 |
| request_id            | APIリクエスト単位             | API単体の呼び出し識別              |
| recommendation_run_id | 推薦実行単位                  | Reco内部処理の追跡                 |
| batch_run_id          | Batch実行単位                 | Batch処理の追跡                    |

---

### 12.2 生成・伝播方針

| ケース                 | 方針                                        |
| ---------------------- | ------------------------------------------- |
| webからtraceIdが来ない | apiで新規生成する                           |
| webからtraceIdが来る   | apiで検証し、問題なければ引き継ぐ           |
| apiからrecoを呼ぶ      | traceId / requestIdをHeaderまたはBodyで渡す |
| recoでRunを作成する    | recommendation_run_idとtraceIdを紐づける    |
| エラー発生時           | Responseとerror_logの両方にtraceIdを含める  |
| Batch実行時            | batch起動時にtraceIdを生成する              |

---

### 12.3 ResponseへのtraceId付与

Public APIのResponseには、成功・失敗に関わらずmetaにtraceIdを含める。

| 項目             | 内容             |
| ---------------- | ---------------- |
| meta.traceId     | 横断追跡ID       |
| meta.requestId   | APIリクエストID  |
| meta.generatedAt | Response生成日時 |

---

## 13. Logging / Observability連携方針

### 13.1 APIで記録するログ

API層では以下を記録する。

| ログ            | 内容                               |
| --------------- | ---------------------------------- |
| Access Log      | API呼び出しの概要                  |
| Application Log | 主要イベント                       |
| Error Log       | エラー詳細                         |
| Phase Log       | 必要に応じて処理フェーズ           |
| API Metrics     | latency、error rate、request count |

---

### 13.2 APIログ項目

| 項目        | 内容                     |
| ----------- | ------------------------ |
| timestamp   | 発生日時                 |
| service     | api                      |
| environment | local / dev / production |
| trace_id    | 横断追跡ID               |
| request_id  | APIリクエストID          |
| method      | HTTP Method              |
| path        | API Path                 |
| status_code | HTTP Status              |
| error_code  | GRSエラーコード          |
| duration_ms | 処理時間                 |
| client_type | web / internal / batch   |
| user_agent  | 必要に応じて             |
| ip_hash     | 必要に応じてIPをhash化   |

---

### 13.3 APIメトリクス

| メトリクス             | 内容               |
| ---------------------- | ------------------ |
| api_request_count      | APIリクエスト数    |
| api_success_count      | API成功数          |
| api_error_count        | APIエラー数        |
| api_error_rate         | APIエラー率        |
| api_latency_ms         | API処理時間        |
| validation_error_count | Validationエラー数 |
| reco_call_failed_count | reco呼び出し失敗数 |
| feedback_submit_count  | Feedback送信数     |
| feedback_error_count   | Feedback保存失敗数 |
| rate_limit_count       | Rate Limit発生数   |

---

### 13.4 ログ出力禁止情報

APIログには以下を出力しない。

| 情報                   | 理由                                 |
| ---------------------- | ------------------------------------ |
| Authorization Header   | 認証情報のため                       |
| Cookie全文             | セッション情報を含む可能性があるため |
| API Key                | Secretのため                         |
| DATABASE_URL           | Secretのため                         |
| OPENAI_API_KEY         | Secretのため                         |
| RAKUTEN_APPLICATION_ID | Secretのため                         |
| 自由入力全文           | 個人情報を含む可能性があるため       |
| Stack Trace全文        | 内部情報を含むため                   |
| SQL文全文              | 内部構造を含むため                   |

---

## 14. API Validation方針

### 14.1 基本方針

API層では、Requestを受け付けた時点でValidationを行う。

| 種別                    | 内容                                 |
| ----------------------- | ------------------------------------ |
| 構文Validation          | JSON形式、型、必須項目               |
| 形式Validation          | 文字数、数値範囲、enum               |
| 業務Validation          | budgetMin <= budgetMax など          |
| セキュリティValidation  | 過大入力、危険文字、想定外フィールド |
| Internal API Validation | api→reco間の契約確認                 |

---

### 14.2 Recommendation Request Validation

Recommendation Requestでは、以下を検証する。

| 項目             | Validation                               |
| ---------------- | ---------------------------------------- |
| relationship     | 許容enum値であること                     |
| occasion         | 許容enum値であること                     |
| budgetMin        | 0以上の整数                              |
| budgetMax        | budgetMin以上の整数                      |
| preferredText    | 最大文字数以内                           |
| nonPreferredText | 最大文字数以内                           |
| ngText           | 最大文字数以内                           |
| recipientInfo    | MVPで必要な範囲のみ許容                  |
| topK             | 許容範囲内                               |
| mode             | `ui` / `evaluation` / `batch` 等の許容値 |

---

### 14.3 Feedback Validation

Feedbackでは、以下を検証する。

| 項目           | Validation                               |
| -------------- | ---------------------------------------- |
| resultId       | 必須                                     |
| resultItemId   | 任意または必須。Feedback粒度に応じて決定 |
| feedbackType   | 許容enum値                               |
| rating         | 許容範囲内                               |
| comment        | 最大文字数以内                           |
| reasonFeedback | 許容enum値                               |
| duplicate      | 同一対象への重複Feedbackを制御           |

---

## 15. Pagination / Sorting方針

### 15.1 Pagination方針

MVPでは一覧APIは少ないが、後続拡張を見据え、一覧APIではCursor Paginationを基本とする。

| 項目       | 方針                       |
| ---------- | -------------------------- |
| limit      | 取得件数                   |
| cursor     | 次ページ取得用cursor       |
| nextCursor | Response側の次ページcursor |
| hasMore    | 次ページ有無               |

---

### 15.2 Sorting方針

Sortingは、API仕様書で許容値を明記する。

| 例              | 内容         |
| --------------- | ------------ |
| `createdAtDesc` | 作成日時降順 |
| `priceAsc`      | 価格昇順     |
| `priceDesc`     | 価格降順     |
| `rankAsc`       | 推薦順位昇順 |

MVPの推薦結果一覧は、原則としてRanking結果の順序をそのまま返す。

---

## 16. API Versioning方針

### 16.1 基本方針

APIはURLパスにバージョンを含める。

| バージョン     | 用途                |
| -------------- | ------------------- |
| `/api/v1`      | MVP初期Public API   |
| `/internal/v1` | MVP初期Internal API |

---

### 16.2 バージョン変更が必要なケース

| ケース                   | Version変更要否          |
| ------------------------ | ------------------------ |
| Response項目の追加       | 原則不要                 |
| 任意Request項目の追加    | 原則不要                 |
| 必須Request項目の追加    | 要検討                   |
| Response構造の破壊的変更 | 必要                     |
| enum値の削除             | 必要                     |
| エラー形式の変更         | 必要                     |
| 認証方式の必須化         | 必要または移行期間が必要 |

---

### 16.3 後方互換性方針

| 方針                       | 内容                               |
| -------------------------- | ---------------------------------- |
| 項目追加は互換扱い         | Optional項目追加はv1内で許容       |
| 既存項目の意味変更は避ける | 同じ項目名で意味を変えない         |
| enum削除は避ける           | 削除ではなくdeprecated扱いを検討   |
| 破壊的変更はv2へ           | Frontend影響が大きい変更はv2で扱う |

---

## 17. API Data Format方針

### 17.1 命名規則

| 対象        | 方針        | 例                         |
| ----------- | ----------- | -------------------------- |
| API Field   | camelCase   | `recommendationResultId`   |
| DB Column   | snake_case  | `recommendation_result_id` |
| JSON Object | camelCase   | `reasonSummary`            |
| Enum Value  | snake_case  | `very_good`                |
| URL Path    | kebab-case  | `/recommendation-results`  |
| Header      | Header-Case | `X-Trace-Id`               |

---

### 17.2 日時形式

| 項目     | 方針                       |
| -------- | -------------------------- |
| API日時  | ISO 8601                   |
| Timezone | UTCを基本                  |
| 表示時刻 | web側で必要に応じてJST変換 |
| DB保存   | UTC                        |

例：

| 用途        | 形式                       |
| ----------- | -------------------------- |
| generatedAt | `2026-05-11T12:00:00.000Z` |
| createdAt   | `2026-05-11T12:00:00.000Z` |

---

### 17.3 金額形式

| 項目      | 方針                                   |
| --------- | -------------------------------------- |
| 通貨      | MVPではJPY                             |
| 金額      | 整数                                   |
| 税込/税抜 | 楽天API由来項目に従う。API仕様書で明記 |
| 表示整形  | web側で行う                            |

---

### 17.4 URL形式

商品画像や外部ECリンクは、URL文字列として返す。

| 項目            | 方針                     |
| --------------- | ------------------------ |
| itemImageUrl    | 楽天API由来の商品画像URL |
| mediumImageUrls | 必要に応じて配列         |
| smallImageUrls  | 必要に応じて配列         |
| externalItemUrl | 外部EC商品ページURL      |
| 画像バイナリ    | APIでは返さない          |

---

## 18. Recommendation API方針

### 18.1 位置づけ

Recommendation APIは、MVPの中核APIである。

ユーザー入力条件を受け取り、以下を内部的に実行する。

1. Recommendation Request作成
2. Recommendation Run作成
3. Reco Internal API呼び出し
4. Recommendation Result生成
5. Recommendation Result Item生成
6. Reason生成
7. Response返却

---

### 18.2 API方針

| 項目        | 方針                                                     |
| ----------- | -------------------------------------------------------- |
| Endpoint    | `POST /api/v1/recommendations`                           |
| API分類     | Public API                                               |
| 処理種別    | Command API                                              |
| 同期/非同期 | MVPでは同期Responseを基本                                |
| Request     | Recommendation Request定義書に従う                       |
| Response    | Recommendation Result定義書に従う                        |
| 0件結果     | 200 + empty result                                       |
| エラー      | GRSエラーコード + traceId                                |
| ログ        | recommendation_run / phase_log / error_log               |
| メトリクス  | latency、candidate_count、empty_rate、score_distribution |

---

### 18.3 Response表示対象

レコメンド結果一覧画面に返す主な表示対象は以下。

| 項目            | 表示対象                   |
| --------------- | -------------------------- |
| rank            | 表示する                   |
| itemImageUrl    | 表示する                   |
| itemName        | 表示する                   |
| itemCatchcopy   | 表示する                   |
| price           | 表示する                   |
| reasonBadges    | 表示する                   |
| reasonSummary   | 表示する                   |
| reasonDetail    | 推薦理由詳細表示で表示する |
| reasonPoints    | 推薦理由詳細表示で表示する |
| cautionNote     | 必要に応じて表示する       |
| externalItemUrl | 外部EC遷移ボタンで利用する |
| itemDetail      | 商品詳細画面で利用する     |

---

### 18.4 Responseで原則返さない項目

| 項目                    | 理由                    |
| ----------------------- | ----------------------- |
| finalScore              | MVP画面で表示しないため |
| scoreBreakdown          | 内部検証用のため        |
| modelVersionId          | UI表示対象ではないため  |
| semanticConfigVersionId | UI表示対象ではないため  |
| reasonBasis             | 内部根拠のため          |
| rawFeatureValues        | 内部処理用のため        |
| embedding               | 内部処理用のため        |

必要な場合は、debug modeまたは管理者向けAPIで別途扱う。

---

## 19. Item API方針

### 19.1 位置づけ

Item APIは、商品詳細画面で利用する。

MVPでは、推薦結果から商品詳細へ遷移する導線があるため、商品情報を取得できるAPIを用意する。

---

### 19.2 API方針

| 項目       | 方針                         |
| ---------- | ---------------------------- |
| Endpoint   | `GET /api/v1/items/{itemId}` |
| API分類    | Public API                   |
| 処理種別   | Query API                    |
| 対象       | 本サービス管理対象商品       |
| 外部商品   | MVPでは楽天市場商品のみ      |
| 画像       | 楽天API由来の画像URLを返す   |
| 外部EC遷移 | externalItemUrlを返す        |
| エラー     | 商品が存在しない場合404      |

---

### 19.3 Item API Response項目候補

| 項目               | 内容                         |
| ------------------ | ---------------------------- |
| itemId             | 商品ID                       |
| source             | rakuten                      |
| externalItemId     | 楽天商品IDまたはitemCode     |
| itemName           | 商品名                       |
| itemCaption        | 商品説明                     |
| itemCatchcopy      | キャッチコピー               |
| price              | 価格                         |
| itemImageUrls      | 商品画像URL配列              |
| mediumImageUrls    | 楽天API由来の中サイズ画像URL |
| smallImageUrls     | 楽天API由来の小サイズ画像URL |
| externalItemUrl    | 楽天商品ページURL            |
| genreId            | 楽天ジャンルID               |
| reviewAverage      | レビュー平均                 |
| reviewCount        | レビュー件数                 |
| availabilityStatus | 推薦対象状態                 |

---

## 20. Feedback API方針

### 20.1 位置づけ

Feedback APIは、レコメンド結果に対するユーザー反応を保存するAPIである。

Feedbackは、後続の推薦品質改善・評価・分析に利用する重要データである。

---

### 20.2 API方針

| 項目       | 方針                                                      |
| ---------- | --------------------------------------------------------- |
| Endpoint   | `POST /api/v1/recommendation-results/{resultId}/feedback` |
| API分類    | Public API                                                |
| 処理種別   | Command API                                               |
| 対象       | Recommendation ResultまたはResult Item                    |
| 認証       | MVPでは匿名Feedback                                       |
| 重複制御   | MVPでは簡易重複制御を検討                                 |
| 自由入力   | 文字数制限・ログ出力制限                                  |
| エラー     | GRS-FDB-\* を利用                                         |
| ログ       | feedback保存成功 / 失敗を記録                             |
| メトリクス | feedback_count、positive/negative、feedback_error_count   |

---

### 20.3 Feedback粒度

Feedbackは、以下の粒度を扱えるように設計する。

| 粒度           | 内容                     |
| -------------- | ------------------------ |
| result単位     | 推薦結果全体へのFeedback |
| resultItem単位 | 個別推薦商品へのFeedback |
| reason単位     | 推薦理由へのFeedback     |
| comment単位    | 自由入力コメント         |

MVPでは、UI実装負荷を考慮し、resultItem単位または簡易Feedbackから開始してよい。

---

## 21. Reco Internal API方針

### 21.1 位置づけ

Reco Internal APIは、apiコンポーネントからrecoコンポーネントを呼び出すための内部APIである。

Public APIから直接recoを呼ばず、apiが以下を担う。

- Public API Request受付
- Validation
- traceId生成
- Recommendation Request作成
- reco呼び出し
- Response整形
- Error Response整形
- Access Log / Error Log記録

---

### 21.2 API方針

| 項目       | 方針                                         |
| ---------- | -------------------------------------------- |
| Endpoint   | `POST /internal/reco/v1/recommendations/run` |
| API分類    | Internal API                                 |
| 呼び出し元 | api                                          |
| 呼び出し先 | reco                                         |
| 認証       | Internal API Key候補                         |
| Request    | 正規化済みRecommendation Request             |
| Response   | Recommendation Result生成に必要な内部結果    |
| traceId    | 必ず伝播                                     |
| Error      | GRS-REC-_ / GRS-LLM-_ 等                     |
| Timeout    | Public APIより短すぎない値を設定             |
| Retry      | 原則api側で安易に再実行しない                |

---

### 21.3 Reco Internal APIで返す内部項目

Reco Internal APIでは、Public APIより多くの内部項目を返してよい。

| 項目                   | 用途                     |
| ---------------------- | ------------------------ |
| recommendationRunId    | Run追跡                  |
| recommendationResultId | Result紐づけ             |
| candidateCounts        | フェーズごとの候補数     |
| resultItems            | 推薦結果商品             |
| scoreBreakdown         | 結果保存・分析用         |
| reasonData             | Reason生成結果           |
| metricSummary          | Reco品質メトリクス用     |
| warnings               | 0件、Feature偏り等の警告 |

ただし、これらをそのままPublic APIへ返すとは限らない。

---

## 22. Batch / External API連携方針

### 22.1 Batch APIの位置づけ

商品データ取得・更新・Feature生成は、原則としてPublic APIではなくBatchで実行する。

MVPでは、GitHub Actions等からBatchを起動する想定である。

---

### 22.2 BatchとAPIの関係

| 処理                    | 方針                            |
| ----------------------- | ------------------------------- |
| 楽天API取得             | batchが直接外部APIを呼び出す    |
| Raw保存                 | batchがObject Storageへ保存する |
| Raw Metadata保存        | batchがDBへ保存する             |
| Staging変換             | batchで実行する                 |
| Item反映                | batchで実行する                 |
| Feature生成             | batchまたはrecoで実行する       |
| Embedding生成           | batchまたはrecoで実行する       |
| Public APIからBatch起動 | MVPでは対象外                   |

---

### 22.3 外部API呼び出し方針

| 項目         | 方針                              |
| ------------ | --------------------------------- |
| 楽天API Key  | サーバ側環境変数で管理            |
| Request条件  | api_call_logにマスキングして記録  |
| Response本文 | DBではなくObject StorageへRaw保存 |
| Rate Limit   | api_call_log / error_logで記録    |
| Timeout      | 外部APIごとに設定                 |
| Retry        | Rate Limitを考慮して制御          |
| 差分取得     | 疑似差分取得方針に従う            |

---

## 23. CORS / Rate Limit方針

### 23.1 CORS方針

Public APIでは、許可Originを制限する。

| 環境       | 方針                           |
| ---------- | ------------------------------ |
| local      | localhostのwebポートを許可     |
| preview    | preview環境のOriginを許可      |
| production | production webのOriginのみ許可 |

`*` の許可は原則使用しない。

---

### 23.2 Rate Limit方針

MVPでは匿名ユーザーを前提とするため、IP単位やOrigin単位でのRate Limitを検討する。

| API                                                     | Rate Limit必要性 |
| ------------------------------------------------------- | ---------------- |
| POST /api/v1/recommendations                            | 高               |
| POST /api/v1/recommendation-results/{resultId}/feedback | 中               |
| GET /api/v1/items/{itemId}                              | 中               |
| GET /api/v1/health                                      | 低               |

レコメンド実行APIは、reco / LLM / DB負荷が高いため、特に制限対象とする。

---

## 24. Timeout / Retry方針

### 24.1 Timeout方針

| 呼び出し                   | Timeout方針                        |
| -------------------------- | ---------------------------------- |
| web → api                  | ユーザー体験を損なわない範囲で設定 |
| api → reco                 | 推薦処理の想定時間を踏まえて設定   |
| reco → LLM / Embedding API | 外部依存Timeoutを設定              |
| batch → 楽天API            | Rate LimitとAPI応答時間を考慮      |
| api → database             | 短めに設定し、失敗時はエラー化     |
| batch → object storage     | Raw保存失敗を検知できるように設定  |

---

### 24.2 Retry方針

| 対象             | 方針                                   |
| ---------------- | -------------------------------------- |
| Validation Error | Retryしない                            |
| Business Error   | Retryしない                            |
| DB一時エラー     | 条件付きでRetry検討                    |
| LLM Timeout      | 条件付きでRetry検討                    |
| 楽天API Timeout  | Batch側でRetry検討                     |
| Rate Limit       | 即時Retryせず待機または次回Batchへ回す |
| Reco実行失敗     | Public API側で安易に自動Retryしない    |

---

## 25. Idempotency方針

### 25.1 基本方針

MVPでは、厳密なIdempotency制御は最小限とする。

ただし、以下のAPIでは重複登録・重複実行に注意する。

| API               | 方針                                           |
| ----------------- | ---------------------------------------------- |
| レコメンド実行    | 同一入力でも新しいRunとして扱ってよい          |
| Feedback送信      | 重複Feedbackを制御する                         |
| Batch取込         | content_hashやexternal_item_idで重複反映を防ぐ |
| Internal Reco API | recommendationRunId単位で重複実行に注意する    |

---

### 25.2 Idempotency-Key

`Idempotency-Key` はMVPでは必須にしない。

後続で以下の用途に導入を検討する。

- Feedback重複防止
- 決済導入時の二重実行防止
- 非同期推薦実行の重複受付防止
- Batch起動APIの二重起動防止

---

## 26. OpenAPI / スキーマ管理方針

### 26.1 基本方針

後続のAPI仕様書では、OpenAPI形式で管理できるようにする。

| 項目            | 方針                                      |
| --------------- | ----------------------------------------- |
| API仕様         | Markdown + OpenAPI YAMLの併用を検討       |
| Request Schema  | zod / OpenAPI schema と整合させる         |
| Response Schema | OpenAPI schema と整合させる               |
| Error Schema    | 共通エラー形式として定義                  |
| enum            | 定義書・実装・OpenAPIで不整合を起こさない |
| 型生成          | 後続でTypeScript型生成を検討              |

---

### 26.2 Schema管理の注意点

| 注意点                   | 内容                                                   |
| ------------------------ | ------------------------------------------------------ |
| ドキュメントと実装の乖離 | API仕様書を正本にするか、OpenAPIを正本にするかを決める |
| enumの重複定義           | Domain定義とAPI Schemaで二重管理しない                 |
| API Field名              | camelCaseに統一する                                    |
| DB Field名               | snake_caseに統一する                                   |
| 変換層                   | api層でDB/API変換を担う                                |

---

## 27. API一覧作成への引き継ぎ

API一覧.md では、以下の列を持つことを推奨する。

| 列               | 内容                                 |
| ---------------- | ------------------------------------ |
| API名            | 論理名                               |
| API物理名        | Endpoint名                           |
| API分類          | Public / Internal / Batch / External |
| Method           | GET / POST                           |
| Path             | URL Path                             |
| 呼び出し元       | web / api / batch等                  |
| 呼び出し先       | api / reco / external等              |
| 関連画面         | 利用する画面                         |
| 関連機能         | 機能一覧との対応                     |
| 関連リソース     | リソース一覧との対応                 |
| Request概要      | 主な入力                             |
| Response概要     | 主な出力                             |
| 主なエラーコード | GRS-\*                               |
| trace_id対象     | 対象有無                             |
| ログ対象         | access / error / phase / metric      |
| MVP対象          | 対象 / 後続                          |
| 備考             | 補足                                 |

---

## 28. API仕様書作成への引き継ぎ

API仕様書.md では、APIごとに以下を定義する。

| 項目            | 内容                     |
| --------------- | ------------------------ |
| API概要         | 目的・利用画面・責務     |
| Method / Path   | HTTP MethodとURL         |
| API分類         | Public / Internal等      |
| 認証            | 必要有無                 |
| Request Header  | Header定義               |
| Path Parameter  | Path Parameter定義       |
| Query Parameter | Query Parameter定義      |
| Request Body    | JSON Schema              |
| Response Body   | JSON Schema              |
| Error Response  | エラー形式               |
| エラーコード    | 発生し得るGRSコード      |
| Status Code     | HTTP Status              |
| ログ            | 記録対象                 |
| メトリクス      | 記録対象                 |
| Validation      | 入力検証                 |
| 備考            | 非同期、Retry、Timeout等 |

---

## 29. MVP API候補一覧

### 29.1 Public API候補

| API名          | Method | Path                                                 | MVP対象 | 用途                     |
| -------------- | ------ | ---------------------------------------------------- | ------- | ------------------------ |
| Health Check   | GET    | `/api/v1/health`                                     | 対象    | API稼働確認              |
| レコメンド実行 | POST   | `/api/v1/recommendations`                            | 対象    | 推薦条件入力から結果生成 |
| 商品詳細取得   | GET    | `/api/v1/items/{itemId}`                             | 対象    | 商品詳細画面表示         |
| Feedback送信   | POST   | `/api/v1/recommendation-results/{resultId}/feedback` | 対象    | 推薦結果へのFeedback     |

---

### 29.2 Internal API候補

| API名              | Method | Path                                       | MVP対象               | 用途                      |
| ------------------ | ------ | ------------------------------------------ | --------------------- | ------------------------- |
| Reco Health Check  | GET    | `/internal/reco/v1/health`                 | 対象                  | reco稼働確認              |
| Reco推薦実行       | POST   | `/internal/reco/v1/recommendations/run`    | 対象                  | apiからrecoへ推薦実行依頼 |
| Batch Health Check | GET    | `/internal/batch/v1/health`                | 後続                  | batch稼働確認             |
| Feature生成依頼    | POST   | `/internal/reco/v1/item-features/generate` | 後続またはBatch内処理 | 商品Feature生成           |

---

### 29.3 後続API候補

| API名                        | Method | Path                                            | 理由                 |
| ---------------------------- | ------ | ----------------------------------------------- | -------------------- |
| レコメンド履歴一覧           | GET    | `/api/v1/recommendation-history`                | 認証導入後           |
| レコメンド履歴詳細           | GET    | `/api/v1/recommendation-results/{resultId}`     | 認証導入後           |
| 人手評価タスク一覧           | GET    | `/api/v1/evaluation-tasks`                      | 管理・評価機能導入後 |
| 人手評価登録                 | POST   | `/api/v1/evaluation-tasks/{taskId}/evaluations` | 管理・評価機能導入後 |
| 管理ダッシュボードメトリクス | GET    | `/api/v1/admin/metrics`                         | 管理画面導入後       |
| ログ検索                     | GET    | `/api/v1/admin/logs`                            | 管理画面導入後       |

---

## 30. レビュー観点

| 観点          | 確認内容                                             |
| ------------- | ---------------------------------------------------- |
| API分類       | Public / Internal / External の区分が明確か          |
| MVP範囲       | 認証・履歴・管理APIをMVP対象外として整理できているか |
| URL設計       | Resource基準で一貫しているか                         |
| Method方針    | GET / POST中心になっているか                         |
| Request       | camelCase、JSON、Validation方針が明確か              |
| Response      | data / meta / error の基本構造が明確か               |
| Error         | GRSエラーコードとHTTP Statusの対応が整理されているか |
| traceId       | 成功・失敗ともにtraceIdを返す方針か                  |
| Logging       | ログ・Observability設計書と接続できているか          |
| Security      | Secretや内部情報をResponse / Logに出さない方針か     |
| Reco接続      | api→reco Internal APIの責務が明確か                  |
| 0件結果       | エラーではなく正常系として扱えているか               |
| 商品画像      | 楽天API由来の商品画像URLを扱える方針か               |
| Feedback      | 品質改善用データとして保存できる方針か               |
| 後続拡張      | 認証、履歴、管理APIを後から追加しやすいか            |
| API一覧接続   | 次工程のAPI一覧.mdへ展開できるか                     |
| API仕様書接続 | API仕様書.mdへ詳細化できるか                         |

---

## 31. まとめ

Gift Recommendation Service MVP のAPI設計では、以下を基本方針とする。

| 項目          | 方針                                                              |
| ------------- | ----------------------------------------------------------------- |
| API分類       | Public API / Internal API / External APIを分離する                |
| Public API    | webから呼ばれるMVP画面用APIに絞る                                 |
| Internal API  | api→recoなど内部コンポーネント間APIとして定義する                 |
| HTTPメソッド  | GET / POSTを基本とし、PUT / PATCH / DELETEは原則使用しない        |
| URL           | `/api/v1` をBase Pathとし、kebab-case・複数形リソースを基本とする |
| Request       | JSON + camelCase + Validation必須                                 |
| Response      | data / meta / error の統一構造を基本とする                        |
| Error         | HTTP Status + GRSエラーコード + traceIdで返す                     |
| traceId       | web / api / reco / batchを横断して伝播する                        |
| 認証          | 初回MVPではPublic API認証なし。ただしInternal APIは保護する       |
| Observability | APIログ、error_log、traceId、メトリクスと接続する                 |
| Reco品質      | レコメンド実行APIでは候補数・0件率・処理時間・エラーを観測する    |
| 後続拡張      | 認証、履歴、管理、評価APIを追加できる設計にする                   |

MVPで優先的に定義するAPIは以下である。

| API                                                       | 用途             |
| --------------------------------------------------------- | ---------------- |
| `GET /api/v1/health`                                      | API稼働確認      |
| `POST /api/v1/recommendations`                            | レコメンド実行   |
| `GET /api/v1/items/{itemId}`                              | 商品詳細取得     |
| `POST /api/v1/recommendation-results/{resultId}/feedback` | Feedback送信     |
| `GET /internal/reco/v1/health`                            | Reco稼働確認     |
| `POST /internal/reco/v1/recommendations/run`              | Reco内部推薦実行 |

本方針をもとに、次工程では以下を作成する。

- API一覧.md
- API仕様書.md
- API Request / Response Schema定義
- OpenAPI定義
- API Validation設計
- APIテスト設計
