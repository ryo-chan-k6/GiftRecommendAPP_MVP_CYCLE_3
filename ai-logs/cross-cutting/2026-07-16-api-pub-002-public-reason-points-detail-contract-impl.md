# Cross-Cutting Impact Log — API-PUB-002 Public reasonPoints/reasonDetail Contract 実装

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-16-api-pub-002-public-reason-points-detail-contract-impl` |
| Log種別 | `cross-cutting` |
| 件名 | Public / Internal `reasonPoints` / `reasonDetail` 任意追加の Contract 実装記録 |
| 発生日時 | 2026-07-16 |
| 記録日時 | 2026-07-16 |
| 関連Issue | `#1398`（Contract Task）/ `#1397`（親 Epic） |
| 関連 Branch | `feature/task-1398-api-pub-002-public-reason-points-detail` |
| 重要度 | `high` |
| 状態 | `implemented`（PR 未作成。親 Agent が作成） |

入力正本: [2026-07-16-public-reason-points-detail-contract-epic-prep.md](./2026-07-16-public-reason-points-detail-contract-epic-prep.md)

---

## 2. 実施内容（要約）

- API-PUB-002 / API-INT-002 契約仕様書・recommendation_reason §5.5・SCR-006 注記を更新
- `public-api.yaml` / `internal-reco-api.yaml` に optional `reasonPoints` / `reasonDetail` を追加
- `pnpm orval` で web / api generated を再生成（手動編集なし）
- api response-mapper が Internal `resultItems` から Public へ透過
- reco `resultItems` / `ReasonDataItem` に同フィールドを任意で載せる（Reason Generator 経由で domain へ配線）
- `reasonBasis` は Public 非返却を維持

破壊性: **非破壊**（optional 追加のみ）

---

## 3. マッピング方針（確定反映）

| 項目 | 方針 |
| ---- | ---- |
| マッピング元 | Internal **`resultItems[]`**（推奨・採用） |
| `reasonData` | debug/evaluation 向け。ui 経路の単独ソースにしない |
| Public 必須化 | しない |
| `reasonBasis` | Public 非返却 |

---

## 4. 影響ファイル（実装時）

| 領域 | パス |
| ---- | ---- |
| docs | API-PUB-002 / API-INT-002 / recommendation_reason / SCR-006 |
| OpenAPI | `packages/contracts/openapi/public-api.yaml`, `internal-reco-api.yaml` |
| generated | `apps/web/src/generated/api/`, `apps/api/src/generated/reco-client/` |
| api | `types.ts`, `response-mapper.ts`, unit tests |
| reco | domain result / schemas / response_mapper / reason-generator executor / tests |

---

## 5. 検証

| コマンド | 結果 |
| -------- | ---- |
| `pnpm orval` | 成功 |
| `pnpm --filter api test` | pass 221 / fail 0 / skipped 2 |
| `uv run pytest tests/unit/api/test_recommendations_run_response_mapping.py`（apps/reco） | 8 passed |

---

## 6. 残論点（Human Review）

- SCR-006 で同フィールドを将来表示するか（本 Task は注記更新のみ・表示必須化なし）
- Reason Generator が `reason_detail` を常に埋めるか（現状 domain 経由で optional。未生成時は省略可）
