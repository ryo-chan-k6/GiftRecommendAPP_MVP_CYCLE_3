# Cross-Cutting Impact Log — Public Reason Points/Detail Contract Epic 準備

## 1. 概要

| 項目          | 内容 |
| ------------- | ---- |
| Log ID        | `2026-07-16-public-reason-points-detail-contract-epic-prep` |
| Log種別       | `cross-cutting` |
| 件名          | Public `reasonPoints` / `reasonDetail` 任意追加（横断 Contract Epic）起票用影響整理 |
| 発生日時      | 2026-07-16 |
| 記録日時      | 2026-07-16 |
| 発生元        | SCR-005 #1390 Human 判断（案 B） |
| 関連Issue     | `#1397`（Contract Epic）/ `#1398`（Contract Task）/ 要求元 `#1390` `#1389` |
| 親 Epic       | `#1397` `[Epic]API-PUB-002:Public Reason詳細フィールド追加` |
| 関連PR        | なし（Contract 作業前） |
| 重要度        | `high` |
| 状態          | `in_progress`（Epic/Task 起票済み。実作業は `/work-issue`） |

Human 判断正本: [2026-07-16-scr-005-public-reason-points-detail-contract.md](../human-decisions/2026-07-16-scr-005-public-reason-points-detail-contract.md)

---

## 2. 結論（エージェント向け要約）

**並行中の他エージェント作業がすべて develop に merge された後**、他エージェント Task を止め、**横断 Contract Epic** を起票して実施する。

目的: API-PUB-002 Public `data.items[]` に `reasonPoints` / `reasonDetail` を **任意追加**し、OpenAPI・generated・api マッピング・関連 docs を整合させる。  
SCR-005 実装・単体テストは本 Contract 完了後に着手する。

破壊性: **非破壊**（optional フィールド追加のみ。必須化しない）。

---

## 3. 着手ガード（必須）

| # | 条件 | 確認 |
| - | ---- | ---- |
| 1 | 並行エージェントの変更が develop に merge 済み | Human が確認。未完了なら起票しない |
| 2 | 他エージェントの In Progress / 未 merge PR を停止または完了 | Human 判断 |
| 3 | develop が安定し、Contract 専用 worktree を切れる | `git fetch` + worktree |
| 4 | SCR-005 画面仕様 §8.3 案 B が正本として存在する | `docs/06_実装設計/web/SCR-005_*.md` |

**禁止**: 並行 OpenAPI / api / web recommendation-result 変更と同時に本 Contract を進めない。

---

## 4. 推奨 Epic / Task 構成（起票時案）

### 4.1 Epic

| 項目 | 推奨値 |
| ---- | ------ |
| Issue タイトル例 | `[Epic]API-PUB-002:Public Reason詳細フィールド追加`（識別子・文言は起票時に Human 確定） |
| unit / type | `epic` / `feature` または contract 系 |
| Branch base / PR target | `develop` |
| 依存 | API-PUB-002 #357（merge 済み）、SCR-005 #1389（利用側・blocked） |
| 起票手段 | `/create-contract-task` または Orchestrator による Epic Definition 新規 |

### 4.2 子 Task 分割案

| 順 | Task | 主成果物 |
| --: | ---- | -------- |
| 1 | 契約仕様・方針 docs 追随 | API-PUB-002 契約仕様書、API-INT-002 の Public 表面化注記、recommendation_reason 定義書 §5.5、必要なら SCR-006 注記 |
| 2 | OpenAPI + Orval generated | `packages/contracts/openapi/public-api.yaml`、web/api 側 generated |
| 3 | api マッピング実装 | `apps/api` response-mapper（Internal → Public） |
| 4 | 契約・マッピング単体テスト | api unit tests |

※ 1〜3 を 1 Task にまとめるかは Contract Gate 運用と Human 判断に従う。分割する場合も **同一 Contract Epic** 配下とする。

---

## 5. 契約変更案（確定方針）

| 項目 | 型 | 必須 | 内容 |
| ---- | -- | ---- | ---- |
| `reasonPoints` | `string[]` | **任意** | 箇条書き理由。画面は 2〜3 想定 |
| `reasonDetail` | `string` | **任意** | 詳細表示用短文 |

| 条件 | 方針 |
| ---- | ---- |
| `includeReason=false` | 両フィールドとも省略可 |
| `includeReason=true` かつ Reason 成功 | 値が生成されていれば返却可（**必須ではない**） |
| Reason 失敗 / `isFallback=true` | `reasonSummary` 必須方針は現行維持。points/detail は省略してよい |
| `reasonBasis` | **引き続き Public 非返却**（API設計方針書 §18.4） |

破壊的変更: **なし**（追加のみ）。

---

## 6. 影響ファイル（想定）

### 6.1 docs（契約・整合）

| パス | 変更内容 |
| ---- | -------- |
| `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` | §7.3.2 に両フィールド追加。§7.3.2.1「返却しない」から除外 |
| `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` | Public へ渡す Reason 一覧の更新（現状 summary/badges/caution のみ表記） |
| `docs/06_実装設計/database/recommendation_reason_テーブル定義書.md` | §5.5「Public で返さない」から `reason_detail` / `reason_points_json` を外す（または Public 任意返却に改記） |
| `docs/06_実装設計/web/SCR-006_商品詳細画面画面仕様書.md` | 「Public に無い」前提の記述見直し（表示するかは SCR-006 方針。最低限注記更新） |
| `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` §18.3 | 既に表示対象。変更不要の可能性大（整合確認のみ） |

### 6.2 OpenAPI / generated

| パス | 変更内容 |
| ---- | -------- |
| `packages/contracts/openapi/public-api.yaml` | Item schema に optional `reasonPoints` / `reasonDetail` |
| Orval 再生成 | `apps/web` / `apps/api` の public client generated（手動編集禁止） |

### 6.3 実装

| パス | 変更内容 |
| ---- | -------- |
| `apps/api/src/app/recommendations/response-mapper.ts` | Internal item / reasonData から Public へ透過 |
| `apps/api/src/app/recommendations/types.ts` | Public item 型に追加 |
| `apps/api/tests/unit/app/recommendations/**` | マッピング・スモーク更新 |
| `apps/reco` | **原則変更不要**（Internal に既に存在。未生成なら Reason Generator 側は別確認） |

### 6.4 利用側（Contract 後・SCR-005 Epic）

| パス | 変更内容 |
| ---- | -------- |
| `apps/web/src/features/recommendation-result/**` | SCR-005 実装 Task で描画（本 Contract Epic の out of scope 推奨） |

---

## 7. out_of_scope（Contract Epic でも混ぜないもの）

- SCR-005 UI 実装・単体テストそのもの（#1389 配下で Contract 後に実施）
- `reasonBasis` の Public 露出
- Reason 永続（Postgres 配線）そのものの新規設計
- 専用 route / モーダルページ新設
- `reasonPoints` / `reasonDetail` の **必須化**

---

## 8. 推奨作業手順（着手時）

```text
1. develop 安定確認・他エージェント停止
2. 横断 Contract Epic Issue + Branch（develop 起点）を作成
3. Task Definition /create-contract-task 相当を整備
4. 契約仕様書 → OpenAPI → Orval generated → api mapper → テスト
5. Contract Epic PR → AI Review → Human Review → merge to develop
6. SCR-005 実装 Task の blocked 解除
```

Command 参照: `.cursor/commands/create-contract-task.md`、Contract Gate運用設計書。

---

## 9. SCR-005 との依存関係

```text
[並行作業] 他エージェント → develop merge
  ↓
[本メモ] 横断 Contract Epic（reasonPoints / reasonDetail 任意追加）
  ↓ develop merge
[SCR-005] 実装 → 単体テスト → Epic #1389 統合
```

画面仕様正本（案 B）: `docs/06_実装設計/web/SCR-005_推薦理由詳細表示画面仕様書.md` §8.3

---

## 10. Human Review 観点（Contract 起票・実施時）

- 任意追加で足りるか（必須化が必要になっていないか）
- Internal → Public のマッピング元（`resultItems[]` vs `reasonData.items[]`）をどちらを正とするか
- SCR-006 で同フィールドを表示するか、SCR-005 のみとするか
- ペイロード肥大・文言ポリシー（禁止表現）を Public 露出で再確認するか
