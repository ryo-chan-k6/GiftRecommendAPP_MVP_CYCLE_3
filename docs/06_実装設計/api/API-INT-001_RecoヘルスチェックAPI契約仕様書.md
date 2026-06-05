# Recoヘルスチェック API契約仕様書

> 本書は **API-INT-001** の契約面（Internal I/F）正本である。
> 処理フロー・依存チェック実装詳細・結合テスト観点は `API-INT-001_RecoヘルスチェックAPI実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/internal-reco-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-INT-001-CONTRACT`                    |
| ドキュメント名 | Recoヘルスチェック API契約仕様書          |
| 対象システム   | Gift Recommendation Service MVP（Internal） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05                                |

---

## 2. 概要

api（`apps/api`）から reco（`apps/reco` エンドポイント層）の稼働状態を確認する Internal API である。推薦パイプラインは実行せず、reco サービスが HTTP で応答可能かを返す。

本書では **api↔reco 間の HTTP 契約** のみを定義する。推薦ロジック（MOD-RECO-001 等）の内部処理は本書の scope 外とする。

---

## 3. 目的

- api→reco 間の Request / Response / Error / Validation を確定し、Contract Gate および後続 OpenAPI Contract Task の入力とする。
- API設計方針書・API一覧・エラーコード定義書と整合した Internal 契約面を提供する。
- api が Reco Client（MOD-API-005）経由で reco 接続確認を行う際の I/F 境界を明確にする。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-INT-001`                                     |
| API名    | Recoヘルスチェック                                |
| API種別  | `Internal API`                                    |
| Method   | `GET`                                             |
| Endpoint | `/internal/reco/v1/health`                        |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/reco`（エンドポイント層）                   |
| Consumer | `apps/api`（MOD-API-005 Reco Client 等）          |
| 認証要否 | `true`（Internal API Key。詳細は §6.1）           |
| 権限条件 | サービス間呼び出しのみ。外部ユーザー直接利用不可  |
| 冪等性   | `冪等`（副作用なし。同一 Request の繰り返し可）   |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- api 起動時・定期監視・レコメンド実行前の reco 疎通確認時
- 運用確認（api / 監視ツールからの内部呼び出し）

### 5.2 呼び出し元

- `apps/api`（Reco Client / 運用確認処理）

### 5.3 主なユースケース

- reco が常駐サービスとして稼働していることを確認する。
- reco が応答不能の場合、api 側で接続エラーまたは 5xx を検知し、後続処理（API-INT-002 等）を抑制またはエラー表示する。

### 5.4 関連モジュール（参照のみ）

| 項目 | 内容 |
| ---- | ---- |
| Consumer モジュール | `MOD-API-005`（Reco Client）— 本 API の呼び出し責務 |
| Provider 境界 | `apps/reco` エンドポイント層（HTTP I/F） |
| 後続 Internal API | `API-INT-002`（Reco推薦実行）— ヘルス確認後に実行される推薦 API |

---

## 6. Request仕様

### 6.1 Request Header

| Header | 必須 | 内容 | 例 |
| ------ | ---- | ---- | -- |
| `Accept` | `true` | `application/json` | `application/json` |
| `X-Internal-Api-Key` | `true` | Internal API 保護用キー（値は環境変数。本書に実値を記載しない） | `***REDACTED***` |
| `X-Trace-Id` | `false` | 横断追跡 ID。指定時は Response `meta.traceId` へ反映 | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID。指定時は Response `meta.requestId` へ反映 | `req_01HZYX` |

Internal API は API設計方針書 §11.3 に従い `X-Internal-Api-Key` で保護する。`X-Trace-Id` / `X-Request-Id` は API一覧上 trace_id 対象が **任意** のため必須としない。指定された場合は reco 側で Response `meta` へ反映する。

### 6.2 Path Parameters

| 項目 | 型 | 必須 | 内容 | 例 |
| ---- | -- | ---- | ---- | -- |
| - | - | - | なし | - |

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| - | - | - | なし | - | - |

### 6.4 Request Body

なし（GET のため Request Body を使用しない。API設計方針書 §7.4）。

### 6.5 Request Example

```http
GET /internal/reco/v1/health HTTP/1.1
Host: reco.internal.example
Accept: application/json
X-Internal-Api-Key: ***REDACTED***
X-Trace-Id: 550e8400-e29b-41d4-a716-446655440000
```

### 6.6 Observability（契約露出範囲）

| 項目 | 露出箇所 | 必須 | 内容 |
| ---- | -------- | ---- | ---- |
| `traceId` | Request Header `X-Trace-Id`（任意）/ Response `meta.traceId` | `false` | 指定時は往復一致 |
| `requestId` | Request Header `X-Request-Id`（任意）/ Response `meta.requestId` | `false` | 指定時は往復一致 |

access_log / metric の**実装・記録詳細**は実装仕様書 Task で扱う（ログ・Observability設計書を正本とする）。契約上、metric 対象は `reco_health_check_count`（API一覧）とする。

---

## 7. Response仕様

### 7.1 Response Header

| Header | 内容 | 例 |
| ------ | ---- | -- |
| `Content-Type` | `application/json` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | reco 稼働確認成功 | reco が正常応答し、契約上の稼働状態を返却できる場合 |
| 401 | 認証失敗 | `X-Internal-Api-Key` 不正または未指定 |
| 403 | 権限不足 | Internal API への不正アクセス（`GRS-AUTH-002` 等） |
| 500 | 内部エラー | reco 内部の想定外エラー（`GRS-COM-999` / `GRS-REC-002` 等） |
| 503 | 一時利用不可 | reco が起動中だが依存（DB 等）が利用不可（`GRS-COM-003` 等） |

ヘルスチェックは **推薦未実行** のため、400 / 422 / 502 / 504 は通常発生しない。api 側の HTTP クライアントタイムアウトは接続エラーとして扱い、実装仕様書 Task で整理する。

**稼働不良と HTTP Status:** reco プロセスは応答するが内部依存が不全の場合、HTTP **503** と `data.status: degraded` の組み合わせを許容する（§7.3.1）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。

#### 7.3.1 `data`（稼働状態）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `status` | `string` | `true` | 稼働状態 | MVP 値域: `ok` / `degraded` / `unavailable` |
| `service` | `string` | `true` | サービス識別子 | 固定値 `reco` |
| `version` | `string` | `false` | アプリケーションバージョン | デプロイ識別用。未設定可 |
| `checkedAt` | `string` | `false` | 確認日時（ISO 8601） | reco 側生成時刻 |

| `status` 値 | HTTP Status（典型） | 意味 |
| ----------- | ------------------- | ---- |
| `ok` | 200 | reco プロセスが正常応答し、MVP で必要な最小依存が利用可能 |
| `degraded` | 200 または 503 | reco は応答するが一部依存が不全（詳細チェックは実装 Task） |
| `unavailable` | 503 | reco が利用不可 |

MVP 初版では `status: ok` のみを必須成功パターンとし、`degraded` / `unavailable` の判定条件詳細は実装仕様書 Task で確定する。

#### 7.3.2 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `false` | 横断追跡 ID | Header `X-Trace-Id` 指定時は一致 |
| `requestId` | `string` | `false` | API リクエスト ID | Header `X-Request-Id` 指定時は一致 |
| `generatedAt` | `string` | `false` | 生成日時（ISO 8601） | - |

### 7.4 Response Example

#### 7.4.1 正常系（`status: ok`）

```json
{
  "data": {
    "status": "ok",
    "service": "reco",
    "version": "0.1.0",
    "checkedAt": "2026-06-05T12:00:00+09:00"
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "generatedAt": "2026-06-05T12:00:00+09:00"
  }
}
```

#### 7.4.2 エラー系（認証失敗）

```json
{
  "error": {
    "code": "GRS-AUTH-001",
    "message": "認証に失敗しました。"
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

---

## 8. Error Response仕様

### 8.1 共通形式

API設計方針書 §8.3 に従い、エラー時は `error` + `meta` 構造とする。`data` は返さない。

| 項目 | 型 | 必須 | 内容 |
| ---- | -- | ---- | ---- |
| `error.code` | `string` | `true` | `GRS-*` エラーコード |
| `error.message` | `string` | `true` | 安全なメッセージ |
| `error.details` | `array` / `object` | `false` | Validation 補足（本 API では通常なし） |
| `meta.traceId` | `string` | `false` | 横断追跡 ID |
| `meta.requestId` | `string` | `false` | リクエスト ID |

### 8.2 発生し得るエラーコード

API一覧の主なエラーコード（`GRS-COM-*` / `GRS-REC-*`）および Internal 認証に整合する。

| HTTP Status | error.code | 発生条件 |
| ----------- | ---------- | -------- |
| 401 | `GRS-AUTH-001` | Internal API Key 不正 |
| 401 | `GRS-AUTH-004` | Internal API Key 未指定 |
| 403 | `GRS-AUTH-002` | 許可されない操作 |
| 500 | `GRS-COM-999` | 想定外内部エラー |
| 500 | `GRS-REC-002` | reco 処理失敗（ヘルスチェック処理内） |
| 503 | `GRS-COM-003` | 一時利用不可（依存不全等） |

api が Public API 向けにエラーを整形する場合の詳細は実装仕様書 Task で扱う。本 API は Internal のため、api 内部ログに `GRS-*` を保持する。

---

## 9. Validation仕様

| 対象 | ルール | 失敗時 |
| ---- | ------ | ------ |
| HTTP Method | `GET` のみ | 405（実装 Task で扱う。契約上は想定外） |
| `X-Internal-Api-Key` | 必須・検証成功 | 401（`GRS-AUTH-001` / `GRS-AUTH-004`） |
| Path / Query / Body | 本 API ではパラメータ・Body なし | - |

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/internal-reco-api.yaml` |
| 操作 ID（案） | `getRecoHealth` または `checkRecoHealth`（OpenAPI Task で確定） |
| Path | `/internal/reco/v1/health` |
| components schema | `RecoHealthResponse` / `HealthStatus` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（api→reco） | `apps/api/src/generated/reco-client/` |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を OpenAPI（internal）Contract Task の入力正本とする。

Contract Gate 通過後に Implementation Task および apps/reco・apps/api 実装 Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Internal ヘルスチェック契約確定 |

### 11.1 rollout order

- 本契約確定 → `internal-reco-api.yaml` 更新 → Orval 再生成（reco-client）→ apps/api Reco Client 更新 → apps/reco エンドポイント実装

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | 有効な `X-Internal-Api-Key` で 200、`data.status: ok`、`data.service: reco` | contract |
| 2 | auth error | `X-Internal-Api-Key` 欠落・不正で 401 | contract |
| 3 | trace 伝播 | `X-Trace-Id` 指定時に `meta.traceId` が一致 | contract |
| 4 | 冪等性 | 同一 Request の繰り返しで副作用なし | contract |
| 5 | generated client | OpenAPI 生成後、型が Response と一致（`apps/api` reco-client） | typecheck |

実装結合・依存障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（契約面のみ。Phase1 1a） | #392 |

---

## 14. 未決事項

### 14.1 確定済み（本書へ反映済み）

| No | 論点 | 確定内容 | 反映箇所 |
| --: | ---- | -------- | -------- |
| 1 | Endpoint / Method | `GET /internal/reco/v1/health`（API一覧・API設計方針書 §29.2） | §4 |
| 2 | Provider / Consumer | Provider: `apps/reco` エンドポイント層、Consumer: `apps/api` | §4、§5.4 |
| 3 | Request Body | なし（GET） | §6.4 |
| 4 | 認証 | Internal API Key 必須（API設計方針書 §11.3） | §6.1、§9 |

### 14.2 未決（人間判断待ち）

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 | 追跡 Issue |
| --: | ---- | ---------------- | ------ | ---- | ---- | ---------- |
| 1 | `degraded` / `unavailable` の判定条件 | MVP 初版は `ok` のみ必須としたが、依存チェック（DB 等）の範囲は実装判断が必要 | Human | - | 実装仕様書 Task で詳細化 | - |
| 2 | `data.version` の必須化 | デプロイ追跡に有用だが MVP で必須とするか未確定 | Human | - | 現状 optional | - |

OpenAPI（`internal-reco-api.yaml`）への機械可読反映は **別 Contract Task** とする。

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-INT-001 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Internal API / Response 形式 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-* |
| 認証・認可方針書 | `docs/05_アプリケーション設計/基盤/認証・認可方針書.md` | Internal API Key |
| ログ・Observability設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | access_log / metric |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-INT-001 |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | MOD-API-005 |
| 参考（同一群） | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` | Internal API 契約スタイル |
| Task Definition | `prompts/definitions/tasks/api-int-001-reco-health-check/api-contract-spec.yaml` | #392 scope |
| Epic Definition | `prompts/definitions/epics/api-int-001-reco-health-check/epic.yaml` | #391 scope |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で、OpenAPI（internal）Task の入力として十分か
- API一覧の API-INT-001（endpoint / Method GET / Internal / Provider reco・Consumer api / MVP）と一致しているか
- API設計方針書 §11.3（Internal 保護）および §8.2（data + meta）と矛盾していないか
- Provider（apps/reco エンドポイント層）/ Consumer（apps/api）の I/F 境界が明確か
- 推薦パイプライン・MOD-RECO 実装詳細を含んでいないか
- `packages/contracts/openapi/internal-reco-api.yaml` への反映方針が明確か（本 Task でファイル未変更）
- secret / `.env` 実値が含まれていないか

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint（`GET /internal/reco/v1/health`）と api→reco I/F 境界
- Internal API Key をヘルスチェックでも必須とする方針
- Response `data.status` の値域（`ok` / `degraded` / `unavailable`）と MVP での必須範囲
- `data.version` を optional とした方針
- OpenAPI Contract Task への分離方針（`internal-reco-api.yaml`）

---

## 17. 備考

- 本書は `prompts/templates/docs/api-contract-spec.md` に準拠した Phase1 ①（1a）成果物である。
- reco を FastAPI 等の常駐サービスとして動かす前提（API一覧 備考）に整合する。
- 本 API は API-INT-002（推薦実行）の前提となる接続確認用途であり、推薦ロジックは実行しない。
