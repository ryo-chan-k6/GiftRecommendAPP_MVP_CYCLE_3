# Human Decision Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `2026-06-01-openapi-contract-home-packages-contracts` |
| Log種別       | `human-decision`      |
| 件名          | OpenAPI契約定義の正本配置を `packages/contracts/` に統一する |
| 発生日時      | 2026-06-01            |
| 記録日時      | 2026-06-01            |
| 発生元Command | `/start-epic`（事前検討） |
| 発生元Agent   | `orchestrator-ai`     |
| workstream_key | `contract-impl-task-separation` |
| 関連Issue     | `#300`                |
| 関連PR        | （未作成）            |
| Definition    | `prompts/definitions/epics/contract-impl-task-separation/epic.yaml` |
| 重要度        | `high`                |
| 状態          | `resolved`            |

---

## 2. 結論

OpenAPI契約定義の正本配置を `packages/contracts/` に統一する。generated出力先（`apps/web/src/generated/api/`・`apps/api/src/generated/reco-client/`）と Orval設定（`orval.config.ts`）はディレクトリ構成定義書の既存方針を維持する。

---

## 3. human-decision として記録する理由

ディレクトリ構成定義書内に `openapi/`（本文）と `packages/contracts/`（別表）の両記載が併存し、正本docsの矛盾解消方針はAIだけで確定すべきでないため。

### 3.1 記録対象理由

- 正本docs（ディレクトリ構成定義書）の矛盾解消方針であり、横断影響が大きい
- 後続の Contract Task / Implementation Task のパス基準を決定づける

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。本ログは正本docs間の矛盾解消という人間判断を記録するために作成する。正本は AIログ運用ルール §13 とする。

---

## 4. 発生経緯

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 発生元                | `planning`                             |
| 関連Task              | パス標準化Task（本Epic配下 Task1 予定） |
| 関連Task Definition   | `prompts/definitions/epics/contract-impl-task-separation/epic.yaml` |
| 関連Command           | `/start-epic`                          |

### 4.1 詳細

設計・開発プロセス再検討の中で、Orval前提フローと現行運用の不整合を整理した際、OpenAPI契約定義の配置が `openapi/`・`packages/contracts/`・`docs/openapi/`・`apps/web/src/lib/api-client/.../generated` の4系統に分裂していることが判明した。

---

## 5. 判断が必要な事項

- OpenAPI契約定義の正本を `openapi/`（ルート）と `packages/contracts/` のどちらにするか

---

## 6. 背景

ディレクトリ構成定義書では、本文に `openapi/public-api.yaml` / `openapi/internal-reco-api.yaml`（ルート `openapi/`）の記載がある一方、別表に `packages/contracts/` を「API契約定義を配置」と記載しており、内部で矛盾している。contract-definition schema/example は `docs/openapi/openapi.yaml` を、API-PUB-002 Task は `openapi/paths/recommendations` と `apps/web/src/lib/api-client/.../generated` を参照しており、系統が統一されていない。

---

## 7. 選択肢

| 案  | 内容 | メリット | デメリット |
| --- | ---- | -------- | ---------- |
| A   | `openapi/`（ルート）に統一 | 構成定義書本文と一致 | packages配下の共有契約管理と分離、monorepo配下の一貫性が下がる |
| B   | `packages/contracts/` に統一 | monorepoの共有パッケージとして契約を一元管理、構成定義書別表と一致 | 構成定義書本文の `openapi/` 記載を是正する必要がある |

---

## 8. AIの推奨

案B（`packages/contracts/`）。monorepo構成における共有契約パッケージとして自然であり、web/api双方のgenerated生成元を一元管理できるため。

---

## 9. 人間に決めてほしいこと

OpenAPI契約定義の正本を `packages/contracts/` に統一してよいか。

---

## 10. 判断後に必要な対応

- ディレクトリ構成定義書本文の `openapi/` 記載を `packages/contracts/` 方針へ是正する
- contract-definition schema/example・API-PUB-002 Task の参照パスを統一する

---

## 11. 確認した事実

- 構成定義書本文に `openapi/public-api.yaml` / `openapi/internal-reco-api.yaml` の記載がある
- 構成定義書別表に `packages/contracts/`（API契約定義配置）の記載がある
- contract-definition schema/example は `docs/openapi/openapi.yaml` を参照している
- API-PUB-002 Task は `openapi/paths/recommendations` と `apps/web/src/lib/api-client/.../generated` を参照している

---

## 12. 推論

- パスを統一しないまま Implementation Task を並列化すると、Orval再生成時に横断手戻りが発生する可能性が高い

---

## 13. 関連情報

| 種別           | 参照                |
| -------------- | ------------------- |
| 関連docs       | docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md |
| 関連Issue      | #300                |
| 関連PR         | （未作成）          |
| 関連Branch     | refactor/epic-300-contract-impl-task-separation |

---

## 14. 人間判断結果（記録時）

| 項目       | 内容                 |
| ---------- | -------------------- |
| 判断者     | ryo-chan-k6          |
| 判断日時   | 2026-06-01           |
| 採用案     | 案B（`packages/contracts/` に統一） |
| 判断理由   | monorepoの共有契約パッケージとして契約を一元管理するため |
| 後続Issue  | #300 配下 パス標準化Task |
| 後続Task   | contract-impl-task-separation / path-standardization |
