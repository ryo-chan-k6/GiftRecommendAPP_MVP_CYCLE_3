# APIヘルスチェック API契約仕様書

> 本書は **API-PUB-001** の契約面（Public I/F）正本である。
> 処理フロー・MOD-API 責務・依存コンポーネント（DB / reco）チェック詳細・結合テスト観点は `API-PUB-001_APIヘルスチェックAPI実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-001-CONTRACT`                    |
| ドキュメント名 | APIヘルスチェック API契約仕様書           |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05                                |

---

## 2. 概要

web（`apps/web`）および運用確認（監視・疎通確認）から api（`apps/api`）へ、API レイヤの稼働状態を確認する Public API である。関連リソースは **Health** であり、Response では **API稼働状態** を返す（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-001）。

---

## 3. 目的

- 監視・疎通確認・運用確認が利用する Request / Response / Error を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- API設計方針書・API一覧・エラーコード定義書と整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-001`                                     |
| API名    | APIヘルスチェック                                 |
| API種別  | `Public API`                                      |
| Method   | `GET`                                             |
| Endpoint | `/api/v1/health`                                  |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web` / 運用確認（監視・疎通確認）           |
| 認証要否 | `false`（MVP は非認証。後続で Authorization 追加可） |
| 権限条件 | MVP ではなし                                      |
| 冪等性   | `冪等`（同一 Request の繰り返しで副作用なし）     |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- デプロイ後・定期監視による API 稼働確認時
- web 起動時または画面表示前の疎通確認時（任意）
- 運用ツール・ロードバランサ・監視システムからのヘルスプローブ時

### 5.2 呼び出し元

- `apps/web`（任意の疎通確認）
- 運用確認（監視・疎通確認）

### 5.3 主なユースケース

- API プロセスが応答可能であることを確認する。
- HTTP 200 かつ `data.status: "ok"` を正常系として扱う。
- 障害時は HTTP 5xx と `GRS-COM-*` エラーコードで調査可能にする。

---

## 6. Request仕様

### 6.1 Request Header

| Header       | 必須    | 内容               | 例                                   |
| ------------ | ------- | ------------------ | ------------------------------------ |
| `Accept`     | `false` | `application/json` | `application/json`                   |
| `X-Trace-Id` | `false` | 横断追跡 ID        | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID  | `req_01HZYX`                         |

MVP では `Authorization` は使用しない。`Content-Type` は Request Body がないため不要。

### 6.2 Path Parameters

| 項目 | 型 | 必須 | 内容 | 例 |
| ---- | -- | ---- | ---- | -- |
| -    | -  | -    | なし | -  |

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

### 6.4 Request Body

なし（GET では Request Body を使用しない。API設計方針書 §6）。

### 6.5 Request Example

Request Body なし。例:

```http
GET /api/v1/health HTTP/1.1
Host: api.example.com
Accept: application/json
```

---

## 7. Response仕様

### 7.1 Response Header

| Header         | 内容               | 例                |
| -------------- | ------------------ | ----------------- |
| `Content-Type` | `application/json` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | 処理成功（API 稼働中） | api プロセスが応答可能で Health 情報を返却できる場合 |
| 500 | 内部エラー | 想定外の処理失敗（`GRS-COM-999`） |
| 503 | 一時利用不可 | api が一時的に応答不能（`GRS-COM-003`） |
| 504 | タイムアウト | 内部処理タイムアウト（`GRS-COM-002`） |

**契約上の正常系:** HTTP **200** かつ `data.status: "ok"`。監視・疎通確認用途のため、軽量応答を基本とする（API一覧 §API-PUB-001 備考）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。主データは **Health** リソースの表面表現（API稼働状態）とする。

#### 7.3.1 `data`（Health）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `status` | `string` | `true` | API 稼働状態 | enum: `ok` / `degraded` / `unavailable`（OpenAPI Task で固定） |
| `service` | `string` | `true` | サービス識別子 | 例: `gift-recommendation-api` |
| `apiVersion` | `string` | `true` | API バージョン | URL パス `v1` と整合。例: `v1` |
| `checkedAt` | `string` | `false` | ヘルス判定日時（ISO 8601） | 未指定時は `meta.generatedAt` を参照可 |

**契約面の `status` 意味（MVP）:**

| 値 | 意味 | HTTP Status（原則） |
| -- | ---- | ------------------- |
| `ok` | api プロセスが正常応答可能 | 200 |
| `degraded` | api は応答するが一部依存に劣化あり | 200（契約上は応答可。監視閾値は実装仕様書で定義） |
| `unavailable` | api が正常な Health を返せない | 503 |

依存コンポーネント（DB / reco）の個別チェック結果・閾値・タイムアウトは本契約では **表面化しない**。実装仕様書 Task で定義する（§14.1 No.1）。

#### 7.3.2 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `false` | 横断追跡 ID | API一覧では trace_id 対象は任意。指定時は Header を引き継ぎまたは生成 |
| `requestId` | `string` | `false` | API リクエスト ID | 未指定時は api 側で生成可 |
| `generatedAt` | `string` | `false` | 生成日時（ISO 8601） | - |

### 7.4 Response Example

#### 7.4.1 正常系（200）

```json
{
  "data": {
    "status": "ok",
    "service": "gift-recommendation-api",
    "apiVersion": "v1",
    "checkedAt": "2026-06-05T09:00:00+09:00"
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-05T09:00:00+09:00"
  }
}
```

#### 7.4.2 劣化あり（200・契約上は応答可）

```json
{
  "data": {
    "status": "degraded",
    "service": "gift-recommendation-api",
    "apiVersion": "v1"
  },
  "meta": {
    "generatedAt": "2026-06-05T09:01:00+09:00"
  }
}
```

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時は API設計方針書 §8.3 に準拠する。`meta.traceId` / `meta.requestId` は可能な範囲で返す。

```json
{
  "error": {
    "code": "GRS-COM-003",
    "message": "現在サービスを利用できません。時間を置いて再度お試しください。",
    "details": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY"
  }
}
```

### 8.2 Error一覧（本 API で想定する代表）

| Status | Error Code | 発生条件 | Response概要 | ユーザー向け表示 |
| -----: | ---------- | -------- | ------------ | ---------------- |
| 500 | `GRS-COM-999` | 想定外内部エラー | 内部エラー | 予期しないエラーが発生しました。時間を置いて再度お試しください。 |
| 503 | `GRS-COM-003` | 一時的利用不可 | サービス一時停止 | 現在サービスを利用できません。時間を置いて再度お試しください。 |
| 504 | `GRS-COM-002` | タイムアウト | タイムアウト | 処理に時間がかかっています。時間を置いて再度お試しください。 |

本 API では Request Body を持たないため、`GRS-COM-001`（Bad Request）等の Validation 系は原則発生しない。不正な HTTP メソッド（例: POST）は api ルーティング層で 405 等として扱う（本契約の Error 一覧外。実装仕様書で整理）。

API一覧の主なエラーコード `GRS-COM-*` に整合する。`GRS-REC-*` / `GRS-DB-*` 等は本 Public Health API の契約 Error 一覧には含めない（内部障害は `GRS-COM-003` / `GRS-COM-999` へ集約可）。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| HTTP Method | `GET` のみ許可 | - | ルーティング層で拒否（405 等は実装仕様書で定義） |
| Request Body | 送信しない | - | GET では Body なし |
| Path / Query | 本 API ではパラメータなし | - | 未知 Query は無視または 400（実装仕様書で統一） |

構文 Validation の対象は最小限とする（軽量ヘルスチェックのため）。

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `getHealth` または `healthCheck`（OpenAPI Task で確定） |
| Path | `/api/v1/health` |
| components schema | `HealthResponse` / `HealthStatus` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を 1b OpenAPI Contract Task の入力正本とする。

Contract Gate 通過後に Implementation Task（`api-implementation-spec`）および apps 実装 Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public Health 契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新（任意）→ api 実装

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | GET で 200、`data.status: "ok"` | contract |
| 2 | 冪等性 | 同一 Endpoint の連続 GET で副作用なし | contract |
| 3 | Response 構造 | `data` + `meta`、必須フィールド存在 | contract |
| 4 | エラー系 | 503 + `GRS-COM-003` の形式 | contract |
| 5 | trace 伝播 | `X-Trace-Id` 指定時に `meta.traceId` が一致（任意） | contract |
| 6 | generated client | OpenAPI 生成後、型が Response と一致 | typecheck |

実装結合・依存コンポーネント障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（契約面のみ。Phase1 Wave2 C2 batch1） | Epic #384 |

---

## 14. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | 依存コンポーネント（DB / reco）チェックを Response に含めるか | `degraded` 判定の契約面定義に影響 | Human | - | 実装仕様書 Task と合わせて確定推奨 |
| 2 | `degraded` 時の HTTP Status を 200 固定とするか | 監視アラート閾値に影響 | Human | - | 本書は契約上 200 を原則とした |
| 3 | `service` 識別子の正式文字列 | OpenAPI example / 監視ダッシュボード整合 | Human | - | 例は `gift-recommendation-api` |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-001 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Request/Response/Error 形式 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-COM-* |
| ログ・Observability設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | access_log / metric |
| 可用性要件 | `docs/03_ドメイン要件定義/非機能要件定義書/可用性要件.md` | ヘルスチェック要件 |
| Task Definition | `prompts/definitions/tasks/api-pub-001-api-health-check/api-contract-spec.yaml` | Epic #384 配下 scope |
| Epic Definition | `prompts/definitions/epics/api-pub-001-api-health-check/epic.yaml` | epic_scope |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で、OpenAPI Task の入力として十分か
- API設計方針書 §8（data/meta 構造）と矛盾していないか
- API一覧の API-PUB-001（endpoint / Method / Health リソース / GRS-COM-*）と一致しているか
- 実装面（MOD-API フロー・依存チェック詳細）を含んでいないか
- secret / `.env` 実値が含まれていないか

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint（`GET /api/v1/health`）と MVP 非認証方針の最終確認
- §14 の `status` enum と依存コンポーネント表面化範囲
- OpenAPI Contract Task への分離方針の確認

---

## 17. 備考

- 本書は `prompts/templates/docs/api-contract-spec.md` に準拠した Phase1 ①（1a）成果物である。
- API-INT-001（Recoヘルスチェック）は別 API。本書では web↔api の Public Health 境界のみを正とする。
- ログ・Observability（access_log / api_request_count / api_error_count）は API一覧に準拠。実装記録方針は実装仕様書で扱う。
