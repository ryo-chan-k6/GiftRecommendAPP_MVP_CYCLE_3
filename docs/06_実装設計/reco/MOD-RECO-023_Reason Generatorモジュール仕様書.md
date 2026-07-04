# Reason Generator モジュール仕様書

## 1. ドキュメント情報

| 項目           | 内容                                       |
| -------------- | ------------------------------------------ |
| ドキュメントID | `MOD-RECO-023`                             |
| ドキュメント名 | Reason Generator モジュール仕様書          |
| 対象システム   | Gift Recommendation Service（`apps/reco`） |
| MVP対象        | `○`                                        |
| 作成日         | 2026-07-04                                 |
| 更新日         | 2026-07-05                                 |

---

## 2. 概要

Reason Generator（Reason生成）は、Reco オンライン推薦パイプラインの **出力フェーズ第 3 ステップ**において、`MOD-RECO-001` Recommendation Orchestrator から `execution_context` を **1 回**受け取り、`MOD-RECO-022` Result Snapshot Builder が永続化済みの **`recommendation_result.items[]`**（Snapshot 充填済み）を主入力とし、Matching / Ranking / Semantic / Item 情報を根拠として **商品ごとの推薦理由文・バッジ・根拠**を生成し、**`recommendation_reason` テーブルへ INSERT** して、`execution_context` へ返却するモジュールである。`MOD-RECO-022` 完了後、**Orchestrator が Result 返却前に**呼び出される。

本モジュールは **Reason 根拠選定・テンプレート解決・文面生成・妥当性検証・Reason 永続化**に責務を限定し、Ranking / 順位決定（`MOD-RECO-016`〜`020`）、Result ヘッダ / Snapshot 構築（`MOD-RECO-021` / `022`）、Run 終端状態更新（`MOD-RECO-002`）、Public / Internal API レスポンス変換（`apps/api` / `API-INT-002` エンドポイント層）は行わない。Reason 生成ロジックの正本は **Reason生成定義書**、DB 物理列の正本は **`recommendation_reason_テーブル定義書`** / **`reason_template_テーブル定義書`** を正とする。

**責務境界（022 / 023 分割）**: Recoモジュール一覧 §6.22 は「推薦理由を生成する」と記載する。**Result Item の Snapshot 充填・明細 INSERT** は `MOD-RECO-022` が完了済みであることを前提とし、本モジュールは **Reason 文面生成と `recommendation_reason` INSERT** のみを担当する。

**部分成功方針**: `MOD-RECO-021` / `022` が成功した Run では、Reason 生成の成否にかかわらず **Recommendation Result を HTTP 200 で返却**する（`MOD-RECO-001` §10.3）。本モジュールは Item 単位の内部フォールバックを優先し、回復不能時は Orchestrator へ制御を返して汎用 Reason 注入を委ねる。

---

## 3. 目的

- `apps/reco` における Reason Generator 実装・単体テストの前提を定義する
- Orchestrator との I/F（`execution_context` 入出力）、**Reason 失敗時の Run 継続**（部分成功）を後続実装可能な粒度で整理する
- 根拠選定・テンプレート解決・文面生成・`reason_basis_json` 構築・DB INSERT 手順を明確化する
- Recoモジュール一覧・Reason生成定義書・`MOD-RECO-001` / `021` / `022` 仕様書との整合を担保する

---

## 4. モジュール基本情報

| 項目 | 内容 |
| ---- | ---- |
| モジュールID | `MOD-RECO-023` |
| モジュール名 | Reason生成 |
| 物理名 | `Reason Generator` |
| 分類 | 出力処理 |
| 処理種別 | `OL` |
| 配置予定 | `apps/reco/src/reco/application/reason-generator/**` |
| 所属Epic | `MOD-RECO-023`（Epic Issue #992） |
| MVP対象 | `○` |
| 主な呼び出し元 | `MOD-RECO-001` Recommendation Orchestrator |
| 主な呼び出し先 | `ReasonTemplateRepository` / `ItemSemanticReadRepository` / `RecommendationReasonRepository`（`infrastructure/db/`）、`ExternalAiApiClient`（LLM 整形・config 有効時のみ） |

`MOD-API-*` / `MOD-RECO-*` / `MOD-BATCH-*` 配下の Task では、該当モジュール ID の責務範囲に変更を限定する。`MOD-RECO-*` では `apps/reco/src/reco/api/**` の API-INT エンドポイント層を対象に含めない。

---

## 5. 責務

### 5.1 主責務

- `MOD-RECO-022` 完了後、Orchestrator から **1 回**呼び出され、`execution_context.recommendation_result.items[]` を **1 Item あたり 1 Reason** として処理する
- 各 Item について、Ranking / Matching / Feature / **`item_semantic`（Batch 正本）** / Item Snapshot 情報から **Reason 根拠（`reason_basis`）を選定**する（Reason生成定義書 §7〜§11、§8.3.8）
- `reason_template` を解決し（`reason_template_テーブル定義書` §7.1）、**テンプレートベースで文面を生成**する（MVP 基本方式）
- 必要に応じ **LLM 整形**を行う（**`RECO_REASON_LLM_REFINEMENT_ENABLED=true` 時のみ**。根拠外事実の追加禁止。Reason生成定義書 §12）
- **禁止表現チェック**・妥当性検証を行い、`reason_summary` / `reason_detail` / `reason_points` / `reason_badges` / `caution_note` を組み立てる
- **`reason_basis_json`**（`template_name` / `template_version` / `used_features` / `used_scores` / `generation_method` 等）を構築する（`recommendation_reason_テーブル定義書` §5.4）
- 成功時または **内部フォールバック時**に **`recommendation_reason` 行を INSERT** し、採番した `recommendation_reason_id` をドメインへ書き戻す
- 充填済み **`execution_context.recommendation_result`**（Reason 付き）を返却し、Orchestrator へ引き渡す
- 成功時に **Reason 生成向け Metric**（§12.1）を Orchestrator / `MOD-RECO-025` 経由で依頼する
- 入力欠損・LLM 失敗等は **Item 単位で内部フォールバック**し、Run 全体を `GRS-REC-012` で中断しない（`MOD-RECO-001` §10.3）

### 5.2 対象外責務

- `API-INT-002` エンドポイント層（HTTP 受付、reco 側防御的 Validation、OpenAPI スキーマ整合）
- `MOD-RECO-001` Orchestrator の実行順序制御・汎用 Reason 最終注入（§10.3）・Phase Log 契機の物理実装
- **Ranking 計算・順位変更・`final_score` 変更**（Reason は説明層。Ranking定義書）
- **Result ヘッダ / Snapshot 構築・`recommendation_result_item` INSERT**（`MOD-RECO-021` / `022` 責務）
- **`reason_template` マスタの CRUD**（database seed / 運用更新。本モジュールは **読取・解決のみ**）
- **`config_versions.reason_template_catalog_ok` の Run レベル検証**（`MOD-RECO-003` 責務。本モジュール到達時は `true` 前提）
- **`recommendation_run.run_status` の終端更新**（`MOD-RECO-002` 責務）
- Public API（`API-PUB-002`）向け `reasonStatus` / `isFallback` の **HTTP 表現**（`apps/api` 側責務）
- Phase Log `reason_generated` の **物理記録**（Orchestrator が記録依頼。本モジュールは直接記録しない）
- OpenAPI / DB schema / DDL の変更

---

## 6. 入出力

### 6.1 入力（Orchestrator → 本モジュール）

| 入力 | 型 / 構造 | 必須 | 生成元 | 用途 | 備考 |
| ---- | --------- | ---- | ------ | ---- | ---- |
| `execution_context` | パイプライン実行コンテキスト | `true` | `MOD-RECO-001` | 処理起点 | |
| `execution_context.recommendation_result` | Recommendation Result ドメイン | `true`¹ | `MOD-RECO-021` / `022` | Reason 生成の主入力 | §6.2.1 |
| `execution_context.recommendation_result.items[]` | Result Item 明細（Snapshot 済み） | `true`¹ | `MOD-RECO-022` | 1 件あたり 1 Reason | ¹は下記 |
| `execution_context.feature_match_result` | 候補別 Feature Match | `true`¹ | `MOD-RECO-014` | `strong_match` / `weak_match` 導出 | §6.2.3 |
| `execution_context.meaning_match_result` | 候補別意味マッチ | `false`¹ | `MOD-RECO-015` | 内訳・Badge 補助 | 欠損時は Feature のみで生成 |
| `execution_context.recommendation_request` | 推薦入力条件 | `true` | `API-INT-002` 経由 | `relationship` / `occasion` ラベル | §6.2.4 |
| `execution_context.config_versions` | Config 群 | `true` | `MOD-RECO-003` | `reason_template_catalog_ok` 前提 | 到達時 `true` |
| `execution_context.run_id` | `uuid` | `true` | `MOD-RECO-002` | ログ・再現性 | |
| `execution_context.trace_id` | `string` | `true` | Request 由来 | 構造化ログ | |

¹ **`recommendation_result.result_item_count` ≥ 1** のとき必須。`result_item_count = 0` のとき Orchestrator は **本モジュールを呼ばない**（`MOD-RECO-021` §8.3.6）。

**前提**: `MOD-RECO-022` が完了済み（`snapshot_builder_items_persisted=true`）。各 `items[]` に `recommendation_result_item_id`・Snapshot 列・スコア列が設定済みであること。

**防御的入力**: `result_item_count ≥ 1` なのに `items[]` が空、または件数不一致の場合は **回復不能**として Orchestrator へ返却（`MOD-RECO-001` §10.3 汎用 Reason 注入または `GRS-REC-013` 判定は Orchestrator 責務）。

#### 6.1.1 Item 単位の参照入力（Run 内メモリ）

各 `items[].item_id` をキーに、以下を JOIN 参照する（本モジュールは **新規スコア算出を行わない**）。

| ソース | 使用フィールド | 用途 |
| ------ | -------------- | ---- |
| `items[]` | `rank` / `final_score` / `context_score` / `score_breakdown_json` / `snapshot` | 主入力・表示文脈 |
| `feature_match_result.entries[]` | `match`（8 軸） | `strong_match_features` / `weak_match_features` |
| `meaning_match_result.entries[]` | `social_match` / `symbolic_match` | 文脈理由・`used_scores` |
| `item_semantic` | `semantic_json.concepts[]`（`concept_code` / `evidence_texts`） | **`used_semantic_evidence`（商品側根拠）** | Batch 正本（§8.3.8） |
| `semantic_extraction_result`（任意） | `concepts[].evidence_text` | **`used_semantic_evidence`（ユーザー入力側根拠）** | `MOD-RECO-004` 成果物 |
| `items[].snapshot` | `item_name_snapshot` 等 | 表示文脈・テンプレート補助 | **`evidence_text` の正本ではない** |

### 6.2 出力（本モジュール → Orchestrator）

| 出力 | 型 / 構造 | 利用先 | 用途 | 備考 |
| ---- | --------- | ------ | ---- | ---- |
| `execution_context.recommendation_result` | Recommendation Result ドメイン | Orchestrator / `apps/api` | Reason 付き Result | §6.2.2 |
| `reason_generator_item_count` | `number` | Orchestrator / `MOD-RECO-025` | 処理対象 Item 件数 | `result_item_count` と一致 |
| `reason_generator_success_count` | `number` | 観測 | 通常生成成功件数 | |
| `reason_generator_fallback_count` | `number` | 観測 | 内部フォールバック件数 | Orchestrator `reason_fallback_count` と合算可 |
| `reason_generator_persisted` | `boolean` | Orchestrator | Reason INSERT 完了フラグ | 全 Item で行あり（fallback 含む） |
| `reco_error` | 標準化 reco エラー | Orchestrator | **回復不能時のみ** | Run 継続可否は §10.2 |

#### 6.2.1 `recommendation_result.items[]`（入力・更新）

`MOD-RECO-022` モジュール仕様書 §6.2.1 / §6.2.2 を正とする。本モジュールは以下を **読み取り**、Reason 生成後 **同一オブジェクトへ書き戻す**（スコア・順位・Snapshot 列は変更しない）。

| フィールド | 必須 | 本モジュールでの扱い |
| ---------- | ---- | -------------------- |
| `recommendation_result_item_id` | `true` | `recommendation_reason` FK。変更しない |
| `item_id` | `true` | 根拠 JOIN キー |
| `rank` / `final_score` / `context_score` | `true` | `used_scores`・文面根拠。変更しない |
| `score_breakdown_json` | `false` | 内訳説明。変更しない |
| `snapshot` | `true` | Item 表示情報・evidence 接続 |
| `reason` | `false`（入力時） | **本モジュールが充填**（ドメイン上の Reason サマリ。詳細は DB 正本） |

#### 6.2.2 Reason 出力（ドメイン / DB）

`recommendation_reason_テーブル定義書` §6 を正とする。1 Item あたり **最大 1 行**（`UNIQUE(recommendation_result_item_id)`）。

| フィールド（ドメイン / DB） | 必須 | 内容 |
| ----------------------------- | ---- | ---- |
| `recommendation_reason_id` | `true` | 新規 UUID（INSERT 後確定） |
| `recommendation_result_item_id` | `true` | 親 Result Item FK |
| `template_id` | `true` | 使用 `reason_template.reason_template_id` |
| `reason_summary` | `true` | 短い推薦理由（空文字不可） |
| `reason_detail` | `false` | 詳細推薦理由 |
| `reason_points_json` | `false` | 箇条書き（2〜3 個推奨） |
| `reason_badges_json` | `false` | 表示ラベル配列 |
| `caution_note` | `false` | 注意・補足文（条件付き） |
| `reason_basis_json` | `true` | 根拠 JSON（§5.4 必須項目） |
| `created_at` | `true` | 生成日時（DB default 可） |

**`generation_method`**: MVP では物理列を持たず、`reason_basis_json.generation_method` に記録する（`recommendation_reason_テーブル定義書` §17.1 No.2）。

| 値 | 意味 |
| -- | ---- |
| `template` | テンプレートのみ |
| `llm_refined` | LLM 整形のみ |
| `hybrid` | テンプレート + LLM |
| `reason_module_internal_fallback` | 本モジュール内部フォールバック（§17.3 / §10.2） |
| `orchestrator_generic_fallback` | Orchestrator 汎用文注入（本モジュール外。記録用） |

#### 6.2.3 `strong_match_features` / `weak_match_features`（内部導出）

Reason生成定義書 §8.3 / §11.1 を正とする。本モジュールが `feature_match_result` から導出する。

| 区分 | 条件 | 用途 |
| ---- | ---- | ---- |
| `strong_match_features` | `feature_match[f] >= 0.80` | 主理由・Badge・`reason_points` |
| `weak_match_features` | `0.60 <= feature_match[f] < 0.80` かつ重要 Feature | `caution_note` 判断 |

#### 6.2.4 `relationship` / `occasion`（入力・参照）

`recommendation_request` から **コード**を読み取り、マスタまたは内蔵ラベルマップで **表示ラベル**へ変換してテンプレートに埋め込む（Reason生成定義書 §9）。欠損時は Reason生成定義書 §17.1 の汎用表現を用いる。

---

## 7. 依存関係

### 7.1 依存モジュール

| 依存先 | 方向 | 用途 | 失敗時の扱い | 備考 |
| ------ | ---- | ---- | ------------ | ---- |
| `MOD-RECO-001` | 呼び出し元 | `execution_context` 受領 | — | Orchestrator |
| `MOD-RECO-022` | 上流 | Snapshot 済み Result Item | 未到達（`022` 失敗時） | Item INSERT 済み前提 |
| `MOD-RECO-014` | 上流（参照） | `feature_match_result` | 欠損時は汎用 Reason へフォールバック | スコア変更なし |
| `MOD-RECO-015` | 上流（参照） | `meaning_match_result` | 同上 | 任意 |
| `MOD-RECO-003` | 上流（間接） | `reason_template_catalog_ok` | `false` 時は本モジュール未到達 | Run レベル検証 |
| `MOD-RECO-024` | 間接 | エラー標準化 | Orchestrator 経由 | 回復不能時 |
| `MOD-RECO-025` | 間接（任意） | Metric 記録 | 記録失敗は Result に影響させない | |
| `MOD-RECO-029` | 間接 | Error Log | 回復不能時 | |

**下流利用**: `apps/api` が `recommendation_reason` を **LEFT JOIN** し Public / Internal レスポンスを組み立てる（本モジュール外）。

### 7.2 参照データ

| データ | 参照元 | 用途 | version / config | 備考 |
| ------ | ------ | ---- | ---------------- | ---- |
| `reason_template` | DB | 文面テンプレート解決 | `is_active = true` | §8.3.2 |
| `item_semantic` | DB（Batch 正本） | 商品側 `evidence_text` / Concept 根拠 | `semantic_config_version_id` = Run 解決値 | §8.3.8。`item_semantic_テーブル定義書` §5.3 |
| `relationship_master` / `occasion_master` | DB（任意） | ラベル変換 | — | 未整備時はコード内マップ |
| `recommendation_result_item` | DB（`022` INSERT 済み） | FK 整合確認 | — | 読取のみ |
| Run 内メモリ（`feature_match_result` 等） | `execution_context` | 根拠選定 | — | 永続化は本モジュール |

---

## 8. 処理仕様

### 8.1 処理フロー

```mermaid
flowchart TD
    IN([Orchestrator から execution_context 受領]) --> VAL[入力検証<br/>items 件数・022 前提]
    VAL -->|不整合| ORCH_FB[Orchestrator へ回復不能を返却]
    VAL --> LOOP{{各 items[] を順次処理}}
    LOOP --> BASIS[Reason 根拠選定<br/>strong_match / scores / evidence]
    BASIS --> TPL[reason_template 解決]
    TPL -->|解決失敗| IFB1[Item 内部フォールバック]
    TPL --> GEN[テンプレート文面生成]
    GEN --> LLM{LLM 整形<br/>任意}
    LLM -->|成功| VALTXT[禁止表現・妥当性検証]
    LLM -->|失敗| VALTXT
    GEN -->|スキップ| VALTXT
    VALTXT -->|検証失敗| IFB1
    VALTXT --> BUILD[reason_basis_json 組立]
    IFB1 --> BUILD
    BUILD --> INS[recommendation_reason INSERT]
    INS -->|INSERT 失敗| IFB2[汎用文で再試行]
    IFB2 --> INS
    INS --> NEXT{次 Item}
    NEXT -->|あり| LOOP
    NEXT -->|なし| CNT[件数・fallback 集計]
    CNT --> OUT([execution_context 返却])
```

### 8.2 処理ステップ

| No | 処理 | 入力 | 出力 | 補足 |
| --: | ---- | ---- | ---- | ---- |
| 1 | 入力検証 | `execution_context` | — | `items` / `022` 前提 |
| 2 | `item_semantic` 一括読取 | `items[].item_id` + Run `semantic_config_version_id` | `semantic_json` マップ | §8.3.8 |
| 3 | Item ループ開始 | `items[]` | — | 順序は `rank` 昇順を推奨 |
| 4 | 根拠選定 | Feature / Score / `item_semantic` | `strong_match_features` 等 | Reason生成定義書 §11.1 |
| 5 | テンプレート解決 | relationship / occasion / feature | `template_id` | `reason_template_テーブル定義書` §7.1 |
| 6 | 文面生成 | テンプレート + 根拠 | summary / detail / points / badges | §8.3.3 |
| 7 | LLM 整形（config 有効時） | 根拠ファクトのみ | 整形文面 | §8.3.4。default OFF |
| 8 | 妥当性検証 | 生成文面 | 採用 / 差し替え | 禁止表現 §8.3.5 |
| 9 | `caution_note` 判定 | `risk_penalty` / weak_match | `caution_note` or null | §8.3.6 |
| 10 | `reason_basis_json` 組立 | 上記 | JSON | §6.2.2 |
| 11 | DB INSERT | Reason 行 | `recommendation_reason_id` | 同一トランザクション推奨 |
| 12 | ドメイン書き戻し | DB 結果 | `items[].reason` 等 | API 変換は api 層 |
| 13 | 集計・返却 | 全 Item 完了 | `reason_generator_*` | Metric §12.1 |

**処理順序の正本**: Recoモジュール一覧 §5.2 論理順序 23（`MOD-RECO-023`）。物理呼び出しは **`022` 直後・Result 返却直前**（`MOD-RECO-001` §8.2）。

### 8.3 アルゴリズム / 計算仕様

本モジュールは **新規スコア算出・順位変更を行わない**。Reason生成定義書のルールに基づく **説明文生成**のみを担当する。

#### 8.3.1 Reason 生成方針（MVP）

| 項目 | 内容 |
| ---- | ---- |
| 基本方式 | **テンプレート生成**（Reason生成定義書 §10 / §20.1） |
| 主理由 | `feature_match >= 0.80` の Feature（§8.3 / §11.1） |
| 優先順位 | context → strong_match → relationship/occasion → popularity → risk（§7.1） |
| `reason_points` | 2〜3 個（§11.2） |
| 商品側 `evidence_text` | **`item_semantic.semantic_json` から読取**（§8.3.8）。Snapshot テキストからの導出は行わない |
| LLM 整形 | **MVP 初期 default OFF**（§8.3.4）。env フラグでコード変更なしに ON 可能 |
| LLM 失敗時 | テンプレート結果を採用（§17.3）。Run 失敗にしない |
| 再現性 | `recommendation_run.model_version_id` を Run 正本とし、本テーブルには物理保持しない |

#### 8.3.2 テンプレート解決

`reason_template_テーブル定義書` §7.1 の優先順位を正とする。

1. `template_type`（summary / detail / point / caution）ごとに解決
2. `relationship_code` / `occasion_code` / `feature_code` の **具体一致**を優先
3. NULL ワイルドカード行をフォールバック
4. 同一 `template_name` 内で **最大 `template_version`** の `is_active = true` 行

解決不能時は **Item 内部フォールバック**（§10.2）。Run 全体を失敗させない。

#### 8.3.3 文面生成（概要）

Reason生成定義書 §10 のテンプレート群を基本とする。

| 出力 | 生成方針 |
| ---- | -------- |
| `reason_summary` | `{relationship_label}への{occasion_label}として、{primary_reason}がある候補です。` 系（§10.1） |
| `reason_detail` | Social / Symbolic / Popularity テンプレートの連結（§10.2〜§10.4） |
| `reason_points` | 主理由 Feature ごとに 1 点 + 補足 1 点（最大 3） |
| `reason_badges` | `FEATURE_BADGE_MAP`（§11.3 / §16.2） |
| `caution_note` | §8.3.6 条件時のみ |

#### 8.3.4 LLM 整形（config 有効時のみ・MVP）

| 項目 | 内容 |
| ---- | ---- |
| MVP 初期 default | **OFF**（テンプレートのみで Reason 生成。Reason生成定義書 §20.1） |
| 有効化スイッチ | 環境変数 **`RECO_REASON_LLM_REFINEMENT_ENABLED`**（boolean、**default `false`**）。`true` のときのみ本節の LLM 整形を実行する |
| 切替方針 | **コード変更・再デプロイなし**で ON/OFF 可能とする（env / DI 注入）。品質検証・Evaluation 時に env を `true` にして比較する |
| 呼び出し上限 | LLM 有効時も **Run あたり最大 1 回**（`MOD-RECO-004` on-demand パターン踏襲）。Item 単位の逐次 LLM 呼び出しは **行わない** |
| 目的 | 自然文整形のみ（Reason生成定義書 §12.1）。根拠の新規生成は禁止 |
| 入力 | `allowed_reason_facts` / `forbidden_claims` / `tone` / `max_length` |
| 出力 | JSON（`reason_summary` / `reason_points` / `caution_note`） |
| 失敗 | テンプレート結果をそのまま使用（§17.3）。Item 内部 fallback。Run 失敗にしない |
| Secret | API キーは server 側 env のみ。ログ・DB に出力しない |
| Client 契約 | timeout / retry は §13 および §16.1 No.15 を正とする。concrete 実装は External AI API Client（infrastructure 横断） |

#### 8.3.8 商品側 `evidence_text` 取得（`item_semantic` 正本）

Human 判断（Issue #993）により、商品側 Semantic 根拠は **Batch 正本 `item_semantic`** から読み取る。

| 項目 | 内容 |
| ---- | ---- |
| 正本 | `item_semantic_テーブル定義書` §5.3 の `semantic_json` |
| 読取キー | `item_id` + `semantic_config_version_id`（`execution_context.recommendation_run` / `config_versions` から Run 解決値を使用） |
| 取得フィールド | `semantic_json.concepts[].concept_code` / `confidence` / **`evidence_texts`**（string[]） |
| Reason へのマッピング | `evidence_texts[]` を `reason_basis_json.used_semantic_evidence[]` へ展開。各要素の `evidence_text` は配列先頭または Feature 整合する Concept の根拠を採用（Reason生成定義書 §14.2 構造） |
| Item Evidence テンプレート | §10.6。`evidence_text` は **商品説明由来の Batch 抽出根拠**のみ使用。Snapshot 列の自由引用は **行わない** |
| 欠損時 | 行不存在・`concepts[]` 空・`evidence_texts` 空 → **Item Evidence テンプレートをスキップ**し Feature Match ベースで Reason 生成（Reason生成定義書 §17.1）。Run 失敗にしない |
| 禁止 | Snapshot（`item_catchcopy_snapshot` 等）から `evidence_text` を **推測生成**すること（ハルシネーション防止） |

#### 8.3.5 禁止表現チェック

Reason生成定義書 §13 の禁止表現一覧を正とする。検出時は **該当文の削除またはテンプレートへフォールバック**する。

#### 8.3.6 `caution_note` 生成条件

Reason生成定義書 §11.4 を正とする。

| 条件 | 方針 |
| ---- | ---- |
| `risk_penalty >= 0.40` | 注意点を明示 |
| `avoid_similarity >= 0.60` | 避けたい傾向への補足 |
| `social_match < 0.60` | 関係性による注意 |
| 重要 Feature の `weak_match` | 控えめな弱点補足 |

#### 8.3.7 Orchestrator Port 契約（MVP）

| 項目 | 内容 |
| ---- | ---- |
| 呼び出し回数 | Run あたり **1 回**（`022` 成功後、`result_item_count >= 1`） |
| 成功 | 全 Item に `recommendation_reason` 行あり（通常 or fallback） |
| 成功（0 件） | **`result_item_count = 0` のとき Orchestrator は呼ばない** |
| Item 内部フォールバック | **モジュール成功扱い**。`reason_generator_fallback_count` を加算 |
| 回復不能 | `reco_error` を返却。Orchestrator が §17.2 汎用 Reason 注入 |
| Run 失敗 | **`021`/`022` 成功後は Reason のみでは `GRS-REC-012` にしない** |
| Phase Log | **`reason_generated` は成功後に Orchestrator が記録依頼** |
| Wiring | 出力フェーズ（`021`〜`023`）は **未配線（スタブ）**（`MOD-RECO-001` §8.4.2） |
| トランザクション | **`022` Item INSERT と同一トランザクション推奨**（`recommendation_reason_テーブル定義書` §12） |

---

## 9. データ項目マッピング

| 入力項目 | 内部項目 | 出力項目 | 変換内容 | 備考 |
| -------- | -------- | -------- | -------- | ---- |
| `items[].score_breakdown_json` | `used_scores` | `reason_basis_json.used_scores` | 抜粋コピー | 数値を本文に直書きしない |
| `feature_match_result` JOIN | `strong_match_features` | 文面 / badges | 閾値 0.80 | §6.2.3 |
| `item_semantic.semantic_json` | `used_semantic_evidence` | `reason_basis_json` | `evidence_texts` → `evidence_text` 展開 | §8.3.8 |
| `recommendation_request.relationship` | `relationship_label` | テンプレート埋め込み | マスタ変換 | |
| `recommendation_request.occasion` | `occasion_label` | 同上 | 同上 | |
| `reason_template` 行 | テンプレート本文 | summary / detail 等 | プレースホルダ置換 | `template_id` 記録 |
| — | 採番 | `recommendation_reason_id` | UUID v4 | INSERT 後 |
| — | 組立 | `reason_basis_json` | §5.4 必須 key | fallback 時も必須 |
| `items[].recommendation_result_item_id` | FK | `recommendation_result_item_id` | 1:1 | UNIQUE 制約 |

---

## 10. 状態・例外

### 10.1 状態

本モジュールは **ステートレス**（Run 内 1 回呼び出し）。生成する Reason の論理状態は以下。

| 状態 | 意味 | 遷移条件 | 記録先 |
| ---- | ---- | -------- | ------ |
| — | モジュール内部状態なし | — | — |
| 通常 Reason | 根拠に基づく説明文 | 生成・INSERT 成功 | `recommendation_reason` |
| 内部フォールバック Reason | 入力欠損・LLM 失敗等 | §10.2 | 同上 + `generation_method` |
| Orchestrator 注入 Reason | モジュール回復不能 | Orchestrator §10.3 | 同上（`orchestrator_generic_fallback`） |

API 上の `reasonStatus: completed` は **行の存在**で導出する（DB 物理列なし）。

### 10.2 例外

| 例外 | Error Code | 発生条件 | 呼び出し元への返却 | ログ |
| ---- | ---------- | -------- | ------------------ | ---- |
| 入力不整合 | —（モジュール内） | `items` 件数不一致等 | **回復不能** → Orchestrator 判断 | warn |
| 根拠不足（Item） | — | `strong_match` なし等 | **内部フォールバック**（§17.2 汎用文） | info |
| テンプレート解決失敗（Item） | — | 該当行なし | **内部フォールバック** | warn |
| LLM 失敗（Item） | — | API / parse 失敗 | **テンプレート文を採用**（§17.3） | warn |
| 禁止表現検出（Item） | — | §13 該当 | **差し替え or フォールバック** | warn |
| Reason INSERT 失敗（Item） | — | DB 制約違反等 | **汎用文で再 INSERT 試行** | error |
| 全 Item 回復不能 | `GRS-REC-013`¹ | Result 返却に必要な Reason 行を一切確保できない | Orchestrator が汎用注入を試行後も不可 | error（critical） |

¹ **`GRS-REC-013` の適用**: Item 単位のフォールバック失敗では原則使用しない。`021`/`022` 成功後に **Result 自体を返却できない致命ケース**に限定（`MOD-RECO-001` §10.3）。

**汎用 Reason 文（正本）** — Reason生成定義書 §17.2:

```text
今回の条件に対して、候補商品の中でも比較的バランスの良い商品です。
```

---

## 11. DB / 永続化

| テーブル | 操作 | 主な項目 | トランザクション | 備考 |
| -------- | ---- | -------- | ---------------- | ---- |
| `recommendation_reason` | INSERT | §6.2.2 全列 | **`022` と同一 TX 推奨** | IF-DB-RECO-008 |
| `reason_template` | SELECT | 解決用列 | 読取のみ | マスタ更新は対象外 |

**INSERT 手順**（`recommendation_reason_テーブル定義書` §12 引用）:

1. `recommendation_result_item` 行が存在することを確認
2. `reason_template` を解決
3. Feature / Score / Semantic evidence から文面・バッジを生成
4. `reason_basis_json` を組立（fallback 時も `generation_method` 必須）
5. 本テーブルへ INSERT（`reason_summary` は非空必須）
6. MVP では **INSERT 後 UPDATE しない**

---

## 12. ログ・メトリクス

| 種別 | 内容 | 出力タイミング | 保存先 | 備考 |
| ---- | ---- | -------------- | ------ | ---- |
| 構造化ログ | `trace_id` / `run_id` / `item_id` / `template_name` / fallback 有無 | Item 処理完了時 | アプリログ | `reason_basis_json` 全文は出さない |
| 構造化ログ | Reason 生成失敗（Item） | フォールバック時 | アプリログ | ログ・Observability設計書 |
| Phase Log 依頼 | `reason_generated` | 全 Item 完了後 | `MOD-RECO-028`（Orchestrator 経由） | 本モジュールは直接書かない |
| Error Log 依頼 | 回復不能時 | 失敗時 | `MOD-RECO-029`（`024` 経由） | |

### 12.1 メトリクス

| Metric | 内容 | 集計単位 | 用途 |
| ------ | ---- | -------- | ---- |
| `reason_generation_latency_ms` | Reason 生成全体時間 | Run | ログ・Observability設計書 §16.3 |
| `reason_generator_item_count` | 処理 Item 数 | Run | 件数整合 |
| `reason_generator_success_count` | 通常生成成功数 | Run | 品質監視 |
| `reason_generator_fallback_count` | 内部フォールバック数 | Run | fallback 率 |
| `reason_fallback_count` | 汎用文注入数（Orchestrator 合算） | Run / Item | `MOD-RECO-001` §12.1 |

---

## 13. 性能・非機能

| 観点 | 方針 |
| ---- | ---- |
| レイテンシ | Item 数（`top_k`、通常 ≤ 20）に比例。LLM **default OFF** のため MVP 初期はテンプレート + DB 読取が主 |
| 計算量 | O(top_k ×（テンプレート解決 + `item_semantic` 読取）)。DB は Item 単位 INSERT |
| 上位ガード | 出力フェーズ（`021`〜`023`）hard **500ms**（`MOD-RECO-001` §13.2）。本モジュール単体 hard は **MVP では設けない** |
| LLM timeout | **`RECO_REASON_LLM_REFINEMENT_ENABLED=true` 時のみ**適用。**connect + read 合算 300ms**（1 回あたり）。超過時テンプレート fallback |
| LLM retry | **0 回**（本モジュール内）。`MOD-RECO-004` と同様。Client 共通層でも Reason 経路は **再試行しない** |
| INSERT retry | 汎用文での **再 INSERT 試行は 1 回まで**（§10.2） |
| キャッシュ | `reason_template` / **`item_semantic`（Run 内 `item_id` 一括読取）** のキャッシュ可 |
| 並列実行 | MVP は **Item 順次処理**（同一 TX 整合のため） |

---

## 14. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | `strong_match` ありで summary / badges / points が生成されること | unit |
| 2 | テンプレート解決 | relationship / occasion / feature 条件に応じた `template_id` が選ばれること | unit |
| 3 | `reason_basis_json` | §5.4 必須 key がすべて入ること | unit |
| 4 | 閾値 | `feature_match < 0.80` が主理由に使われないこと | unit |
| 5 | `caution_note` | `risk_penalty >= 0.40` で生成されること / 低 risk では null | unit |
| 6 | 入力欠損 | relationship / occasion なしで汎用表現になること（§17.1） | unit |
| 7 | 根拠不足 | `strong_match` なしで内部フォールバックすること | unit |
| 8 | LLM 失敗 | テンプレート文が採用されること（§17.3） | unit |
| 9 | 禁止表現 | 検出時に差し替え or フォールバックすること | unit |
| 10 | DB INSERT | 1 Item 1 行・`reason_summary` 非空・FK 整合 | unit / integration |
| 11 | fallback INSERT | 内部フォールバックでも行が INSERT されること | integration |
| 12 | UNIQUE | 同一 `recommendation_result_item_id` への二重 INSERT が拒否されること | integration |
| 13 | スコア不変 | `rank` / `final_score` / Snapshot が変更されないこと | unit |
| 14 | Orchestrator 連携 | `022` 後 1 回呼び出し・Item 失敗でも Run 継続 | integration |
| 15 | 0 件スキップ | `result_item_count=0` で呼ばれないこと | integration |
| 16 | 責務境界 | Ranking / Snapshot / API 変換を行わないこと | unit |
| 17 | Metric | `reason_generator_*` / `reason_generation_latency_ms` が記録されること | integration |
| 18 | ログ | `trace_id` あり・secret / `reason_basis_json` 全文なし | unit |
| 19 | トランザクション | `022` INSERT と同一 TX でロールバックされること（Wiring 後） | integration |
| 20 | 部分成功 | 一部 Item のみ fallback でも他 Item は通常 Reason であること | integration |
| 21 | `item_semantic` 読取 | `semantic_json.concepts[].evidence_texts` が `used_semantic_evidence` に反映されること | unit / integration |
| 22 | `item_semantic` 欠損 | 行不存在時に Run 失敗せず Feature ベース Reason になること（§8.3.8） | unit |
| 23 | LLM default OFF | `RECO_REASON_LLM_REFINEMENT_ENABLED` 未設定 / `false` で External AI API Client が呼ばれないこと | unit |
| 24 | LLM ON 切替 | env `true` で LLM 整形が 1 Run 1 回実行されること | integration |
| 25 | LLM timeout | 300ms 超過でテンプレート fallback となり Run 継続すること | unit / integration |

---

## 15. 変更管理

### 15.1 変更履歴

| 日付 | 変更内容 | 関連 Issue / PR |
| ---- | -------- | --------------- |
| 2026-07-04 | 初版作成 | Issue #993 |
| 2026-07-05 | §16.1 No.14〜16 確定（`item_semantic` 正本・LLM default OFF・Client timeout/retry） | Issue #993 Human 判断 |

---

## 16. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| - | なし | - | - | - | - |

### 16.1 確定済み論点

| No | 論点 | 確定内容 |
| --: | ---- | -------- |
| 1 | 入力正本 | **`execution_context.recommendation_result`**（`022` 出力・Snapshot 済み） |
| 2 | スコア変更 | **行わない**（Reason は説明層） |
| 3 | Run 失敗条件 | **`021`/`022` 成功後は Reason のみで Run 失敗にしない**（`MOD-RECO-001` §10.3） |
| 4 | 汎用 Reason 文 | Reason生成定義書 §17.2 の固定文 |
| 5 | `generation_method` | **`reason_basis_json` のみ**（物理列なし） |
| 6 | 1 Item 1 Reason | **`UNIQUE(recommendation_result_item_id)`** |
| 7 | テンプレート版記録 | **`template_name` + `template_version`**（版サフィックス文字列 ID は使わない） |
| 8 | 0 件時の呼び出し | **`result_item_count = 0` のとき Orchestrator は呼ばない** |
| 9 | `GRS-REC-013` | Item 単位 fallback では使わず、Result 返却不能時のみ |
| 10 | トランザクション | **`022` Item INSERT と同一トランザクション推奨** |
| 11 | Phase Log | **`reason_generated` は Orchestrator が記録** |
| 12 | API 変換 | Public / Internal レスポンスは **`apps/api` 層** |
| 13 | `reason_template` Run 検証 | **`MOD-RECO-003` が OL で実施**。本モジュールは Item 単位解決のみ |
| 14 | 商品側 `evidence_text` 取得元 | **`item_semantic.semantic_json`（Batch 正本）** から読取。Snapshot からの簡易導出は **不採用**（§8.3.8） |
| 15 | LLM 整形 default | **MVP 初期 OFF**。環境変数 **`RECO_REASON_LLM_REFINEMENT_ENABLED`**（default `false`）で **コード変更なし**に ON/OFF。有効時は **Run あたり最大 1 回**（§8.3.4） |
| 16 | External AI API Client（Reason 経路） | **timeout 300ms（connect+read）/ retry 0**。超過・失敗時はテンプレート fallback。concrete Client は infrastructure 横断 Task の scope（§13） |

---

## 17. 関連資料

| 種別 | パス | 用途 |
| ---- | ---- | ---- |
| Recoモジュール一覧 | `docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md` | §6.22 |
| モジュール一覧 | `docs/05_アプリケーション設計/アプリ/モジュール一覧.md` | 出力処理分類 |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | Reason生成 |
| Reason生成定義書 | `docs/04_ドメインモデル設計/Reason生成定義書.md` | 生成ルール正本 |
| Orchestrator 仕様書 | `docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md` | §10.3 部分成功 |
| Result Builder 仕様書 | `docs/06_実装設計/reco/MOD-RECO-021_Recommendation Result Builderモジュール仕様書.md` | 上流 Result |
| Snapshot Builder 仕様書 | `docs/06_実装設計/reco/MOD-RECO-022_Result Snapshot Builderモジュール仕様書.md` | 直前工程 |
| Config Resolver 仕様書 | `docs/06_実装設計/reco/MOD-RECO-003_Config Version Resolverモジュール仕様書.md` | テンプレートカタログ検証 |
| recommendation_reason 定義 | `docs/06_実装設計/database/recommendation_reason_テーブル定義書.md` | DB 正本 |
| reason_template 定義 | `docs/06_実装設計/database/reason_template_テーブル定義書.md` | テンプレート解決 |
| item_semantic 定義 | `docs/06_実装設計/database/item_semantic_テーブル定義書.md` | 商品側 `evidence_text` 正本 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | `GRS-REC-013` 等 |
| ログ・Observability設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | Reason メトリクス |

---

## 18. レビュー観点

- Recoモジュール一覧 §6.22 のモジュール名・物理名・分類と一致している
- `MOD-RECO-001` §10.3 の部分成功（Reason 失敗でも Run 継続）と整合している
- `MOD-RECO-021` / `022` との責務境界（Result / Snapshot vs Reason）が明確である
- 対象 `MOD-RECO-023` の責務範囲に収まり、API-INT エンドポイント層の変更を混在させていない
- `recommendation_reason_テーブル定義書` / Reason生成定義書と矛盾していない
- 入力、出力、依存データ、例外、ログ、テスト観点が後続実装可能な粒度である
- secret や `.env` 実値が含まれていない

---

## 19. 備考

- Reason生成定義書 §16 の疑似コード（`select_reason_features` / `generate_reason_badges` 等）は実装 Task の参考とする
- 機能×モジュール対応表の **Reason Template Repository** / **Item Semantic Read Repository** / **External AI API Client** は infrastructure 層 Port として実装 Task で定義する
- LLM 品質検証時は **`RECO_REASON_LLM_REFINEMENT_ENABLED=true`** を設定し、同一 Run で template-only / LLM-refined の `reason_basis_json.generation_method` を比較する
- 実装配置は `prompts/definitions/tasks/mod-reco-023-reason-generator/implementation.yaml` と一致させる
- API-PUB-002 / API-INT-002 の `reasonStatus` / `isFallback` 契約詳細は Contract Task で本仕様書 §10 と双方向整合する
