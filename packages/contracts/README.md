# packages/contracts

Gift Recommendation Service の **API 契約（OpenAPI）正本** を配置する。

## 正本関係

| 対象 | 正本パス |
| ---- | -------- |
| Public API（web → api） | `openapi/public-api.yaml` |
| Internal Reco API（api → reco） | `openapi/internal-reco-api.yaml` |
| 共通 schema（Meta / Error / Envelope） | `schemas/common.yaml` |
| Orval 設定 | リポジトリルート `orval.config.ts` |
| generated（web） | `apps/web/src/generated/api/` |
| generated（api → reco） | `apps/api/src/generated/reco-client/` |

契約面の説明・Validation・エラー一覧の正本は `docs/06_実装設計/api/` の各 API 契約仕様書とする。本ディレクトリは機械可読な OpenAPI 3.0.3 定義を正とする。

## MVP 収録 API

| API ID | Method / Path | OpenAPI 操作 ID |
| ------ | ------------- | ----------------- |
| API-PUB-002 | `POST /api/v1/recommendations` | `runRecommendation` |
| API-INT-002 | `POST /internal/reco/v1/recommendations/run` | `runRecoRecommendation` |

## 参照

- 共通 schema は各 OpenAPI から `../schemas/common.yaml` を `$ref` する。
- 生成: リポジトリルートで `pnpm orval`（[利用技術スタック整理表](../../docs/05_アプリケーション設計/基盤/利用技術スタック整理表.md) §11 参照）。
- generated ファイルは手動編集しない。
