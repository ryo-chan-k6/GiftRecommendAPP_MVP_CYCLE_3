# Cross-Cutting Impact Log — エージェント引継ぎメモ

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-07-09-api-int-002-openapi-contract-task-handover` |
| Log種別       | `cross-cutting` |
| 件名          | API-INT-002 OpenAPI Contract Task エージェント引継ぎ |
| 発生日時      | 2026-07-09 |
| 記録日時      | 2026-07-09 |
| 発生元        | Human Review #1091（実装仕様書 §12 No.4 確定） |
| 関連Issue     | `#1091`（前提）/ 次 Task は **新規 Issue 起票** |
| 親 Epic       | `#366` `[Epic]API-INT-002:Reco推薦実行` |
| 関連PR        | `#1094`（実装仕様書。merge 後に本 Task 着手） |
| 重要度        | `high` |
| 状態          | `pending`（#1091 merge 待ち） |

---

## 2. 結論（エージェント向け要約）

**#1091 / PR #1094 merge 完了後**、親 Epic Branch 上で **API-INT-002 専用 OpenAPI Contract Task** を実施する。  
目的は `packages/contracts/openapi/internal-reco-api.yaml` を契約仕様書（#368）に追随させ、Orval 再生成まで完了すること。  
**reco エンドポイント実装 Task（Phase4b 2/3）の開始条件** とする。

---

## 3. Phase4b 上の位置づけ

```text
[完了] #1091 実装仕様書（Phase4b 1/3）← PR #1094
  ↓ merge 後
[次] OpenAPI Contract Task（本メモ）     ← 今ここを起票・実施
  ↓
[その次] reco エンドポイント実装 Task（Phase4b 2/3）
  ↓
[その次] API-INT-002 単体テスト Task（Phase4b 3/3）
```

参照: `docs/00_共通/プロジェクト管理/実装フェーズ実行プロセス設計書.md` §6.6、`API-INT-002_Reco推薦実行API実装仕様書.md` §6

---

## 4. 作業開始条件（ガード）

| # | 条件 | 確認方法 |
| - | ---- | -------- |
| 1 | PR #1094 が親 Epic Branch に merge 済み | `gh pr view 1094 --json state,mergedAt` |
| 2 | 実装仕様書が Epic Branch に存在 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API実装仕様書.md` |
| 3 | 契約仕様書が正本として確定済み | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md`（#368 / PR #372） |
| 4 | Branch base | `feature/epic-366-api-int-002-reco-recommendation-run` |
| 5 | PR target | 同上（Task PR は develop 不可） |

---

## 5. 推奨 Task 起票

| 項目 | 推奨値 |
| ---- | ------ |
| Issue タイトル | `[Task]API-INT-002:Reco推薦実行OpenAPI契約反映` |
| Issue unit / type | `task` / `contract` または `docs` |
| area | `reco` |
| Epic | #366 |
| Branch 例 | `contract/task-<issue-number>-api-int-002-internal-reco-openapi-sync` |

**参考 Task Definition:** `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-contract-spec.yaml`  
→ 本 Task は **YAML + generated 実変更** のため、専用 Definition を新規作成すること。

---

## 6. scope（実施すること）

| 対象 | 内容 |
| ---- | ---- |
| OpenAPI 正本 | `packages/contracts/openapi/internal-reco-api.yaml` |
| 入力正本 | 契約仕様書 §10、実装仕様書 §6 差分表 |
| Orval | `orval.config.ts` に従い再生成 |
| generated | `apps/api/src/generated/reco-client/` |

### 6.1 反映必須差分

| 項目 | 契約（正） | OpenAPI（現状・要修正） |
| ---- | ---------- | ------------------------ |
| Item 配列キー | `data.resultItems` | `data.items` |
| `warnings` | `WarningItem[]` | `string[]` |
| 0 件 `resultStatus` | `completed` | enum に `empty` あり |
| `MetricSummary` | mean/p95 固定 properties | 要整合 |

---

## 7. out_of_scope

- 契約仕様書・実装仕様書の変更
- apps/reco エンドポイント実装
- apps/api wrapper 実装（generated 再生成のみ）

---

## 8. 推奨作業手順

```text
1. Task Definition + Issue 起票
2. Epic Branch から Task Branch 作成
3. internal-reco-api.yaml 更新
4. Orval 再生成
5. contract-check / apps/api typecheck
6. PR（target: feature/epic-366-api-int-002-reco-recommendation-run）
```

---

## 9. 関連正本

| 種別 | パス |
| ---- | ---- |
| 契約仕様書 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` |
| 実装仕様書 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API実装仕様書.md` |
| Human 判断 | `ai-logs/human-decisions/2026-07-09-api-int-002-implementation-spec-human-review-decisions.md` |
