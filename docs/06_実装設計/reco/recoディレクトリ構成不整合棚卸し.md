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

1. `definition-update`（高優先）  
   Epic/Task Definition の `allowed_paths` / `forbidden_paths` / review points を `src/reco` 基準へ統一する。
2. `docs-update`（中優先）  
   Task Definition設計書・AIレビュー運用設計書の境界説明を `src/reco` 基準へ更新する。
3. `migration-guide`（低優先）  
   旧表記を残す必要がある箇所を「移行履歴/参照メモ」に限定し、現行ルール本文から分離する。

## 6. scope外明示

本Taskでは以下を実施しない。

- 実装コード変更（`apps/reco` 配下のPython実装）
- OpenAPI 変更
- DB schema 変更
- 実際の Definition/Review ファイル更新（本書は棚卸しのみ）
