# Phase0 ディレクトリ構成再検討 — 完了チェックリスト

## 1. 目的

Epic #348（directory-structure-review）の Phase0 完了時に、Phase1（API Contract 基盤・物理レイアウト移行）へ着手する前に人手で確認する項目を列挙する。

正本パス基準は [プロジェクトディレクトリ構成定義書](../ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) §8.1.1 / §8.1.2 および Task ①〜③ の merge 結果とする。

---

## 2. 子 Task 完了確認

| # | Task | Issue | PR | 確認 |
| --- | --- | --- | --- | --- |
| ① | 構成定義書 再点検・更新 | #349 | #351 | [x] merge 済み |
| ② | AGENTS・運用docs・rules のパス整合 | #352 | #353 | [x] merge 済み |
| ③ | 識別子Epic epic_scope・generated 整合 | #354 | #355 | [x] merge 済み |

---

## 3. パス基準（Phase0 確定事項）

| 領域 | 正本パス（Phase0） | Phase1 で実施 |
| --- | --- | --- |
| OpenAPI 契約 | `packages/contracts/openapi/**` | ルート `openapi/` からの物理移動 |
| Web API client（generated） | `apps/web/src/generated/api/**` | Orval 再生成・移行 |
| API reco client（generated） | `apps/api/src/generated/reco-client/**` | 同上 |
| Web wrapper | `apps/web/src/lib/**`（手書き） | `lib/api-client/**` からの整理 |
| Reco エンドポイント | `apps/reco/src/reco/api/**` | `src/app/**` からの移行 |
| Reco モジュール | `apps/reco/src/reco/application/**` 等 | `src/modules/**` からの移行 |

---

## 4. 手動確認コマンド（Phase0 完了時）

```bash
# 識別子 Epic に root openapi/paths が残っていないこと
rg 'openapi/paths' prompts/definitions/epics/api-pub-002-recommendation-run/ \
  prompts/definitions/epics/api-int-002-reco-recommendation-run/ || echo OK

# epic.yaml に lib/api-client を generated 正本として誤記していないこと（legacy 禁止パス除く）
rg 'lib/api-client' prompts/definitions/epics/ --glob '**/epic.yaml'

# AGENTS / 運用 docs にルート openapi/ がないこと
rg '^.*openapi/`' AGENTS.md docs/00_共通/AIエージェント運用/成果物一覧×Task\ Definition化方針書.md \
  .cursor/rules/architecture-consistency.mdc 2>/dev/null || true
```

`lib/api-client` のヒットは **forbidden_paths または移行注記** のみであることを確認する。

---

## 5. 識別子 Epic epic_scope 突合

| Epic | allowed_paths 要点 | forbidden 要点 |
| --- | --- | --- |
| API-PUB-002 | `packages/contracts/**`, `apps/web/src/generated/api/**`, `apps/web/src/lib/**` | `openapi/**`, `apps/web/src/lib/api-client/**` |
| API-INT-002 | `apps/reco/src/reco/api/**`, `packages/contracts/**` | `apps/reco/src/reco/application/**`, `openapi/**` |
| SCR-002 | `apps/web/src/generated/api/**`, `apps/web/src/lib/**` | `openapi/**` |
| MOD-RECO-001 | `apps/reco/src/reco/application/**` | `apps/reco/src/reco/api/**`, `apps/reco/src/modules/**` |

各 Epic の `pr-review.yaml` の forbidden 観点文言が上記と矛盾しないことを確認する。

---

## 6. Phase1 着手前ゲート（Human 判断）

- [x] Phase0 子 Task 3 件がすべて親 Epic Branch に merge 済み
- [ ] Epic PR（#348 → `develop`）の AI Review / Human Review 完了
- [x] OpenAPI 物理移行・Orval 再生成は **Phase1 Contract Task** として起票する方針を維持（Human 判断 2026-06-03）
- [x] `apps/**` / `packages/**` の実装変更を Phase0 PR に含めていない
- [x] migration-guide（棚卸し No.6–7）は Phase0 に含めない → Phase1 横断 or 別 Task（Human 判断 2026-06-03）
- [x] Phase1 着手は Human からの明示依頼まで行わない（Human 判断 2026-06-03）

---

## 7. 参照

- Epic Definition: `prompts/definitions/epics/directory-structure-review/epic.yaml`
- 棚卸し: `docs/06_実装設計/reco/recoディレクトリ構成不整合棚卸し.md`
