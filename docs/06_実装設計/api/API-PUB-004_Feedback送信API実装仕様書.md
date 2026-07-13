# Feedback送信 API実装仕様書

> 本書は **API-PUB-004** の **実装面** 正本である。
> 契約面（Request / Response / Error / Validation の定義）は `API-PUB-004_Feedback送信API契約仕様書.md` を正とし、本書では再掲しない。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（#420 / PR #421 develop 反映済み）。generated / Orval / apps 実装の本格整備は後続 Task。本書は docs のみ。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-004-IMPLEMENTATION`              |
| ドキュメント名 | Feedback送信 API実装仕様書                |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-07-14                                |
| 更新日         | 2026-07-14                                |

---

## 2. 前提契約

| 項目 | 内容 |
| ---- | ---- |
| 対象API ID | `API-PUB-004` |
| API名 | Feedback送信 |
| Method / Endpoint | `POST` `/api/v1/recommendation-results/{resultId}/feedback` |
| API契約仕様書 | `docs/06_実装設計/api/API-PUB-004_Feedback送信API契約仕様書.md` |
| OpenAPI定義 | `packages/contracts/openapi/public-api.yaml`（`operationId: submitRecommendationFeedback`） |
| テーブル定義 | `docs/06_実装設計/database/recommendation_feedback_テーブル定義書.md`（#547 / PR #552） |
| 親 Result / Item / Reason | `recommendation_result` / `recommendation_result_item` / `recommendation_reason` 各テーブル定義書 |
| Contract Gate | **契約仕様書確定済み**（#400 / PR #406）。**OpenAPI 断片反映済み**（#420 / PR #421 develop merge）。Orval / generated の全面追随は consumer（SCR-007 等）側 Task で確認 |

> 契約面の Request / Response schema、Validation、Error 一覧は契約仕様書を参照する。本書では実装判断に必要な処理フロー・MOD 責務・DB マッピング・エラー境界・冪等のみ記載する。

### 2.1 Contract Gate 確認結果（本 Task）

| No | チェック | 結果 |
| --: | -------- | ---- |
| 1 | 契約 #400 / PR #406 が develop 反映済み | 充足（契約仕様書が本 Branch に存在） |
| 2 | OpenAPI #420 / PR #421 が `public-api.yaml` に反映済み | 充足（`submitRecommendationFeedback` あり） |
| 3 | `recommendation_feedback` テーブル定義 #547 / PR #552 | 充足 |
| 4 | 本 Task は OpenAPI / apps / DB schema を変更しない | 充足（docs のみ） |

---

## 3. 実装方針

### 3.1 全体方針

| 観点 | 方針 |
| ---- | ---- |
| Provider | `apps/api`（`apps/api/src/app/feedback/**`） |
| Consumer | `apps/web`（SCR-007 Feedback 入力 / レコメンド結果一覧 / 推薦理由詳細）。本 Task では実装しない |
| Web フレームワーク | **Express**（`apps/api` 既存スタック） |
| 担当モジュール | **MOD-API-007** Feedback Controller / **MOD-API-008** Feedback Validator / **MOD-API-009** Feedback Service / **MOD-API-010** Feedback Repository |
| 責務分離 | HTTP 受付 → Validation → 存在確認・冪等判定・保存制御 → DB 永続化。推薦パイプライン（MOD-API-001〜006）および Reco Client は**呼び出さない** |
| 認証 | **MVP は非認証**（契約仕様書 §4）。`Authorization` 検証なし。匿名 Feedback |
| 冪等性 | **条件付き**。`sessionId` + 同一対象 + 同一 `feedbackType` 一致時は **UPDATE → HTTP 200**（`data.status: updated`）。不一致または `sessionId` 未指定時は **INSERT → HTTP 201**（`data.status: accepted`） |
| Ranking 反映 | **即時 Ranking へ自動反映しない**（Recommendation Feedback 定義書 §10.3） |
| DB 書き込み | **api のみ**（IF-DB-API-002）。web / reco / batch からの Direct DB 書き込み禁止 |

### 3.2 エンドポイント層の配置

後続実装 Task の配置目安（現状 `apps/api/src/app/feedback/**` は未作成。本仕様書を正として新規追加する）:

```text
apps/api/src/app/feedback/
├── routes.ts                         # createFeedbackRouter(): POST /:resultId/feedback
├── controllers/
│   └── feedbackController.ts         # MOD-API-007
├── validators/
│   └── feedbackValidator.ts          # MOD-API-008
├── services/
│   └── feedbackService.ts            # MOD-API-009
├── repositories/
│   └── feedbackRepository.ts         # MOD-API-010
└── types.ts                          # 内部 DTO（任意）

apps/api/src/
├── middlewares/                      # request-meta / error 等（既存再利用）
├── infrastructure/db/                # DB client（既存）
└── ...
```

Router mount の目安: `/api/v1/recommendation-results` 配下に Feedback Router を登録する（既存 `recommendations` Router との分離を推奨。実装 Task で Express 構成に合わせる）。

| モジュール | 責務（本 API） |
| ---------- | -------------- |
| MOD-API-007 Feedback Controller | HTTP 受付、meta 解決、Validator / Service 呼び出し、成功（201 / 200）・失敗 Response 組立、metric 境界 |
| MOD-API-008 Feedback Validator | Path / Body の契約 Validation（enum・必須・文字数・type×target 整合）。存在確認は Service 側 |
| MOD-API-009 Feedback Service | Result / Item / Reason 存在確認、trace 列解決、冪等キー検索、INSERT/UPDATE 判定、派生フラグ（`is_positive` / `is_negative`）算出 |
| MOD-API-010 Feedback Repository | `recommendation_feedback` への SELECT（冪等） / INSERT / UPDATE。必要に応じて Result / Item / Reason 読取 |

`apps/reco/**` / `apps/batch/**` / `apps/web/src/app/**` / `apps/web/src/features/**` は **変更しない**（親 Epic `forbidden_paths` 想定）。

### 3.3 DI / 依存

| 項目 | 方針 |
| ---- | ---- |
| request-meta | 既存の Trace / Request ID 解決を再利用。Header 任意・未指定時はサーバ採番可 |
| DB | Postgres。`recommendation_feedback` 書き込み + `recommendation_result` / `recommendation_result_item` / `recommendation_reason` 読取。接続文字列実値をログ・Response に出さない |
| Reco Client / Recommendation Pipeline | **使用しない** |
| Masters | **参照しない** |

### 3.4 認証（実装面）

| 項目 | 方針 |
| ---- | ---- |
| 方式 | MVP 非認証。認証 middleware を本ルートに適用しない |
| `Authorization` | 無視（検証しない） |
| `anonymous_user_id` | DB 列は存在するが **MVP は常に NULL**（書き込まない）。識別は `session_id` のみ |
| 後続 | 認証追加時は契約・OpenAPI 変更を伴う別 Task |

### 3.5 冪等・重複（実装面・契約確定）

契約仕様書 §14（PR #406）および `recommendation_feedback` テーブル定義書 §5.6 を正とする。

| 状況 | HTTP | `data.status` | DB 操作 |
| ---- | ---: | ------------- | ------- |
| 冪等キー不一致、または `sessionId` 未指定（NULL） | **201** | `accepted` | INSERT |
| 冪等キー一致（`sessionId` あり） | **200** | `updated` | UPDATE |
| 重複を拒否する | — | — | **MVP ではしない** |

**冪等キー:** `session_id` + 同一対象 + 同一 `feedback_type`

| `feedback_target_type` | 同一対象の判定列 |
| ---------------------- | ---------------- |
| `result` | `recommendation_result_id`（Path `resultId`） |
| `item` | `recommendation_result_item_id` |
| `reason` | `recommendation_reason_id` |

| 観点 | 方針 |
| ---- | ---- |
| `sessionId` NULL / 未指定 | 部分 UNIQUE 対象外。毎回 INSERT（201）。分析側で重複排除 |
| `GRS-FDB-003`（409） | エラーコード定義書には存在するが、**本 API MVP 契約では返却しない**（更新 200）。API一覧の「重複 409 候補」表記は契約・本書を優先 |
| UNIQUE 競合（レース） | 部分 UNIQUE 違反時は再 SELECT → UPDATE、または 500 `GRS-FDB-005`。実装 Task でトランザクション方針を確定 |

### 3.6 存在確認（実装面）

| 対象 | 確認内容 | 失敗時 |
| ---- | -------- | ------ |
| Path `resultId` | `recommendation_result` に行が存在する | 404 `GRS-FDB-002` |
| `resultItemId`（item 時） | 行が存在し、かつ Path `resultId` に属する | 404 `GRS-FDB-002`（所属外も対象なし扱い） |
| `reasonId`（reason 時） | 行が存在し、親 Result（必要なら Item）と整合 | 404 `GRS-FDB-002` |
| Validation 前の形式不正 | enum 外・必須欠落・文字数超過等 | 400（`GRS-FDB-001` / `GRS-FDB-004` / `GRS-REQ-001`） |

存在しない ID を「内容不正（400）」と「対象なし（404）」に分けない実装にしない。契約どおり **対象不存在は 404**。

### 3.7 保存時の派生・denormalize

| 項目 | 方針 |
| ---- | ---- |
| `recommendation_run_id` / `recommendation_request_id` | Result 行からコピー（LOGICAL FK / trace） |
| `item_id` / `rank_at_feedback` | Item 対象時は Result Item からコピー |
| `feedback_value_type` | Body 未指定時は `feedbackType` から推定（テーブル定義書 §5.5） |
| `feedback_value` | `jsonb` として型を保持 |
| `is_positive` / `is_negative` | `feedbackType` から派生（例: `*_good` → positive、`*_bad` / `item_not_match` 等 → negative）。`comment` のみの場合は nullable 可 |
| `feedback_status` | 保存行は常に `submitted` |
| `user_agent` | Request Header から任意保存可。最大 500 文字。過剰ログ禁止 |
| `submitted_at` | INSERT 時 `now()` |
| `updated_at` | UPDATE 時のみ設定 |

---

## 4. 処理概要

### 4.1 処理フロー

```mermaid
flowchart TD
    START([POST /api/v1/recommendation-results/{resultId}/feedback]) --> META[trace/request meta 解決<br/>Header任意・未指定時はサーバ採番可]
    META --> CTRL[MOD-API-007 Feedback Controller]
    CTRL --> VAL[MOD-API-008 Feedback Validator<br/>Path/Body 契約Validation]
    VAL -->|不正| E400[400 GRS-FDB-001/004 または GRS-REQ-001]
    VAL -->|OK| SVC[MOD-API-009 Feedback Service]
    SVC --> EX_RES{Result 存在?}
    EX_RES -->|No| E404[404 GRS-FDB-002]
    EX_RES -->|Yes| EX_TGT{Item/Reason 必要時<br/>存在・所属確認}
    EX_TGT -->|No| E404
    EX_TGT -->|Yes| IDEM{sessionIdあり かつ<br/>冪等キー一致?}
    IDEM -->|Yes| UPD[MOD-API-010 UPDATE]
    IDEM -->|No| INS[MOD-API-010 INSERT]
    UPD -->|成功| OK200[200 data.status=updated]
    INS -->|成功| OK201[201 data.status=accepted]
    UPD -->|失敗| E500[500 GRS-FDB-005 / GRS-DB-*]
    INS -->|失敗| E500
    SVC -->|想定外| E999[500 GRS-FDB-999 / GRS-COM-999]
    OK200 --> METRIC[feedback_count 等<br/>失敗時は feedback_error_count]
    OK201 --> METRIC
    E400 --> METRIC
    E404 --> METRIC
    E500 --> METRIC
    E999 --> METRIC
    METRIC --> END([完了])
```

### 4.2 処理詳細

1. **meta 解決:** `X-Trace-Id` / `X-Request-Id` は任意。指定時は Response `meta` へ一致反映。未指定時はサーバ採番可。
2. **Controller（MOD-API-007）:** 認証なし。Path `resultId` + JSON Body を受け取り、Validator → Service を呼ぶ。HTTP Method が `POST` 以外はルーティング層で拒否（405 等）。
3. **Validator（MOD-API-008）:** 契約仕様書 §9 に従い、enum・必須・条件付き必須・`rating`（1〜5）・`comment` 最大 500・`feedbackType` × `feedbackTargetType` 整合を検証。失敗時は行を INSERT しない。
4. **Service（MOD-API-009）:**
   - Result 存在確認 → なければ 404 `GRS-FDB-002`
   - target に応じ Item / Reason 存在・所属確認
   - Result から run / request ID を解決
   - `sessionId` がある場合、冪等キーで既存行を検索
   - 一致 → Repository UPDATE、不一致 / 未指定 → Repository INSERT
5. **Repository（MOD-API-010）:** テーブル定義書 §5.5 / §12 の列マッピングで永続化。Response 用に `recommendation_feedback_id` と受付時刻を返す。
6. **成功 Response:** 契約どおり `data`（`recommendationFeedbackId` / `status` / optional `message`）+ `meta`（`traceId` / `requestId` / optional `acceptedAt`）。内部 UUID 以外の秘密情報・`anonymous_user_id`・`user_agent` 原文・テーブル名は **返却しない**。
7. **失敗 Response:** 契約仕様書 §8 の Error 形式。stack trace・SQL・接続文字列を Response / ログ本文に出さない。
8. **metric:** 処理完了時に `feedback_count` を記録。エラー時は `feedback_error_count`。正負は `positive_feedback_count` / `negative_feedback_count`（§8）。

---

## 5. データ項目マッピング

### 5.1 Request Mapping

| Request項目 | 内部項目 / DTO / DB列 | 変換内容 | 備考 |
| ----------- | --------------------- | -------- | ---- |
| Path `resultId` | `recommendation_result_id` | 存在確認後に必須親として設定 | UUID 想定（契約例は文字列） |
| `feedbackTargetType` | `feedback_target_type` | camel → snake | enum |
| `resultItemId` | `recommendation_result_item_id` | item 時必須 | — |
| `reasonId` | `recommendation_reason_id` | reason 時必須 | — |
| `feedbackType` | `feedback_type` | そのまま（snake 値） | 冪等キー要素 |
| `feedbackValueType` | `feedback_value_type` | 未指定時は type から推定 | — |
| `feedbackValue` | `feedback_value` | jsonb 化 | — |
| `feedbackChoiceCode` | `feedback_choice_code` | そのまま | — |
| `feedbackReasonCategory` | `feedback_reason_category` | そのまま | — |
| `rating` | `feedback_rating` | 整数 1〜5 | NOT NULL |
| `comment` | `feedback_text` | 最大 500 文字 | — |
| `sourcePage` | `source_page` | 画面 ID | 例: `SCR-007` |
| `sessionId` | `session_id` | 冪等キー要素。個人情報・token を含めない | 未指定可 |
| `X-Trace-Id` | `meta.trace_id` | 任意。未指定時サーバ採番可 | Response と一致 |
| `X-Request-Id` | `meta.request_id` | 任意。未指定時サーバ採番可 | Response と一致 |
| `User-Agent`（任意） | `user_agent` | 長さ制限して保存可 | Response に出さない |
| （Service 解決） | `recommendation_run_id` / `recommendation_request_id` | Result からコピー | — |
| （Service 解決） | `item_id` / `rank_at_feedback` | Item からコピー | item / reason 時 |
| （Service 算出） | `is_positive` / `is_negative` | type から派生 | nullable 可 |
| （固定） | `feedback_status` | `submitted` | — |
| （固定） | `anonymous_user_id` | **常に NULL** | MVP |

### 5.2 Response Mapping（成功・201 / 200）

| 内部項目 / DTO | Response項目 | 変換内容 | 備考 |
| -------------- | ------------ | -------- | ---- |
| `recommendation_feedback_id` | `data.recommendationFeedbackId` | UUID → 文字列 | 必須 |
| INSERT / UPDATE 判定 | `data.status` | `accepted` / `updated` | 201 / 200 と対応 |
| 固定文言（任意） | `data.message` | 受付 / 更新メッセージ | 契約 Example 準拠可 |
| `meta.trace_id` | `meta.traceId` | そのまま | — |
| `meta.request_id` | `meta.requestId` | そのまま | — |
| `submitted_at`（INSERT）または `updated_at`（UPDATE） | `meta.acceptedAt` | ISO 8601 | optional |
| `session_id` / `anonymous_user_id` / `user_agent` | — | **Response に含めない** | 契約 §7.3.2 |
| SQL / 内部 stack | — | **含めない** | — |

### 5.3 Error Mapping（実装面）

| 内部状況 | HTTP | Error Code | 備考 |
| -------- | ---: | ---------- | ---- |
| Body / type / target 不整合・必須不足・rating 不正 | 400 | `GRS-FDB-001` | Validator |
| `comment` 500 文字超過 | 400 | `GRS-FDB-004` | Validator |
| JSON 形式・型不正 | 400 | `GRS-REQ-001` | 共通 Validation |
| Result / Item / Reason 不存在または所属外 | 404 | `GRS-FDB-002` | Service |
| 冪等キー一致 | **200 更新** | （エラーではない） | **409 / `GRS-FDB-003` は返さない** |
| Feedback 保存失敗（INSERT/UPDATE） | 500 | `GRS-FDB-005` | Repository |
| DB 接続・クエリ障害 | 500 | `GRS-DB-001`〜`006` 等 | 既存 DB エラー境界に合わせる |
| Feedback 想定外 | 500 | `GRS-FDB-999` | — |
| 共通想定外 | 500 | `GRS-COM-999` | stack 非公開 |

詳細メッセージ・ユーザー向け表示は契約仕様書 §8・エラーコード定義書を正とする。

---

## 6. generated client 利用方針

| 項目 | 内容 |
| ---- | ---- |
| generated出力先 | `apps/web/src/generated/api/`（Orval。本 Task では再生成しない） |
| operationId | `submitRecommendationFeedback` |
| client wrapper | `apps/web/src/lib/**` 配下の手書き wrapper（SCR-007 等の実装 Task で利用。本 Task では変更しない） |
| 再生成コマンド | プロジェクト標準の Orval 再生成（本 Task では実行しない） |
| 検証コマンド | typecheck / contract test（本 Task では実行しない） |

generated ファイルは手動編集しない。利用側は wrapper を介して generated client を呼ぶ。

---

## 7. provider / consumer 実装影響

### 7.1 provider

| 項目     | 内容 |
| -------- | ---- |
| provider | `apps/api` |
| 責務     | Public Feedback 送信 API の提供・Validation・冪等保存 |
| 影響有無 | `あり`（後続実装 Task） |
| 必要対応 | `apps/api/src/app/feedback/**` 新規、Router mount、DB 読取/書込、metric / error 配線 |

- MOD-API-007〜010 の実装
- `/api/v1/recommendation-results/{resultId}/feedback` の Router 登録
- `recommendation_feedback` INSERT / 冪等 UPDATE（§3.5）
- Result / Item / Reason 存在確認
- Error / meta / metric の既存共通部品との整合

### 7.2 consumer

| 項目     | 内容 |
| -------- | ---- |
| consumer | `apps/web`（SCR-007 / 結果一覧 / 理由詳細） |
| 責務     | Feedback 入力 UI からの送信・完了表示 |
| 影響有無 | `あり`（画面・client Task。本 Task では対象外） |
| 必要対応 | generated client 経由で本 API を呼び、201 / 200 を完了表示に反映 |

- MVP は匿名 Feedback。`sessionId` の採番・保管方式は §11 の未決事項
- Ranking 即時反映を期待しない

---

## 8. ログ・監視

| 種別 | 内容 | 出力タイミング | 備考 |
| ---- | ---- | -------------- | ---- |
| API access log | method / path / status / latency / trace_id | リクエスト完了時 | `session_id` / `feedback_text` 原文の過剰出力を避ける |
| error log | error.code / 内部要約 / trace_id | 4xx（必要時）・5xx | SQL・接続文字列・secret を出さない |
| audit log | Feedback 受付の要約（任意） | INSERT / UPDATE 成功時 | `recommendationFeedbackId` と target 粒度程度。個人情報不可 |
| metric | `feedback_count` | 処理完了時（成功含む） | API一覧 / Observability |
| metric | `feedback_error_count` | エラー応答時 | — |
| metric | `positive_feedback_count` | 正の Feedback 成功時 | `is_positive` または type から |
| metric | `negative_feedback_count` | 負の Feedback 成功時 | 同上 |

---

## 9. 実装テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系（新規 item） | 必須項目で 201 + `status: accepted` + DB INSERT | integration |
| 2 | 正常系（新規 reason） | `reasonId` + `reason_good` で 201 | integration |
| 3 | 正常系（新規 result） | `result_good` で 201 | integration |
| 4 | 冪等更新 | 同一 `sessionId` + 対象 + type 再送で 200 + `status: updated` + UPDATE | integration |
| 5 | sessionId なし | 再送でも毎回 201（重複 INSERT 許容） | integration |
| 6 | validation | type×target 不整合で 400 `GRS-FDB-001`。行なし | integration |
| 7 | rating / comment | rating 欠落 400、comment 501 文字で `GRS-FDB-004` | integration |
| 8 | 対象なし | 存在しない `resultId` / 所属外 Item で 404 `GRS-FDB-002` | integration |
| 9 | DB 失敗 | 書き込み失敗で 500 `GRS-FDB-005` または `GRS-DB-*` | integration |
| 10 | 非公開項目 | Response に `sessionId` / `user_agent` / 内部 stack が含まれない | integration |
| 11 | meta 伝播 | `X-Trace-Id` 指定時に `meta.traceId` 一致 | integration |
| 12 | metric | `feedback_count` / `feedback_error_count` / 正負 count が境界どおり | unit / integration |
| 13 | 409 非返却 | 重複時に `GRS-FDB-003` を返さない | integration |
| 14 | generated client | `submitRecommendationFeedback` 型整合（consumer Task） | typecheck |
| 15 | provider / consumer | SCR-007 から送信・完了表示できること（画面 Task） | manual |

> 契約面の単体テスト観点（validation / auth / Request・Response schema）は契約仕様書を正とする。本 Task ではテストコードを追加しない。

---

## 10. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-07-14 | 初版作成（実装面のみ） | #1226 |

---

## 11. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `sessionId` の採番・保管方式（cookie / body / header / localStorage） | consumer（web）実装と冪等体験に影響 | Human | 実装 Task 前推奨 | 契約上 Body `sessionId` は optional。API 側は値を検証して保存するのみ |
| 2 | Result 全体 Feedback と Item/Reason Feedback の同時送信を MVP で許容するか | 1 Request = 1 Feedback 行が現行契約。一括 API は別契約 | Human | 任意 | 現状はクライアントが複数回 POST |
| 3 | UNIQUE 違反時のレースハンドリング | 並列同一キーで UNIQUE 競合し得る | 実装 Task / Human | 実装時 | 再 SELECT→UPDATE 推奨 |

### 11.1 契約で確定済み（本書は追従）

| No | 論点 | 確定内容 | 出典 |
| --: | ---- | -------- | ---- |
| 1 | 成功 Status | 新規 **201** / 更新 **200** | 契約 §14 |
| 2 | 重複応答 | **更新 200**。409 / `GRS-FDB-003` は返却しない | 契約 §14 |
| 3 | `comment` 最大文字数 | **500** | 契約 §14 |
| 4 | `rating` | **必須**（1〜5） | 契約 §14 |
| 5 | `anonymous_user_id` | MVP 未使用（NULL 固定） | テーブル定義書 §17.1 |

---

## 12. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 契約仕様書 | `docs/06_実装設計/api/API-PUB-004_Feedback送信API契約仕様書.md` | 前提契約 |
| テーブル定義 | `docs/06_実装設計/database/recommendation_feedback_テーブル定義書.md` | 保存列・冪等 UNIQUE |
| Result / Item / Reason | 各 `*_テーブル定義書.md` | 存在確認 |
| ドメイン | `docs/04_ドメインモデル設計/RecommendationFeedback定義書.md` | Feedback 意味・冪等方針 |
| OpenAPI | `packages/contracts/openapi/public-api.yaml` | `submitRecommendationFeedback` |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | metric / Provider |
| モジュール一覧 | `docs/05_アプリケーション設計/アプリ/モジュール一覧.md` | MOD-API-007〜010 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-FDB-* |
| ログ設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | feedback_* metric |
| Task Definition | `prompts/definitions/tasks/api-pub-004-feedback-submit/api-implementation-spec.yaml` | 本 Task 条件 |
| 親 Epic | #386 | 作業管理 |

---

## 13. レビュー観点

- 確定済み API 契約（契約仕様書 / OpenAPI）と実装方針が整合している
- 処理フロー・MOD-API-007〜010・内部 DTO / DB マッピングが明確である
- 冪等が **更新 200** であり、MVP で `GRS-FDB-003` を返さないことが明示されている
- Result / Item / Reason 存在確認と 404 境界が契約と一致している
- Response に `session_id` / `anonymous_user_id` / `user_agent` / secret を含めない
- generated client を手動編集せず、本 Task では OpenAPI / apps を変更していない
- provider / consumer の実装影響が整理されている
- ログ・監視・結合テスト観点が整理されている
- secret や `.env` 実値が含まれていない

### 13.1 Human Review で確認してほしいこと

- §11 未決事項（特に `sessionId` 採番方式）の扱い
- API一覧の「重複 409 候補」と契約・本書（更新 200）の差分を一覧側で後追い修正するか
- 後続 apps/api 実装 Task の入力粒度として十分か

---

## 14. 備考

- 本 Task は Phase4b 縦串の 1/3（実装面仕様書）。後続は apps/api 実装 → 単体テスト → Epic PR → develop。
- Task PR target は親 Epic Branch `feature/epic-386-pub-004-feedback-submit`。
- Feedback は品質改善・分析の入口であり、Online 推薦実行本体（API-PUB-002）のブロッカーではない（レーン 5）。
- Task Definition の scope 文言に「409 GRS-FDB-003」が残っている場合でも、**契約 §14 を正**とし、本書は更新 200 で統一する。
