# 成果物一覧 × Task Definition化方針

## 1. 基本方針

| 観点         | 方針                                                                      |
| ------------ | ------------------------------------------------------------------------- |
| 基本粒度     | 原則 `1成果物 = 1 Task Definition`                                        |
| 例外1        | API仕様書は `1 API = 1 Task Definition`                                   |
| 例外2        | 画面設計書は `1画面 = 1 Task Definition`                                  |
| 例外3        | バッチ仕様書は `1バッチ = 1 Task Definition`                              |
| 例外4        | テーブル定義書は `1テーブル` または `1テーブル群 = 1 Task Definition`     |
| 例外5        | OpenAPI / Orval / generated 影響があるものは `Contract Definition` を優先 |
| 正本         | 成果物docs、DDL、OpenAPI、source code等                                   |
| 作業計画     | GitHub Issue                                                              |
| 作業結果     | Pull Request                                                              |
| レビュー結果 | Pull Request                                                              |
| 通知         | Slack。ただし正本ではない                                                 |

---

## 2. Definition種別の使い分け

| 対象                                          | 使用するDefinition                                                              |
| --------------------------------------------- | ------------------------------------------------------------------------------- |
| 通常の設計書作成                              | `task-definition`                                                               |
| 画面設計書作成                                | `task-definition`                                                               |
| 個別API仕様書作成                             | `task-definition`                                                               |
| OpenAPI / Orval / generated を伴うAPI契約変更 | `contract-definition`                                                           |
| PRレビュー                                    | `review-definition`                                                             |
| レビュー指摘対応                              | `task-definition`                                                               |
| 実装作業                                      | `task-definition`                                                               |
| CI/CD・GitHub Actions変更                     | 原則 `task-definition`、横断影響が大きい場合は `contract-definition` 相当で扱う |
| AI運用・Command・Prompt改善                   | `task-definition`                                                               |
| 実験・検証作業                                | `task-definition` + 必要に応じて `experiment-log`                               |

---

## 3. 成果物種別ごとのTask化方針

| 成果物種別     | Task化単位                     | Definition種別        | 使用テンプレート                        | 備考                                   |
| -------------- | ------------------------------ | --------------------- | --------------------------------------- | -------------------------------------- |
| 方針書         | 1成果物 = 1Task                | `task-definition`     | 未作成。汎用docsテンプレート候補        | DevOps方針書、CI/CD方針書など          |
| 一覧表         | 1成果物 = 1Task                | `task-definition`     | 未作成。list/table系テンプレート候補    | API一覧、バッチ一覧、テーブル一覧など  |
| 設計書         | 1成果物 = 1Task                | `task-definition`     | 成果物別テンプレート                    | 認証・認可設計書、ログ設計書など       |
| 図・構成図     | 1成果物 = 1Task                | `task-definition`     | Mermaid / draw.io方針が必要             | システム構成図、遷移図、依存関係図など |
| 画面設計書     | 1画面 = 1Task                  | `task-definition`     | `prompts/templates/docs/screen-spec.md` | 画面一覧・画面遷移図をinputにする。命名は Task Definition設計書 §15.3 |
| API仕様書      | 1 API = 1Task                  | `task-definition`     | `api-contract-spec.md` + `api-implementation-spec.md`（1成果物に統合） | OpenAPI変更を伴う場合はContract Task化。命名は §15.2 |
| OpenAPI定義書  | 1 API変更単位 = 1Contract Task | `contract-definition` | `prompts/templates/docs/openapi-spec.md` | generated影響あり。完了後は [Contract Gate運用設計書](./Contract%20Gate運用設計書.md) を満たして Implementation 開始 |
| バッチ仕様書   | 1バッチ = 1Task                | `task-definition`     | `prompts/templates/docs/batch-spec.md`   | バッチ処理一覧をinputにする。Batch ID 正本は `BATCH-*`（§15.4） |
| テーブル定義書 | 1テーブル = 1Task              | `task-definition`     | `prompts/templates/docs/table-spec.md`   | テーブル一覧の物理テーブル名をTask識別子とし、物理ER・論理ERをinputにする |
| DDL            | 1変更単位 = 1Task              | `task-definition`     | `.sql`                                  | migration方針と連動                    |
| ソースコード   | 1機能/1モジュール = 1Task      | `task-definition`     | PRテンプレート中心                      | 実装成果物。docsではない               |
| テストケース   | 1機能/1観点群 = 1Task          | `task-definition`     | test-caseテンプレート候補               | テスト観点一覧をinputにする            |
| 運用改善資料   | 1成果物 = 1Task                | `task-definition`     | 汎用docsテンプレート候補                | P10系                                  |

---

## 3.5 Epic 粒度方針（識別子単位 Epic）

§3 の「1成果物 = 1 Task」は **Task 粒度**の方針である。**Epic 粒度**は本節で定義する。Epic は配下 Task の作業計画と**ファイル境界の宣言（`epic_scope.allowed_paths`）**を持つ親 Issue であり、AI が自動フローで作業しても scope を越境しないためのガードレールとして機能する。

### 3.5.1 基本方針

| 粒度 | 適用 | 説明 |
| ---- | ---- | ---- |
| 識別子単位（原則） | API-PUB / API-INT / SCR / BATCH / MOD-API / MOD-RECO / MOD-BATCH | 各成果物正本一覧の ID を 1 つ ＝ 1 Epic に対応させる |
| 機能・領域単位（例外） | DevOps / 横断運用 / ID 体系未整備領域 | 識別子が定まらない領域に限り、機能・領域単位の Epic を例外として残す |

「呼び出すモジュール側のファイルを API Epic 子 Task が触る場合は、必ず該当 `MOD-*` モジュール Epic配下の Task として別途切る」を原則とする。API Epic 配下 Task の差分が `epic_scope.allowed_paths` 外に出るとき、AI Agent は作業を停止し、`human_decision_points` に理由を残す。

識別子単位 Epic は `06_実装設計` の仕様書と `07_開発・単体テスト` の実装を一気通貫で束ねる。GitHub Projects の Epic `Phase` は完了ゲートとして原則 `07_開発・単体テスト` とし、仕様書フェーズの進捗は子 Task の `Phase`（`06_実装設計`）で追う（[Projects運用ルール](../プロジェクト管理/Projects運用ルール.md) §6.1）。

### 3.5.2 識別子単位 Epic と `epic_scope.allowed_paths`

| 成果物識別子 | Epic タイトル | 配下 Task の典型 | `epic_scope.allowed_paths` 例 |
| ------------ | ------------- | ---------------- | ----------------------------- |
| `API-PUB-NNN` | `[Epic]API-PUB-NNN:{機能名}` | API仕様書・OpenAPI・実装・単体テスト（api 層のみ） | `apps/api/src/app/<resource>/**`、`apps/web/src/lib/api-client/<resource>/**`、`openapi/paths/<resource>/**` |
| `API-INT-NNN` | `[Epic]API-INT-NNN:{機能名}` | 同上（reco エンドポイント層のみ） | `apps/reco/src/app/<endpoint>/**`、`openapi/internal/<endpoint>/**` |
| `SCR-NNN` | `[Epic]SCR-NNN:{画面名}` | 画面仕様書・実装・テスト | `apps/web/src/app/<route>/**`、`apps/web/src/features/<feature>/**` |
| `BATCH-NNN` | `[Epic]BATCH-NNN:{バッチ名}` | バッチ仕様書・実装・テスト | `apps/batch/src/<batch>/**`、`.github/workflows/batch-<batch>*.yml` |
| `MOD-RECO-NNN` | `[Epic]MOD-RECO-NNN:{Recoモジュール名}` | Recoモジュール仕様・実装・単体テスト | `apps/reco/**` の該当モジュール範囲（エンドポイント層 `apps/reco/src/app/**` を**除く**） |
| `MOD-API-NNN` / `MOD-BATCH-NNN` | `[Epic]{MOD-ID}:{モジュール名}` | API / Batch モジュール仕様・実装・単体テスト | `apps/api/**` / `apps/batch/**` の該当モジュール範囲 |
| 例外（DevOps 等） | `[Epic]<機能・領域名>` | 既存方針 | 個別記載（範囲が広い場合は明示注記） |

ファイル境界は、各 Epic Definition の `epic_scope.allowed_paths` に列挙する。schema 詳細は `prompts/definitions/_schemas/epic-definition.schema.md` §4、命名は [Task Definition設計書](./Task%20Definition設計書.md) §15.0（Epic タイトル規約）を正とする。

### 3.5.3 Epic 間依存

Epic 間の依存関係は、各 Epic / Task Definition の `dependencies.epics`（Epic Issue 番号配列）に明示する。典型依存は以下とする。

```mermaid
flowchart LR
  EpicSCR["Epic SCR-NNN"]
  EpicAPI["Epic API-PUB-NNN"]
  EpicINT["Epic API-INT-NNN"]
  EpicMOD["Epic MOD-RECO-NNN"]

  EpicSCR -->|"依存"| EpicAPI
  EpicAPI -->|"依存"| EpicINT
  EpicINT -->|"依存"| EpicMOD
```

依存 Epic が `Done` でない場合、`/start-task` は子 Task の `human_decision_points` への理由記載を必須とする（[`.cursor/commands/start-task.md`](../../../.cursor/commands/start-task.md)）。

### 3.5.4 例: `[Epic]API-PUB-002:レコメンド実行`

| 区分 | 内容 |
| ---- | ---- |
| 配下 Task の対象 | `apps/api/src/app/recommendations/` 配下の route / controller / application service / validator / mapper / reco-client、`apps/web/src/lib/api-client/recommendations/**`、`openapi/paths/recommendations/**`、上記の単体テスト |
| 配下 Task の対象外 | `apps/reco/**`（モジュール実装）、`apps/web/src/app/**`（画面実装）、`apps/batch/**`（バッチ実装） |
| 依存 Epic | `[Epic]API-INT-002:Reco推薦実行`、`[Epic]MOD-RECO-001:Recommendation Orchestrator` |
| 典型子 Task | `[Task]API-PUB-002:レコメンド実行API仕様書作成` / `[Task]API-PUB-002:レコメンド実行OpenAPI定義` / `[Task]API-PUB-002:レコメンド実行API実装` / `[Task]API-PUB-002:レコメンド実行API単体テスト` |

---

## 4. Phase別 Task Definition化方針

| Phase | 工程名               | Task Definition化方針                                                                                                              | 優先度 |
| ----- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| P1    | 事業構想             | 既存成果物の更新Task中心。新規作成は原則不要                                                                                       | 低     |
| P2    | ドメイン探索         | 既存成果物の更新Task中心。用語変更・概念変更時にTask化                                                                             | 中     |
| P3    | ドメイン要件定義     | MVPスコープ変更時にTask化                                                                                                          | 中     |
| P4    | ドメインモデル設計   | 推薦ロジック変更時にTask化。Request / Retrieval / Matching / Ranking / Result / Reason / Feedback / Evaluationは個別Task化しやすい | 高     |
| P5    | アプリケーション設計 | 後続06_実装設計のinputになるため、未整備・修正があれば優先Task化                                                                   | 高     |
| 06_実装設計 | 実装設計       | 現時点の主対象。画面、API、DB、バッチ、基盤を実Task Definition化する                                                               | 最高   |
| P7    | 開発・単体テスト     | 識別子単位 Epic 配下では子 Task として 07 を個別管理。Epic の Projects Phase は完了ゲート（原則 07）。横断の 07 専用 Task は必要に応じて別途 Task 化 | 高     |
| P8    | 結合・総合テスト     | テスト計画・ケース・結果記録単位でTask化                                                                                           | 中     |
| P9    | リリース             | リリース前に手順書・チェックリスト単位でTask化                                                                                     | 中     |
| P10   | 運用・改善           | MVPリリース後に分析・改善単位でTask化                                                                                              | 中     |

---

## 5. 06_実装設計の優先Task化方針

現時点で実Task Definitionの試作対象にするなら、06_実装設計を優先するのがよいです。

| 優先 | 成果物               | Task化単位                 | 使用テンプレート | 主なinput docs                                                       |
| ---- | -------------------- | -------------------------- | ---------------- | -------------------------------------------------------------------- |
| 1    | API仕様書            | 1 API = 1Task              | `api-contract-spec.md` + `api-implementation-spec.md` | API設計方針書、API一覧、機能一覧、モジュール一覧、エラーコード定義書。命名 §15.2 |
| 2    | 画面設計書           | 1画面 = 1Task              | `screen-spec.md` | 画面一覧、画面遷移図、API一覧、API仕様書。命名 §15.3               |
| 3    | OpenAPI定義書        | 1 API変更 = 1Contract Task | `openapi-spec.md` | API仕様書、API設計方針書、エラーコード定義書                         |
| 4    | 物理ER               | 1成果物 = 1Task            | `physical-er-spec.md` | 論理ER、テーブル一覧、正本定義表                                 |
| 5    | テーブル定義書       | 1テーブル = 1Task          | `table-spec.md`  | 物理ER、論理ER、enum定義書、コード定義書。Task識別子は物理テーブル名 |
| 6    | DDL                  | 1変更単位 = 1Task          | `.sql`           | テーブル定義書、マイグレーション方針書                               |
| 7    | バッチ仕様書         | 1バッチ = 1Task            | `batch-spec.md`  | バッチ処理一覧、外部商品データ連携設計書。命名 §15.4（Batch ID: `BATCH-*`） |
| 8    | Recoモジュール仕様書 | 1モジュールID = 1Task        | `module-spec.md` | Recoモジュール一覧、Matching / Ranking / Retrieval定義書             |
| 9    | 環境変数定義書       | 1成果物 = 1Task            | 未作成           | 基盤構成設計書、環境設計方針書                                       |
| 10   | 基盤構成設計書       | 1成果物 = 1Task            | 未作成           | システム物理構成図、利用技術スタック整理表                           |

> 上記Task化優先順を **Phase0〜Phase4の実行段取り**（基盤先行→共通基盤→個別縦割り）として時系列に並べ、各PhaseのEpic/Task分割・依存・並列（worktree/マルチエージェント）方針へ展開したものは、[実装フェーズ実行プロセス設計書](../プロジェクト管理/実装フェーズ実行プロセス設計書.md) を正本とする。本節はTask化単位・優先順の正本であり、実行段取りは同設計書を参照する。

---

## 6. 推奨する最初の実Task Definition試作対象

最初の試作は、以下のどちらかがよいです。

| 候補                  | 推奨度 | 理由                                                                 |
| --------------------- | ------ | -------------------------------------------------------------------- |
| 個別API仕様書作成Task | 高     | `api-contract-spec.md` / `api-implementation-spec.md` が作成済みで、Contract Taskとの接続も確認しやすい |
| 画面設計書作成Task    | 高     | `screen-spec.md` が作成済みで、画面・API連携のTask設計を検証しやすい |
| 物理ER作成Task        | 中     | `physical-er-spec.md` は作成済みだが、DB全体影響が大きいため先に一覧整備が必要 |
| OpenAPI定義書作成Task | 中     | `openapi-spec.md` は作成済み。Contract Definition検証にはよいが、最初の通常Taskとしては重い |

推奨は、**個別API仕様書作成Task**です。

理由は、以下の流れを一気に検証できるためです。

```
API一覧
  ↓
個別API仕様書
  ↓
OpenAPI定義
  ↓
Orval
  ↓
generated client
  ↓
provider / consumer 影響確認
```
---

## 7. 実Task Definition作成時の標準構造

個別Task Definitionでは、最低限この対応を必ず入れます。

```
input:
  docs:
    - path:"<参照する正本docs>"
      required: true
      purpose:"<参照目的>"
  templates:
    - path:"<使用テンプレート>"
      required: true
      purpose:"<テンプレート利用目的>"
      applies_to:
        -"<output.docs[].path と対応>"

output:
  docs:
    - path:"<作成・更新する成果物path>"
      action:"create"
      required: true
      template:"<input.templates[].path と同じ>"
```
---

## 8. 成果物別のDefinition化判断表

| 成果物                         | Definition化 | 理由                                  |
| ------------------------------ | ------------ | ------------------------------------- |
| 課題定義書                     | 必要時のみ   | 事業方針変更時に更新Task化            |
| ターゲット定義書               | 必要時のみ   | ターゲット変更時に更新Task化          |
| 価値仮説定義書                 | 必要時のみ   | 検証方針変更時に更新Task化            |
| MVPスコープ定義書              | 必要         | MVP範囲変更の影響が大きいため         |
| ドメイン概念一覧               | 必要         | 後続成果物への影響が大きいため        |
| ユビキタス言語集               | 必要         | 用語変更時は全体影響あり              |
| ドメイン概念連関図             | 必要         | ドメイン構造変更時にTask化            |
| ユースケース一覧               | 必要         | 画面・機能・APIのinputになるため      |
| 機能要件定義書                 | 必要         | 機能一覧・実装範囲のinput             |
| 非機能要件定義書               | 必要         | 基盤・セキュリティ・性能設計のinput   |
| MVP対象機能一覧                | 必要         | 実装Taskのscope判断に必要             |
| 制約・対象外一覧               | 必要         | out_of_scope判断に必要                |
| P4ドメインモデル系成果物       | 必要         | 推薦ロジックとDB/API設計の中核        |
| P5アプリケーション設計系成果物 | 必要         | 06_実装設計の直接input                |
| 06_実装設計系成果物            | 必須         | これから実Task Definition化する主対象 |
| P7開発成果物                   | 必須         | 実装Issue・PRと直接対応する           |
| P8テスト成果物                 | 必須         | 品質判断・リリース判定に必要          |
| P9リリース成果物               | 必須         | リリース前にTask化                    |
| P10運用・改善成果物            | 必要         | MVPリリース後にTask化                 |

---

## 9. 仕様書別Task Definition雛形の追加順序

仕様書量産に向けたTask Definition雛形は、以下の順で整備する。

| 優先 | 仕様書種別 | 現状 | 基準テンプレート | Definition雛形パス例 | 識別子 |
| ---- | ---------- | ---- | ---------------- | -------------------- | ------ |
| 1 | 画面仕様書 | 作成済み例あり | `prompts/templates/docs/screen-spec.md` | `prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml` | `SCR-*` |
| 2 | API仕様書 | 作成済み例あり | `api-contract-spec.md` + `api-implementation-spec.md` | `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml` | `API-PUB-*` / `API-INT-*` |
| 3 | Recoモジュール仕様書 | 追加候補 | `prompts/templates/docs/module-spec.md` | `prompts/definitions/tasks/mod-reco-001-recommendation-orchestrator/module-spec.yaml` | `MOD-RECO-*` |
| 4 | バッチ仕様書 | 作成済み例あり | `prompts/templates/docs/batch-spec.md` | `prompts/definitions/tasks/batch-003-rakuten-item-pseudo-diff/batch-spec.yaml` | `BATCH-*` |
| 5 | DBテーブル定義書 | 追加候補 | `prompts/templates/docs/table-spec.md` | `prompts/definitions/tasks/recommendation-request-table/table-spec.yaml` | 物理テーブル名 |
| 6 | OpenAPI定義書 | 追加候補 | `prompts/templates/docs/openapi-spec.md` | `prompts/definitions/tasks/api-int-002-reco-recommendation-run/openapi-spec.yaml` | `API-*` |

### 9.1 既存の作成済みDefinition例

| Definition | 用途 |
| ---------- | ---- |
| `prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml` | 画面仕様書Taskの基準例 |
| `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml` | API仕様書Taskの基準例 |
| `prompts/definitions/tasks/batch-003-rakuten-item-pseudo-diff/batch-spec.yaml` | バッチ仕様書Taskの基準例 |

### 9.2 次に追加するDefinition雛形

| 優先 | Definition雛形 | 追加理由 |
| ---- | -------------- | -------- |
| 1 | Public API仕様書Task（例: `api-pub-002-recommendation-run/api-spec.yaml`） | web向けAPI仕様書作成の基準例が必要 |
| 2 | Recoモジュール仕様書Task（例: `mod-reco-001-recommendation-orchestrator/module-spec.yaml`） | `MOD-RECO-*` 個別Epic配下のTask粒度を確認するため |
| 3 | DBテーブル定義書Task（例: `recommendation-request-table/table-spec.yaml`） | 物理テーブル名をTask識別子にする運用を確認するため |
| 4 | OpenAPI定義書Contract Task（例: `api-int-002-reco-recommendation-run/openapi-spec.yaml`） | API仕様書からOpenAPI / generatedへ接続する流れを確認するため |

---

## 10. docsテンプレート整備状況

現時点で `prompts/templates/docs/` に存在するdocsテンプレートは以下です。

| テンプレート | 対象成果物 |
| ------------ | ---------- |
| `prompts/templates/docs/api-contract-spec.md` | API契約仕様書（契約面） |
| `prompts/templates/docs/api-implementation-spec.md` | API実装仕様書（実装面） |
| `prompts/templates/docs/screen-spec.md` | 画面仕様書 |
| `prompts/templates/docs/batch-spec.md` | バッチ仕様書 |
| `prompts/templates/docs/module-spec.md` | Recoモジュール仕様書 |
| `prompts/templates/docs/table-spec.md` | テーブル定義書 |
| `prompts/templates/docs/openapi-spec.md` | OpenAPI定義書 |
| `prompts/templates/docs/physical-er-spec.md` | 物理ER |
| `prompts/templates/docs/enum-spec.md` | enum定義書 |

追加で整備した方がよいテンプレート候補は以下です。

| 優先 | テンプレート候補 | 対象成果物 |
| ---- | ---------------- | ---------- |
| 1    | `prompts/templates/docs/api-list.md` | API一覧 |
| 2    | `prompts/templates/docs/infra-spec.md` | 基盤構成設計書 |
| 3    | `prompts/templates/docs/env-var-spec.md` | 環境変数定義書 |
| 4    | `prompts/templates/docs/test-case-list.md` | テストケース一覧 |
