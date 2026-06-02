# recoディレクトリ構成不整合棚卸し

## 1. 目的と基準

- 目的: `apps/reco` 配下のパス表記揺れを棚卸しし、`src/reco` 統一方針への更新対象を特定する。
- 基準正本: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md`
- 本棚卸しは docs / prompts の不整合整理のみを対象とし、実装変更は扱わない。

## 2. 対象範囲

- `docs/` 配下の `apps/reco` 関連記述
- `prompts/definitions/` 配下の `epic_scope` / `review_points` / 背景記述

## 3. 分類定義

| 分類 | 定義 | 優先度目安 |
| --- | --- | --- |
| 正本矛盾 | 正本方針（`src/reco`）と直接矛盾する記述 | 高 |
| 運用ルール矛盾 | Epic/Task境界やレビュー運用の前提が旧構成依存になっている記述 | 中 |
| 参照メモ | 背景メモ・注記等で旧パスが残る記述（直ちに誤動作はしない） | 低 |

## 4. 不整合一覧（出典ファイル単位）

| No | 分類 | 出典ファイル | 現在記述（要約） | `src/reco` 基準との差分 | 優先度 | 後続Task |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 正本矛盾 | `prompts/definitions/epics/api-int-002-reco-recommendation-run/epic.yaml` | エンドポイント層を `apps/reco/src/app/**` と定義 | 正式方針は `apps/reco/src/reco/api/**` | 高 | `definition-update` |
| 2 | 正本矛盾 | `prompts/definitions/epics/mod-reco-001-recommendation-orchestrator/epic.yaml` | モジュール境界を `apps/reco/src/modules/**` 基準で記述 | 正式方針は `apps/reco/src/reco/application/**` を基準化 | 高 | `definition-update` |
| 3 | 正本矛盾 | `prompts/definitions/tasks/mod-reco-001-recommendation-orchestrator/module-spec.yaml` | API-INT境界除外を `apps/reco/src/app/**` で注記 | 正式方針は `apps/reco/src/reco/api/**` で除外定義 | 高 | `definition-update` |
| 4 | 運用ルール矛盾 | `docs/00_共通/AIエージェント運用/Task Definition設計書.md` | API-INT境界説明が `apps/reco/src/app/**` 前提 | 境界規約が `src/reco/api` へ未追従 | 中 | `docs-update` |
| 5 | 運用ルール矛盾 | `docs/00_共通/AIエージェント運用/AIレビュー運用設計書.md` | レビュー観点が `apps/reco/src/app/**` / `src/modules/**` を前提 | レビュー観点を `src/reco/*` 系へ再定義が必要 | 中 | `docs-update` |
| 6 | 参照メモ | `prompts/definitions/reviews/api-int-002-reco-recommendation-run/pr-review.yaml` | リスク/確認観点に `apps/reco/src/modules` 等の旧構成メモ | 背景メモの参照先が新構成へ未置換 | 低 | `migration-guide` |
| 7 | 参照メモ | `prompts/definitions/epics/reco-directory-architecture-redesign/epic.yaml` | 「揺れ」として `src/modules/**` / `src/app/**` を併記 | 棚卸し後は旧表記を移行注記へ限定する必要 | 低 | `migration-guide` |

## 5. 更新順序（引き継ぎ）

| 順 | 作業 | Phase0 Task | 状態 |
| --- | --- | --- | --- |
| 0 | 構成定義書・OpenAPI レイアウト方針・§7.3.1 境界 | `[Task]directory-structure-review:構成定義書 再点検・更新`（#349） | **完了**（PR #351 merge） |
| 1 | `definition-update`（高優先）— 識別子 Epic `epic_scope` | `[Task]directory-structure-review:識別子Epic epic_scope・generated 整合` | 未着手（③） |
| 2 | `docs-update`（中優先）— 運用設計書・AGENTS・rules | `[Task]directory-structure-review:AGENTS・運用docs・rules のパス整合`（#352） | **PR #353**（AI Review 待ち） |
| 3 | `migration-guide`（低優先）— 参照メモの整理 | ③ または Epic PR 本文 | 未着手 |

Epic #264（recoディレクトリ構成全面再設計）の残作業は Epic #348（directory-structure-review）に吸収済み（Human 判断 2026-06-02）。

## 6. scope外明示

本Taskでは以下を実施しない。

- 実装コード変更（`apps/reco` 配下のPython実装）
- OpenAPI 変更
- DB schema 変更
- 実際の Definition/Review ファイル更新（本書は棚卸しのみ）
