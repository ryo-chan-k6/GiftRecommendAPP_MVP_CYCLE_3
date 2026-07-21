# Human Decision Log

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-07-09-api-int-002-implementation-spec-human-review-decisions` |
| Log種別       | `human-decision` |
| 件名          | API-INT-002 実装仕様書 §12 未決事項の Human Review 確定 |
| 発生日時      | 2026-07-09 |
| 記録日時      | 2026-07-09 |
| 発生元        | Human Review（#1091 / PR #1094） |
| 関連Issue     | `#1091` |
| 親 Epic       | `#366` |
| 関連PR        | `#1094` |
| 重要度        | `high` |
| 状態          | `resolved` |

---

## 2. 結論

`API-INT-002_Reco推薦実行API実装仕様書.md` §12 に列挙していた 5 件の未決事項を、Human Review にてすべて確定した。正本は実装仕様書 §12.1 および各反映節（§3.3 / §3.4 / §4 / §6 / §8）。

---

## 3. 確定事項

### 3.1 No.1 CompositionMode デフォルト

| 項目 | 確定内容 |
| ---- | -------- |
| エンドポイント層 | `build_composition_ports(CompositionMode.PRODUCTION)` **固定** |
| 環境変数切替 | MVP では **導入しない** |
| `DEFAULT` 利用 | Orchestrator 単体テスト・DI 明示注入時のみ |

### 3.2 No.2 `response_built` 記録主体

| 項目 | 確定内容 |
| ---- | -------- |
| `phase_log` | **Orchestrator 終了時に一本化**（既存実装・単体テストと整合） |
| エンドポイント層 | `phase_log` は記録しない。HTTP access log のみ |

### 3.3 No.3 Internal API Key 環境変数名

| 項目 | 確定内容 |
| ---- | -------- |
| 環境変数 | **`RECO_INTERNAL_API_KEY`** |
| Header | `X-Internal-Api-Key` |
| api / reco | 同一 secret 値（環境設計書・認証・認可方針書・既存 settings と整合） |

### 3.4 No.4 OpenAPI 差分修正タイミング

| 項目 | 確定内容 |
| ---- | -------- |
| 実施タイミング | **#1091（実装仕様書 Task）merge 完了後** |
| 位置づけ | reco エンドポイント実装 Task（Phase4b 2/3）の **直前** |
| Branch | 親 Epic Branch `feature/epic-366-api-int-002-reco-recommendation-run` |
| エージェント引継ぎ | `ai-logs/cross-cutting/2026-07-09-api-int-002-openapi-contract-task-handover.md` |

### 3.5 No.5 `warnings` 発火閾値（MVP 初期値）

| code | 確定閾値 |
| ---- | -------- |
| `LOW_CANDIDATES_AFTER_MATCHING` | `matchingCount >= 1` かつ `matchingCount < min(topK, 5)` |
| `FEATURE_DISTRIBUTION_SKEW` | `metricSummary.featureDistribution` の任意 1 次元で `mean > 0.85` または `mean < 0.15` |

`topK` は Request `execution.topK`（未指定時 ui デフォルト 10）。閾値は実装 Task で定数モジュールに集約し、C4 reco-quality 後に調整可。

---

## 4. 正本反映先

| 成果物 | パス |
| ------ | ---- |
| 実装仕様書 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API実装仕様書.md` |
| OpenAPI Contract Task 引継ぎ | `ai-logs/cross-cutting/2026-07-09-api-int-002-openapi-contract-task-handover.md` |

---

## 5. 備考

- 契約仕様書（#368）§14.2 は引き続き「未決事項なし」。本確定は **実装面** の論点のみ。
- No.4 の Contract Task は本 PR（#1094）の scope 外。別 Task Issue として起票する。
