# Recommendation Orchestrator モジュール仕様書

## 1. ドキュメント情報

| 項目           | 内容                                                     |
| -------------- | -------------------------------------------------------- |
| ドキュメントID | `MOD-RECO-001`                                           |
| ドキュメント名 | Recommendation Orchestrator モジュール仕様書             |
| 対象システム   | Gift Recommendation Service（`apps/reco`）               |
| MVP対象        | `○`                                                      |
| 作成日         | 2026-06-25                                               |
| 更新日         | 2026-06-27                                               |

---

## 2. 概要

Recommendation Orchestrator（推薦実行制御）は、Reco オンライン推薦パイプラインの起点モジュールである。`API-INT-002`（Reco推薦実行）のエンドポイント層から `Recommendation Request` を受け取り、`MOD-RECO-002`〜`MOD-RECO-029` の各モジュールを定義済みの処理順序で呼び出し、最終的に `Recommendation Result` を返却する。

本モジュールは **実行制御** に責務を限定し、Semantic 抽出・Retrieval・Matching・Ranking・Reason 生成などのドメイン計算は各下位モジュールに委譲する。Phase Log / Error Log の **記録契機の管理** と、異常時の **パイプライン中断・エラー伝播** を担う。

---

## 3. 目的

- `apps/reco` における推薦パイプライン実装・単体テストの前提となる Orchestrator 責務を定義する
- 入出力、依存モジュール、処理順序、状態遷移、例外・ログ方針を後続実装可能な粒度で整理する
- Recoモジュール一覧・モジュール一覧・ドメイン定義書との整合を担保する

---

## 4. モジュール基本情報

| 項目 | 内容 |
| ---- | ---- |
| モジュールID | `MOD-RECO-001` |
| モジュール名 | 推薦実行制御 |
| 物理名 | `Recommendation Orchestrator` |
| 分類 | 実行制御 |
| 処理種別 | `OL` |
| 配置予定 | `apps/reco/src/reco/application/recommendation-orchestrator/**` |
| 所属Epic | `MOD-RECO-001`（Epic Issue #260） |
| MVP対象 | `○` |
| 主な呼び出し元 | `API-INT-002` Reco推薦実行の reco 内部ハンドラ（`apps/reco/src/reco/api/**`） |
| 主な呼び出し先 | `MOD-RECO-002`〜`MOD-RECO-025`（OL パイプライン）、`MOD-RECO-028` / `MOD-RECO-029`（ログ）、`MOD-RECO-024`（エラー処理） |

`MOD-API-*` / `MOD-RECO-*` / `MOD-BATCH-*` 配下のTaskでは、該当モジュールIDの責務範囲に変更を限定する。`MOD-RECO-*` では `apps/reco/src/reco/api/**` の API-INT エンドポイント層を対象に含めない。エンドポイント層の変更が必要な場合は、該当する `API-INT-*` Epic 配下 Task として扱う。

---

## 5. 責務

### 5.1 主責務

- Reco オンライン推薦パイプライン全体の **実行順序を制御** する（Recoモジュール一覧 §5.2 の処理順序に従う）
- `Recommendation Request` から **実行コンテキスト**（`recommendation_run` 紐づけ、trace、mode 等）を初期化し、下位モジュールへ受け渡す
- **実行モード**（`ui` / `evaluation` / `batch`）に応じたパイプライン起動を判定する
- 各処理フェーズの **開始・終了契機** を管理し、`MOD-RECO-028` Phase Log Writer への記録を依頼する
- 下位モジュールの失敗を検知し、`MOD-RECO-024` Reco Error Handler 経由で **標準化エラー・Error Log** へ接続する
- 正常終了時に `Recommendation Result`（Response 相当）を呼び出し元へ返却する
- 異常終了時に **Error Code**（`GRS-REC-*`）とともに失敗応答を呼び出し元へ返却する
- 推薦全体の **処理時間計測**（`recommendation_latency_ms`）の起点・終点を管理する
- `MOD-RECO-021` / `022` が成功した後、**Reason 生成の成否にかかわらず `Recommendation Result` を返却**する（§10.3）
- `MOD-RECO-023` が回復不能な場合、Reason生成定義書 §17.2 の **汎用 Reason 文**を注入し `isFallback: true` として返却する

### 5.2 対象外責務

- `API-INT-002` エンドポイント層（HTTP 受付、reco 側防御的 Validation、OpenAPI スキーマ整合）の実装
- `MOD-RECO-002`〜`MOD-RECO-029` 各モジュール **本体** のアルゴリズム・永続化詳細の実装
- `MOD-RECO-026` / `MOD-RECO-027`（処理種別 `BT`）のオンライン推薦中の直接呼び出し
- Semantic 抽出、Feature 生成、Retrieval、Matching、Ranking、Reason 生成の **計算ロジック**
- Phase Log / Error Log / Metric の **物理書き込み実装**（`MOD-RECO-028` / `MOD-RECO-029` / `MOD-RECO-025` に委譲）
- 例外の **Error Code への変換ロジック** 詳細（`MOD-RECO-024` に委譲）
- Public API（`API-PUB-002`）向けレスポンス形式への変換（`apps/api` 側責務）
- OpenAPI / Orval / generated の変更
- DB schema / DDL の変更

---

## 6. 入出力

### 6.1 入力

| 入力 | 型 / 構造 | 必須 | 生成元 | 用途 | 備考 |
| ---- | --------- | ---- | ------ | ---- | ---- |
| `recommendation_request` | `RecommendationRequest`（RecommendationRequest定義書） | `true` | `API-INT-002` reco 内部ハンドラ | 推薦条件・mode・top_k 等の起点入力 | `recommendation_request_id` を含む |
| `trace_id` | `string` | `true` | 呼び出し元（api / batch） | 横断トレース | ログ・Phase Log の `trace_id` に引き継ぐ |
| `execution_mode` | `ui` \| `evaluation` \| `batch` | `true` | `recommendation_request.mode` | パイプライン起動判定 | Recoモジュール一覧 §6.1 実行モード |
| `caller_context` | 呼び出し元メタデータ | `false` | `API-INT-002` / Offline Evaluation | 評価・再実行時の付加情報 | 詳細は実装 Task で型定義 |

### 6.2 出力

| 出力 | 型 / 構造 | 利用先 | 用途 | 備考 |
| ---- | --------- | ------ | ---- | ---- |
| `recommendation_result` | `RecommendationResult`（RecommendationResult定義書） | `API-INT-002` reco 内部ハンドラ → `apps/api` | 推薦結果の正本 | 正常終了時 |
| `execution_context` | パイプライン実行コンテキスト | 下位 `MOD-RECO-*` | run_id、config version、中間成果物の受け渡し | Orchestrator 内部状態 |
| `reco_error` | 標準化 reco エラー | 呼び出し元 | 失敗時の Error Code・メッセージ粒度 | `MOD-RECO-024` 経由で生成 |
| `phase_log_events` | Phase 記録依頼 | `MOD-RECO-028` | フェーズ開始・終了・失敗の記録 | Orchestrator は契機管理のみ |
| `error_log_events` | Error 記録依頼 | `MOD-RECO-029` | 失敗時のエラー詳細記録 | `MOD-RECO-024` 経由が原則 |

---

## 7. 依存関係

### 7.1 依存モジュール

| 依存先 | 方向 | 用途 | 失敗時の扱い | 備考 |
| ------ | ---- | ---- | ------------ | ---- |
| `MOD-RECO-003` Config Version Resolver | 呼び出し | 利用 config / model version の解決 | パイプライン中断、`GRS-REC-003` | 物理呼び出し順 2。論理順序 3。**`002` INSERT より前**（§8.2.1 / `MOD-RECO-003` §8.3.7） |
| `MOD-RECO-002` Recommendation Run Recorder | 呼び出し | 推薦実行単位（`recommendation_run`）の INSERT / 状態遷移 | パイプライン中断、`GRS-REC-002` 相当 | 物理呼び出し順 3。論理順序 2。**`003` 解決後に INSERT**（§8.2.1） |
| `MOD-RECO-004` User Semantic Extractor | 呼び出し | Semantic Concept 抽出 | パイプライン中断、`GRS-REC-004` | User Meaning フェーズ |
| `MOD-RECO-005` External Condition Feature Estimator | 呼び出し | relationship / occasion から Feature 推定 | パイプライン中断、`GRS-REC-005` | |
| `MOD-RECO-006` Internal Condition Feature Estimator | 呼び出し | preferred / non_preferred / free text から Feature 推定 | パイプライン中断、`GRS-REC-005` | |
| `MOD-RECO-007` User Feature Generator | 呼び出し | User Feature 統合生成 | パイプライン中断、`GRS-REC-005` | |
| `MOD-RECO-008` User Meaning Projector | 呼び出し | social / symbolic / λ_ctx 算出 | パイプライン中断、`GRS-REC-006` | |
| `MOD-RECO-009` User Context Builder | 呼び出し | Retrieval 用 context 生成 | パイプライン中断、`GRS-REC-005` | |
| `MOD-RECO-010` Query Embedding Generator | 呼び出し | query embedding 生成 | パイプライン中断、`GRS-REC-007` | |
| `MOD-RECO-012` Candidate Retriever | 呼び出し | Pre Hard Filter（内部 `pre_hard_filter`）と Vector Retrieval（内部 `retrieval`） | パイプライン中断、`GRS-REC-008` / `GRS-REC-009` | Orchestrator から **1 回**呼び出し |
| `MOD-RECO-013` Post Hard Filter Executor | 呼び出し | Retrieval 後の除外 | パイプライン中断、`GRS-REC-010` | |
| `MOD-RECO-014` Feature Matcher | 呼び出し | feature 一致度計算 | パイプライン中断、`GRS-REC-011` | |
| `MOD-RECO-015` Meaning Match Aggregator | 呼び出し | social_match / symbolic_match 集約 | パイプライン中断、`GRS-REC-011` | |
| `MOD-RECO-016` Context Scorer | 呼び出し | context_score 算出 | パイプライン中断、`GRS-REC-011` | |
| `MOD-RECO-017` Popularity Scorer | 呼び出し | popularity_score 算出 | パイプライン中断、`GRS-REC-012` | Ranking 前段 |
| `MOD-RECO-018` Risk Scorer | 呼び出し | risk_penalty 算出 | パイプライン中断、`GRS-REC-012` | Ranking 前段 |
| `MOD-RECO-019` Final Score Calculator | 呼び出し | final_score 算出 | パイプライン中断、`GRS-REC-012` | **スコア計算**責務。順位決定は含まない |
| `MOD-RECO-020` Final Ranker | 呼び出し | 表示順位 rank 決定 | パイプライン中断、`GRS-REC-012` | **順位決定**責務。スコア計算は含まない |
| `MOD-RECO-021` Recommendation Result Builder | 呼び出し | recommendation_result 生成 | パイプライン中断、`GRS-REC-012` | |
| `MOD-RECO-022` Result Snapshot Builder | 呼び出し | 表示時点 Snapshot 生成 | パイプライン中断、`GRS-REC-012` | |
| `MOD-RECO-023` Reason Generator | 呼び出し | 推薦理由生成 | 回復不能時は §10.3 に従い汎用 Reason 注入で継続 | `021`/`022` 成功後は Run 失敗にしない |
| `MOD-RECO-024` Reco Error Handler | 呼び出し | 例外の標準化・ログ接続 | エラー応答生成の前提 | 各フェーズ失敗時 |
| `MOD-RECO-025` Metric Logger | 呼び出し（任意） | 件数・処理時間・分布メトリクス記録 | 記録失敗は推薦結果に影響させない | MVP対象 `△` |
| `MOD-RECO-028` Phase Log Writer | 呼び出し | phase_log 永続化 | 記録失敗は推薦結果に影響させない（warn ログ） | 各フェーズ境界 |
| `MOD-RECO-029` Error Log Writer | 間接呼び出し | error_log 永続化 | `MOD-RECO-024` 経由 | 失敗時 |
| `MOD-RECO-026` Item Semantic Generator | 直接呼び出しなし | BT 事前生成データの間接利用 | OL では対象外 | 処理種別 `BT` |
| `MOD-RECO-027` Item Feature Generator | 直接呼び出しなし | BT 事前生成データの間接利用 | OL では対象外 | 処理種別 `BT` |

### 7.2 参照データ

| データ | 参照元 | 用途 | version / config | 備考 |
| ------ | ------ | ---- | ---------------- | ---- |
| `semantic_config_version` | DB（`MOD-RECO-003` 経由） | Semantic / Feature ルール | `MOD-RECO-003` が解決 | Orchestrator は参照のみ |
| `model_version` | DB（`MOD-RECO-003` 経由） | Embedding / LLM / Reason モデル | 同上 | |
| `ranking_config` | DB（`MOD-RECO-003` 経由） | Ranking パラメータ | 同上 | |
| `item_feature` / `item_embedding` | DB（事前 BT 生成） | Retrieval / Matching | `MOD-RECO-026` / `027` 成果物 | OL では読み取りのみ |

---

## 8. 処理仕様

### 8.1 処理フロー

```mermaid
flowchart TD
    START([API-INT-002 から Recommendation Request 受付]) --> INIT[実行コンテキスト初期化]
    INIT --> P0[Phase: request_received 記録依頼]
    P0 --> R003[MOD-RECO-003 Config 解決]
    R003 --> R002[MOD-RECO-002 Run INSERT]
    R002 --> UM[User Meaning フェーズ<br/>004→005→006→007→008→009→010]
    UM --> RT[Retrieval フェーズ<br/>012→013]
    RT --> MT[Matching フェーズ<br/>014→015→016]
    MT --> RK[Ranking フェーズ<br/>017→018→019→020]
    RK --> OUT[出力フェーズ<br/>021→022→023]
    OUT -->|021/022 失敗| ERR[MOD-RECO-024 Error Handler]
    OUT -->|023 回復不能| FB[汎用 Reason 注入<br/>isFallback=true]
    FB --> MET[Metric 記録依頼（任意）]
    OUT -->|023 成功| MET
    MET --> SUCCESS([Recommendation Result 返却 HTTP 200])

    R003 -->|失敗| ERR
    R002 -->|失敗| ERR
    UM -->|失敗| ERR
    RT -->|失敗| ERR
    MT -->|失敗| ERR
    RK -->|失敗| ERR
    ERR --> ELOG[MOD-RECO-029 Error Log 依頼]
    ELOG --> FAIL([標準化エラー返却])

    INIT -.-> PLW[MOD-RECO-028 Phase Log Writer]
    UM -.-> PLW
    RT -.-> PLW
    MT -.-> PLW
    RK -.-> PLW
    OUT -.-> PLW
```

### 8.2 処理ステップ

Recoモジュール一覧 §5.2 のモジュール整理に従い、Orchestrator は各ステップの **呼び出し順序・入力受け渡し・失敗時中断** を担当する。`MOD-RECO-002` / `003` の **物理呼び出し順** は §8.2.1（`003` → `002` INSERT）を正とする。

#### 8.2.1 `MOD-RECO-003` / `002` の物理呼び出し順

`recommendation_run` INSERT には version 3 列が必須のため、Orchestrator は **Config 解決（`003`）の後**に Run INSERT（`002`）を呼ぶ。詳細は `MOD-RECO-002` モジュール仕様書 §8.2.1 を正とする。

| No | 処理 | 入力 | 出力 | 補足 |
| --: | ---- | ---- | ---- | ---- |
| 1 | 実行コンテキスト初期化 | `recommendation_request`, `trace_id` | `execution_context` | mode 判定を含む |
| 2 | Phase Log（request_received） | `execution_context` | phase 記録依頼 | `MOD-RECO-028` |
| 3 | Config / Version 解決 | request context, mode | `config_versions` 群 | `MOD-RECO-003`。**物理呼び出しは `002` INSERT より前** |
| 4 | Recommendation Run 記録（INSERT accepted） | `execution_context`（version 解決済み） | `recommendation_run` | `MOD-RECO-002`。version 3 列を渡して INSERT |
| 5 | Semantic 抽出 | request text / relationship / occasion | semantic_extraction_result | `MOD-RECO-004` |
| 6 | 外部条件 Feature 推定 | relationship / occasion | external_feature_estimate | `MOD-RECO-005` |
| 7 | 内部条件 Feature 推定 | preferred / non_preferred / free text | internal_feature_estimate | `MOD-RECO-006` |
| 8 | User Feature 生成 | 外部・内部 Feature 推定結果 | user_feature | `MOD-RECO-007` |
| 9 | User Meaning 射影 | user_feature | user_social / user_symbolic / λ_ctx | `MOD-RECO-008` |
| 10 | User Context 生成 | semantic / user_feature | user_context | `MOD-RECO-009` |
| 11 | Query Embedding 生成 | user_context | query_embedding | `MOD-RECO-010` |
| 12 | 候補商品抽出 | execution_context | pre_filtered_item_pool / retrieval_candidate | `MOD-RECO-012`（内部: `pre_hard_filter` → `retrieval`） |
| 13 | Post Hard Filter | retrieval_candidate / semantic NG | validated_candidate | `MOD-RECO-013` |
| 14 | feature 一致度計算 | user_feature / item_feature | feature_match | `MOD-RECO-014` |
| 15 | 意味マッチ集約 | feature_match | social_match / symbolic_match | `MOD-RECO-015` |
| 16 | 文脈スコア算出 | matches / λ_ctx | context_score | `MOD-RECO-016` |
| 17 | 人気補正算出 | popularity signals | popularity_score | `MOD-RECO-017` |
| 18 | リスク補正算出 | risk signals / context | risk_penalty | `MOD-RECO-018` |
| 19 | 最終スコア算出 | context / popularity / risk | final_score | `MOD-RECO-019` |
| 20 | 最終順位生成 | final_score / diversity | ranked_items | `MOD-RECO-020` |
| 21 | Recommendation Result 生成 | ranked_items / score_breakdown | recommendation_result | `MOD-RECO-021` |
| 22 | Result Snapshot 生成 | ranked_items / item values | result item snapshot | `MOD-RECO-022` |
| 23 | Reason 生成 | snapshot / score_breakdown / context | recommendation_reason | `MOD-RECO-023`。失敗時は §10.3 |
| 24 | 正常終了・Result 返却 | 上記成果物 | `recommendation_result` | HTTP 200。Reason fallback 含む |

**処理順序の正本**: Recoモジュール一覧 §5.2 の **論理順序**（モジュール ID 順）を正とする。`MOD-RECO-002` / `003` については、`recommendation_run` INSERT に version 3 列必須のため **物理呼び出しは `003` 解決 → `002` INSERT** とする（§8.2.1、`MOD-RECO-003` モジュール仕様書 §8.3.7）。処理構成定義書 §5.4 および処理フロー概要図は抽象フローとして参照する。

**0件結果**: 候補 0 件は各下位モジュールの責務で検知する。最終的に表示対象 0 件の場合、HTTP 200 と `GRS-REC-001`（推薦候補0件）を返す方針はエラーコード定義書に従い、`MOD-RECO-024` と呼び出し元（api）で最終化する。

### 8.3 アルゴリズム / 計算仕様

本モジュールはスコア計算・意味推定・候補抽出などの **アルゴリズムを実装しない**。処理順序の制御、実行コンテキストの受け渡し、フェーズ境界の管理のみを担当する。

| 項目 | 内容 |
| ---- | ---- |
| パイプライン制御 | §8.2.1 の物理呼び出し順（`003`→`002` INSERT 後、`004`〜`023`）で同期的に各モジュールを呼び出す（MVP） |
| 実行モード分岐 | `ui` / `evaluation` / `batch` に応じて `MOD-RECO-003` へ mode を渡し、利用 config を切り替える |
| Ranking 責務分離 | `MOD-RECO-019`（final_score）→ `MOD-RECO-020`（rank）の順で呼び出す。機能×モジュール対応表と整合 |
| Reason fallback | `MOD-RECO-023` 回復不能時、Reason生成定義書 §17.2 汎用 Reason を注入し `isFallback: true` とする（§10.3） |

### 8.4 下位モジュール配線方針（Wiring・Human 決定）

Orchestrator から下位 `MOD-RECO-*`（002〜023）を呼び出す際、**モジュール本体実装**と **`build_default_stub_ports` への本実装配線（Wiring）** は分離する。Wiring とは `StubXxx` クラスの削除ではなく、MVP デフォルト composition で **本実装 Port を参照する**ことである。`StubXxx` は失敗注入・Orchestrator 単体テスト用に **残す**。

#### 8.4.1 3 段階（ハイブリッド）

| 段階 | タイミング | 成果物 | 備考 |
| ---- | ---------- | ------ | ---- |
| 1. モジュール実装 Task | 各 `MOD-RECO-*` Epic の implementation Task | モジュール本体、Port 適合、**Orchestrator 統合テスト（明示 DI）** | 原則 **`stubs.py` は変更しない** |
| 2. フェーズ Wiring Task | Epic 内の integration milestone | `build_default_stub_ports` の該当 Port を本実装へ差し替え | **フェーズ単位**（下表）。並列 Task 競合を避ける |
| 3. Composition 完成 Task | `MOD-RECO-001` Epic 締め | 本番 DI（DB Repository 等）、E2E 強化 | API-INT-002 接続後 |

#### 8.4.2 フェーズ Wiring 単位（MVP）

| Wiring フェーズ | 対象モジュール | 状態 |
| --------------- | -------------- | ---- |
| 起動 | `003` Config Version Resolver、`002` Run Recorder | **配線済み**（`build_default_config_resolver` / `build_scaffold_run_recorder`） |
| User Meaning | `004`〜`010` | 未配線（スタブ） |
| Retrieval | `012`〜`013` | 未配線 |
| Matching | `014`〜`016` | 未配線 |
| Ranking | `017`〜`020` | 未配線 |
| 出力 | `021`〜`023` | 未配線 |

**例外（起動フェーズ）**: `002` / `003` はモジュール間 I/F（version 3 列、`003`→`002` 物理順）が強く、`002` 実装 Task（#783）および `003` 実装完了時点で **起動フェーズ Wiring を実施済み**とする。

#### 8.4.3 Task Definition との関係

- 各モジュール **implementation Task** の `out_of_scope` に「Orchestrator 本体のスタブ差し替え（**起動フェーズを除く**）」を記載する
- **integration Task 相当**: モジュール Task 必須成果物として `tests/unit/application/<module>/test_orchestrator_integration.py`（または同等）を 1 本以上置き、**明示 DI** で Orchestrator 連携を検証する
- **Wiring Task** は `MOD-RECO-001` Epic またはフェーズ代表 Epic 配下で Issue 化し、`recommendation-orchestrator/stubs.py` の `exclusive_files` として直列化する

#### 8.4.4 配置

| 責務 | 配置 |
| ---- | ---- |
| `StubXxx` 実装 | `application/recommendation-orchestrator/stubs.py` |
| MVP デフォルト composition | `build_default_stub_ports()`（同上） |
| 本番 composition（将来） | `apps/reco` の composition root（別 Task） |

---

## 9. データ項目マッピング

Orchestrator はドメイン変換の **ハブ** として、下位モジュール間の受け渡しを行う。主要マッピングは各 `MOD-RECO-*` モジュール仕様書で詳述し、本仕様書では起点・終点のみ示す。

| 入力項目 | 内部項目 | 出力項目 | 変換内容 | 備考 |
| -------- | -------- | -------- | -------- | ---- |
| `recommendation_request.*` | `execution_context.request` | - | コンテキストへ格納 | RecommendationRequest定義書 |
| - | `execution_context.run_id` | `recommendation_result.run_id` | Run 記録後に紐づけ | `MOD-RECO-002` |
| - | `execution_context.config_versions` | `recommendation_result.version_info` | Version 情報の引き継ぎ | `MOD-RECO-003` |
| - | `ranked_items` + reasons | `recommendation_result.items[]` | Result 構築 | `MOD-RECO-021`〜`023` |

---

## 10. 状態・例外

### 10.1 状態

Orchestrator が管理する推薦実行の論理状態（`recommendation_run.status` の詳細は状態遷移設計書・`MOD-RECO-002` に委譲）。

| 状態 | 意味 | 遷移条件 | 記録先 |
| ---- | ---- | -------- | ------ |
| `running` | パイプライン実行中 | Run 記録成功後、Result 返却前 | `recommendation_run` / Phase Log |
| `succeeded` | 正常終了 | Result 返却完了（Reason fallback 含む） | `recommendation_run` |
| `failed` | 異常終了 | `021`/`022` 以前の必須フェーズ失敗、または Result 返却不能 | `recommendation_run` / Error Log |
| `empty_result` | 0件結果（ビジネス上の空結果） | 候補 0 件だが処理は完了 | `recommendation_run`（`GRS-REC-001`） |

**リトライ**: MVP では Orchestrator 単体でのパイプライン自動リトライは行わない。呼び出し元（`apps/api`）または人間操作による再実行に委ねる。

### 10.2 例外

| 例外 | Error Code | 発生条件 | 呼び出し元への返却 | ログ |
| ---- | ---------- | -------- | ------------------ | ---- |
| 推薦候補0件 | `GRS-REC-001` | 最終表示対象 0 件 | HTTP 200（api 層で Public 形式へ変換） | Phase Log に候補数を記録 |
| 推薦実行失敗 | `GRS-REC-002` | Run 記録・パイプライン制御失敗 | 500 系 | Error Log + Phase Log（failed） |
| Config 解決失敗 | `GRS-REC-003` | `MOD-RECO-003` 失敗 | 500 系 | 同上 |
| Semantic 抽出失敗 | `GRS-REC-004` | `MOD-RECO-004` 失敗 | 500 系 | 同上 |
| User Feature 系失敗 | `GRS-REC-005` | `MOD-RECO-005`〜`009` 失敗 | 500 系 | 同上 |
| User Meaning 射影失敗 | `GRS-REC-006` | `MOD-RECO-008` 失敗 | 500 系 | 同上 |
| Query Embedding 失敗 | `GRS-REC-007` | `MOD-RECO-010` 失敗 | 500 系 | 同上 |
| Pre Hard Filter 失敗 | `GRS-REC-008` | `MOD-RECO-012`（`pre_hard_filter`）失敗 | 500 系 | 同上 |
| Retrieval 失敗 | `GRS-REC-009` | `MOD-RECO-012`（`retrieval`）失敗 | 500 系 | 同上 |
| Post Hard Filter 失敗 | `GRS-REC-010` | `MOD-RECO-013` 失敗 | 500 系 | 同上 |
| Matching 失敗 | `GRS-REC-011` | `MOD-RECO-014`〜`016` 失敗 | 500 系 | 同上 |
| Ranking / Result 構築失敗 | `GRS-REC-012` | `MOD-RECO-017`〜`022` 失敗 | 500 系 | 同上 |
| Reason フェーズ致命失敗 | `GRS-REC-013` | `021`/`022` 成功後も Result 返却不能 | 500 系 | Error Log（critical） |
| Reco タイムアウト | `GRS-REC-101` | 推薦全体 hard timeout 超過（§13） | 504 系 | Error Log |
| Run 状態不整合 | `GRS-REC-201` | 実行状態の競合 | 409 系 | Error Log |
| 想定外エラー | `GRS-REC-999` | 上記に分類できない例外 | 500 系 | Error Log（critical） |

Error Code の正本はエラーコード定義書。Orchestrator は `MOD-RECO-024` が返す標準化結果を呼び出し元へ伝播する。

### 10.3 Reason 失敗時の部分成功（確定方針）

`MOD-RECO-021` / `022` が成功し Result Item が生成できた場合、Reason 生成の成否にかかわらず **Recommendation Result を HTTP 200 で返却**する。

| 条件 | Orchestrator の扱い | API 表現（目標） | DB（目標） |
| ---- | ------------------- | ---------------- | ---------- |
| `MOD-RECO-023` 成功 | 通常 Reason を返却 | `reasonStatus: completed`, `isFallback: false` | `recommendation_reason` に INSERT |
| `MOD-RECO-023` 内部フォールバック（§17.3） | 成功扱い | `reasonStatus: completed`, `isFallback: true` | INSERT（fallback 由来を `reason_basis` に記録） |
| `MOD-RECO-023` 回復不能（Orchestrator 注入） | §17.2 汎用 Reason 文を注入 | `reasonStatus: completed`, `isFallback: true`, 非空 `reasonSummary` | INSERT（fallback 由来を記録） |
| 一部 Item のみ Reason 失敗 | 他 Item は通常、失敗 Item は上記注入 | Run `resultStatus: partial` 可 | Item 単位で fallback 行を INSERT |

**汎用 Reason 文（正本）** — Reason生成定義書 §17.2:

```text
今回の条件に対して、候補商品の中でも比較的バランスの良い商品です。
```

**`GRS-REC-013` の適用**: Item 単位の Reason 失敗（Result 返却継続）では使用しない。`021`/`022` 成功後に Result 自体を返却できない致命ケースに限定する。

**後続整合**: API-INT-002 / API-PUB-002 契約、recommendation_reason テーブル定義書、状態遷移設計書 §11.1 は本方針へ更新する（別 Task。§17 参照）。

---

## 11. DB / 永続化

Orchestrator 本体は DB へ **直接書き込まない**。永続化は下位モジュールに委譲する。

| テーブル | 操作 | 主な項目 | トランザクション | 備考 |
| -------- | ---- | -------- | ---------------- | ---- |
| `recommendation_run` | insert / update | run_id, status, request_id | `MOD-RECO-002` が管理 | Orchestrator は呼び出しのみ |
| `phase_log` | insert | phase_name, phase_status, duration_ms | `MOD-RECO-028` が管理 | フェーズ境界ごと |
| `error_log` | insert | error_code, phase_name, detail_json | `MOD-RECO-029` が管理 | 失敗時 |

---

## 12. ログ・メトリクス

### 12.0 ログ出力タイミング（Orchestrator 責務）

| 種別 | 内容 | 出力タイミング | 保存先 | 備考 |
| ---- | ---- | -------------- | ------ | ---- |
| Phase Log 依頼 | フェーズ開始（`started`） | 各 `MOD-RECO-003`〜`023` の直前 | `phase_log`（`MOD-RECO-028`） | `request_received` はパイプライン開始時 |
| Phase Log 依頼 | フェーズ成功（`succeeded`） | 各モジュール正常 return 直後 | 同上 | `duration_ms` を付与 |
| Phase Log 依頼 | フェーズ失敗（`failed`） | 例外検知・中断決定時 | 同上 | `error_code` を付与 |
| Error Log 依頼 | 例外詳細 | `MOD-RECO-024` 呼び出し時 | `error_log`（`MOD-RECO-029`） | secret はマスキング |
| 構造化ログ | パイプライン開始・終了 | Orchestrator entry / exit | アプリログ | trace_id 必須 |

Phase 名の一覧はログ・Observability設計書 §10.3（`request_received`, `config_resolved`, `semantic_extracted`, … `response_built`）に準拠する。

### 12.1 メトリクス

| Metric | 内容 | 集計単位 | 用途 |
| ------ | ---- | -------- | ---- |
| `recommendation_latency_ms` | 推薦全体の処理時間 | Run | SLO 監視・ボトルネック分析 |
| `phase_duration_ms` | フェーズ別処理時間 | Phase | フェーズ単位の遅延分析 |
| `pre_filter_candidate_count` | Pre Hard Filter 後候補数 | Run | 0件原因調査 |
| `retrieval_candidate_count` | Retrieval 候補数 | Run | 同上 |
| `post_filter_candidate_count` | Post Hard Filter 後候補数 | Run | 同上 |
| `final_result_count` | 最終推薦件数 | Run | 品質・空結果率 |
| `reason_fallback_count` | Reason 汎用文注入件数 | Run / Item | fallback 品質監視 |

メトリクスの永続化は `MOD-RECO-025` Metric Logger に委譲する（MVP対象 `△`）。Orchestrator は計測起点・終点と、下位モジュールからのカウント受け渡しを担う。

---

## 13. 性能・非機能

### 13.1 方針概要

| 観点 | 方針 |
| ---- | ---- |
| レイテンシ | soft / hard の二段制御。Orchestrator は `recommendation_latency_ms` を計測する |
| 計算量 | パイプラインは MVP では **直列実行** |
| タイムアウト | 全体 **hard 4,000ms** 超過で `GRS-REC-101`。フェーズ別は §13.2 |
| リトライ | Orchestrator 内の自動リトライは MVP では **行わない** |
| キャッシュ | Orchestrator 本体ではキャッシュを持たない |
| 並列実行 | MVP ではパイプライン内のモジュール並列実行は行わない |

### 13.2 タイムアウト（暫定値）

正本引用: 性能要件（バックエンド）§3.1・§5.1・§5.2。数値の実現可能性は **PoC（全体テスト計画書 TV-007）** で検証し、検証後に本節および性能要件を更新する。

| 種別 | 対象 | 暫定値 | 超過時の扱い |
| ---- | ---- | ------ | ------------ |
| soft（SLO 監視） | 推薦パイプライン全体 | **2,000ms**（p95 目標） | Metric / warn のみ。処理継続 |
| hard（中断） | 推薦パイプライン全体 | **4,000ms** | パイプライン中断 → `GRS-REC-101` |
| hard | Config 解決（`003`） | **300ms** | 中断 → `GRS-REC-003` |
| hard | User Meaning 一括（`004`〜`010`） | **1,000ms** | 中断 → 該当 `GRS-REC-004`〜`007` |
| hard | Retrieval 一括（`012`〜`013`） | **1,000ms** | 中断 → `GRS-REC-008`〜`010` |
| hard | Matching 一括（`014`〜`016`） | **500ms** | 中断 → `GRS-REC-011` |
| hard | Ranking 一括（`017`〜`020`） | **1,000ms** | 中断 → `GRS-REC-012` |
| hard | Output 一括（`021`〜`023`） | **500ms** | `021`/`022` 失敗 → `GRS-REC-012`；`023` 失敗 → §10.3 fallback |

**全体ウォッチドッグ**: フェーズ別上限の合計より **パイプライン全体 4,000ms** を優先する。api → reco 呼び出し timeout（性能要件 §5.1 内部 Reco API 4 秒）と整合させる。

**PoC 連携**: `[Epic]PoC:Reco性能フィジビリティ検証` の成果を `docs/90_PoC/性能フィジビリティ/` に記録し、検証後に本節を更新する。

---

## 14. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系（ui mode） | 全モジュール成功時に `Recommendation Result` が返ること | unit |
| 2 | 正常系（evaluation / batch mode） | mode に応じた config 解決・パイプライン起動が行われること | unit |
| 3 | 処理順序 | `MOD-RECO-003`→`002`（INSERT）→`004`→…→`023` の物理呼び出し順が §8.2.1 と一致すること | unit |
| 4 | Ranking 責務分離 | `MOD-RECO-019` の後に `MOD-RECO-020` が呼ばれること | unit |
| 5 | 境界値（0件） | 候補 0 件時に `GRS-REC-001` 相当の扱いになること | unit |
| 6 | 例外系（下位失敗） | 各フェーズ失敗でパイプラインが中断し、対応する `GRS-REC-*` が伝播すること | unit |
| 7 | 依存モジュール失敗 | `MOD-RECO-003` 失敗時に後続 User Meaning が呼ばれないこと | unit |
| 8 | Phase Log 契機 | 主要フェーズの開始・終了で `MOD-RECO-028` が呼ばれること | unit / integration |
| 9 | Error Log 接続 | 失敗時に `MOD-RECO-024`→`MOD-RECO-029` が呼ばれること | unit / integration |
| 10 | DB / ログ | Run / Phase / Error が下位モジュール経由で記録されること（Orchestrator 直書き込みなし） | integration |
| 11 | タイムアウト | 全体 hard 4,000ms 超過時に `GRS-REC-101` になること | integration |
| 12 | trace 伝播 | `trace_id` が Phase Log / 構造化ログに引き継がれること | unit |
| 13 | Reason fallback | `023` 回復不能時に §17.2 汎用 Reason が注入され HTTP 200 で Result が返ること | unit / integration |
| 14 | Reason 部分失敗 | 複数 Item で一部のみ fallback のとき Run が `partial` になり得ること | integration |

---

## 15. 変更管理

### 15.1 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-25 | 初版作成 | Issue #758 |
| 2026-06-26 | Human Review 反映（責務・Reason fallback・タイムアウト暫定値・未決事項解消） | Issue #758 |
| 2026-06-25 | `003` 先行解決 → `002` INSERT の物理呼び出し順を §8.1 / §8.2 に反映 | Issue #779 / `MOD-RECO-003` §8.3.7 |
| 2026-06-27 | MOD-RECO-002 整合（`003`→`002` INSERT の物理呼び出し順・§8.2.1 追加） | Issue #777 |
| 2026-06-26 | §8.4 下位モジュール配線方針（3 段階ハイブリッド）を Human 決定として反映 | 配線方針採用 |
| 2026-06-30 | `MOD-RECO-011` 廃止に伴い `010 → 012` 1 呼び出し（内部 `pre_hard_filter` → `retrieval`）へ更新。`GRS-REC-008` / `009` 発生元を `MOD-RECO-012` に整合 | Issue #867 / PR #868 |

---

## 16. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| - | なし | - | - | - | §16.1 の論点は確定済み |

### 16.1 確定済み論点（Issue #758 Human Review）

| No | 論点 | 確定内容 |
| --: | ---- | -------- |
| 1 | Orchestrator 責務範囲 | **契機管理＋委譲**。Phase Log / Error Log 物理書き込みは `028`/`029`、`024` に委譲 |
| 2 | 物理配置パス | `apps/reco/src/reco/application/recommendation-orchestrator/**`（Epic `epic_scope` 準拠） |
| 3 | `002`/`003` 記述粒度 | 依存関係表・処理ステップの **概要のみ**（各モジュール仕様書 Task に委譲） |
| 4 | Reason 失敗時の部分成功 | `021`/`022` 成功後は **Result 返却優先**。回復不能時は §17.2 汎用 Reason 注入 + `isFallback: true` |
| 5 | 処理順序の正本 | **Recoモジュール一覧 §5.2**（モジュール ID 順）。**物理呼び出し順**は `003`→`002` INSERT（§8.2.1、`MOD-RECO-002` §8.2.1 と整合） |
| 6 | タイムアウト | soft **2,000ms** / hard **4,000ms**（性能要件 §5 暫定引用）。**PoC 検証後に更新** |
| 7 | `002`/`003` 物理呼び出し順 | **`MOD-RECO-003` 解決 → `MOD-RECO-002` INSERT**。allocate / commit 分割は不採用 | Human | §8.2.1、`MOD-RECO-003` §8.3.7・§16.1 No.1 |
| 8 | 下位モジュール配線（Wiring） | **3 段階ハイブリッド**（§8.4）。実装 Task + フェーズ Wiring + Composition 完成 | Human | §8.4 |

---

## 17. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| Recoモジュール一覧 | `docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md` | モジュール定義・処理順序 |
| モジュール一覧 | `docs/05_アプリケーション設計/アプリ/モジュール一覧.md` | 全体配置 |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | API-INT-002 連携 |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | OL / BT 分離 |
| 処理フロー概要図 | `docs/05_アプリケーション設計/アプリ/処理フロー概要図.md` | 全体フロー |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | `GRS-REC-*` |
| ログ・Observability設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | Phase Log / Metric |
| RecommendationRequest定義書 | `docs/04_ドメインモデル設計/RecommendationRequest定義書.md` | 入力構造 |
| RecommendationResult定義書 | `docs/04_ドメインモデル設計/RecommendationResult定義書.md` | 出力構造 |
| Retrieval / Matching / Ranking / Reason生成定義書 | `docs/04_ドメインモデル設計/` 配下 | フェーズ前提 |
| API-INT-002 契約仕様書 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` | 呼び出し I/F（エンドポイント層は out of scope） |
| MOD-RECO-003 仕様書 | `docs/06_実装設計/reco/MOD-RECO-003_Config Version Resolverモジュール仕様書.md` | Config 解決・`002`/`003` 物理呼び出し順（§8.3.7） |
| module-spec テンプレート | `prompts/templates/docs/module-spec.md` | 章構成 |
| Epic Definition | `prompts/definitions/epics/mod-reco-001-recommendation-orchestrator/epic.yaml` | allowed_paths |
| 性能要件（バックエンド） | `docs/03_ドメイン要件定義/非機能要件定義書/性能要件（バックエンド）.md` | タイムアウト暫定値の引用元 |
| 全体テスト計画書 | `docs/05_アプリケーション設計/テスト/全体テスト計画書.md` | TV-007 Reco 性能フィジビリティ |
| PoC 成果物 | `docs/90_PoC/性能フィジビリティ/` | タイムアウト検証結果（別 Epic） |

### 17.1 後続整合 Task（本仕様書の確定方針を反映する別 Task）

| 対象 | 整合内容 |
| ---- | -------- |
| API-INT-002 / API-PUB-002 契約仕様書 | Reason 失敗時も非空 `reasonSummary` + `isFallback: true`（§10.3） |
| recommendation_reason テーブル定義書 | fallback 時も INSERT、`reason_basis` に fallback 由来を記録 |
| 状態遷移設計書 §11.1 | Reason 失敗時の「Result 全体失敗」記述を部分成功方針へ更新 |
| 性能要件（バックエンド）§5 | PoC 検証結果に基づく hard / soft 値の見直し |

---

## 18. レビュー観点

- Recoモジュール一覧のモジュール名・物理名・分類・処理種別・MVP対象と一致している
- モジュール一覧の `MOD-RECO-001` 行と整合している
- Orchestrator の責務が実行制御に限定され、他モジュール本体の仕様が混入していない
- `apps/reco/src/reco/api/**`（API-INT エンドポイント層）の変更を本仕様書の実装範囲に含めていない
- 依存モジュール（`MOD-RECO-002`〜`029`）の呼び出し方向・用途・失敗時の扱いが明確である
- `MOD-RECO-019`（Final Score Calculator）と `MOD-RECO-020`（Final Ranker）の責務分離が明確である
- Phase Log / Error Log の出力タイミングが整理されている
- Reason fallback（§10.3）とタイムアウト暫定値（§13.2）が明記されている
- secret や `.env` 実値が含まれていない

---

## 19. 備考

- 本仕様書は `MOD-RECO-001` の **実行制御** 責務に限定する。各下位 `MOD-RECO-*` の詳細は別 Task のモジュール仕様書で定義する
- `API-INT-002` エンドポイント層は `[Epic]API-INT-002` 配下で設計・実装する
- Batch モジュール `MOD-RECO-026` / `027` はオンライン推薦パイプラインからは直接呼び出さない（事前生成データを参照）
- 配置パスは `apps/reco/src/reco/application/recommendation-orchestrator/**` に確定（旧想定 `apps/reco/src/modules/**` は採用しない）
- タイムアウト hard 値は PoC（`docs/90_PoC/性能フィジビリティ/`）完了後に §13.2 を更新する
