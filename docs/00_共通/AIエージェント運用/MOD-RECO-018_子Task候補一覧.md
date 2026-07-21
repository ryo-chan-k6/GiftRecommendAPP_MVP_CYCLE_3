# MOD-RECO-018:Risk Scorer 子Task候補一覧

## 1. 概要

本ドキュメントは、[Epic]MOD-RECO-018:Risk Scorer（Issue #1508）における子Task候補を整理する。

**Epic Issue**: #1508  
**Epic Branch**: `feature/epic-1508-mod-reco-018-risk-scorer`  
**成果物識別子**: MOD-RECO-018  
**モジュール名**: Risk Scorer  
**責務**: リスク補正スコア（risk_score）算出  
**処理種別**: OL（Online処理）  
**MVP対象**: ○  
**分類**: Ranking責務

---

## 2. Epic範囲

### 2.1 含まれる作業

- MOD-RECO-018 Risk Scorerのモジュール仕様書作成
- MOD-RECO-018 Risk Scorerの実装
- MOD-RECO-018 Risk Scorerの単体テスト

### 2.2 含まれない作業（out of scope）

- API-INT-002 エンドポイント層（`apps/reco/src/reco/api/**`）
- API-PUB-002 Public API 実装
- MOD-RECO-001 Orchestrator 本体の変更（別 Epic #260）
- 他 Recoモジュール（当該 MOD-RECO-018 以外）本体の設計・実装
- 画面（SCR-*）の設計・実装
- OpenAPI / Orval / generated 変更
- DB schema 変更（専用 Task へ切り出し）

---

## 3. 子Task一覧

| No | Task ID | Task タイトル | Definition Path | Phase | Status | PR Target |
|----|---------|--------------|-----------------|--------|--------|-----------|
| 1  | task-mod-reco-018-risk-scorer-module-spec | MOD-RECO-018:Risk Scorerモジュール仕様書作成 | prompts/definitions/tasks/mod-reco-018-risk-scorer/module-spec.yaml | 06_実装設計 | 未着手 | Epic Branch |
| 2  | task-mod-reco-018-risk-scorer-implementation | MOD-RECO-018:Risk Scorer実装 | prompts/definitions/tasks/mod-reco-018-risk-scorer/implementation.yaml | 07_開発・単体テスト | 未着手 | Epic Branch |
| 3  | task-mod-reco-018-risk-scorer-unit-test | MOD-RECO-018:Risk Scorer単体テスト | prompts/definitions/tasks/mod-reco-018-risk-scorer/unit-test.yaml | 07_開発・単体テスト | 未着手 | Epic Branch |

---

## 4. Task詳細

### 4.1 Task 1: MOD-RECO-018:Risk Scorerモジュール仕様書作成

**定義ファイル**: `prompts/definitions/tasks/mod-reco-018-risk-scorer/module-spec.yaml`

**目的**: MOD-RECO-018（Risk Scorer / リスク補正算出）のモジュール仕様書を、Recoモジュール一覧および関連ドメイン定義書に基づいて作成する。

**成果物**: `docs/06_実装設計/reco/MOD-RECO-018_Risk Scorerモジュール仕様書.md`

**主な記載内容**:
- モジュール概要・責務
- 入出力ポート定義（ExecutionContext連携）
- リスク補正スコア算出ロジック
- NG商品検出処理
- リスク種別（alcohol / adult / other）の判定方針
- エラーハンドリング
- ログ・Observability
- テスト方針

**依存関係**:
- 前提: Recoモジュール一覧
- 前提: Ranking定義書
- 前提: #260（MOD-RECO-001 Orchestrator仕様書）

**工程**: 06_実装設計

---

### 4.2 Task 2: MOD-RECO-018:Risk Scorer実装

**定義ファイル**: `prompts/definitions/tasks/mod-reco-018-risk-scorer/implementation.yaml`

**目的**: MOD-RECO-018 Risk Scorerのモジュール仕様書に基づき、`apps/reco/src/reco/application/risk-scorer/**` 配下に実装を行う。

**主な実装対象**:
- `RiskScorer` クラス本体
- リスク補正スコア算出ロジック
- NG商品検出ロジック
- ExecutionContext入出力対応
- エラーハンドリング
- ログ出力

**対象ディレクトリ**: `apps/reco/src/reco/application/risk-scorer/**`

**依存関係**:
- 前提: Task 1（モジュール仕様書）完了
- 前提: MOD-RECO-001 Orchestrator実装（ポート契約）

**工程**: 07_開発・単体テスト

---

### 4.3 Task 3: MOD-RECO-018:Risk Scorer単体テスト

**定義ファイル**: `prompts/definitions/tasks/mod-reco-018-risk-scorer/unit-test.yaml`

**目的**: MOD-RECO-018 Risk Scorerの単体テストを作成し、モジュール仕様書および実装の妥当性を検証する。

**主なテスト対象**:
- リスク補正スコア算出の正常系
- NG商品検出の正常系・異常系
- リスク種別判定の境界値
- ExecutionContext入出力の整合性
- エラーケース（不正入力・NULL・未定義）

**対象ディレクトリ**: 
- `apps/reco/tests/unit/application/risk-scorer/**`
- `apps/reco/tests/module/risk-scorer/**`

**依存関係**:
- 前提: Task 2（実装）完了

**工程**: 07_開発・単体テスト

---

## 5. Epic Scope（成果物化方針書 §3.5.2）

### 5.1 allowed_paths

本 Epic の子 Task は、以下のパスに限定する。

```
docs/06_実装設計/reco/MOD-RECO-018_Risk Scorerモジュール仕様書.md
apps/reco/src/reco/application/risk-scorer/**
apps/reco/src/reco/domain/**
apps/reco/src/reco/pipeline/**
apps/reco/tests/unit/application/risk-scorer/**
apps/reco/tests/module/risk-scorer/**
prompts/definitions/tasks/mod-reco-018-risk-scorer/**
prompts/definitions/reviews/mod-reco-018-risk-scorer/**
```

### 5.2 forbidden_paths

以下のパスへの変更は、本 Epic の子 Task では行わない。

```
apps/reco/src/reco/api/**
apps/reco/src/reco/application/recommendation-orchestrator/**
apps/reco/src/reco/application/recommendation-run-recorder/**
apps/reco/src/reco/application/config-version-resolver/**
apps/reco/src/reco/application/user-semantic-extractor/**
apps/reco/src/reco/application/external-condition-feature-estimator/**
apps/reco/src/reco/application/internal-condition-feature-estimator/**
apps/reco/src/reco/application/user-feature-generator/**
apps/reco/src/reco/application/user-meaning-projector/**
apps/reco/src/reco/application/user-context-builder/**
apps/reco/src/reco/application/query-embedding-generator/**
apps/reco/src/reco/application/pre-hard-filter-executor/**
apps/reco/src/reco/application/candidate-retriever/**
apps/reco/src/reco/application/post-hard-filter-executor/**
apps/reco/src/reco/application/feature-matcher/**
apps/reco/src/reco/application/meaning-match-aggregator/**
apps/reco/src/reco/application/context-scorer/**
apps/reco/src/reco/application/popularity-scorer/**
apps/reco/src/reco/application/final-score-calculator/**
apps/reco/src/reco/application/final-ranker/**
apps/reco/src/reco/application/recommendation-result-builder/**
apps/reco/src/reco/application/result-snapshot-builder/**
apps/reco/src/reco/application/reason-generator/**
apps/reco/src/reco/application/item-semantic-generator/**
apps/reco/src/reco/application/item-feature-generator/**
apps/reco/src/modules/**
apps/reco/src/app/**
apps/api/**
apps/web/**
apps/batch/**
packages/contracts/**
openapi/**
db/**
```

---

## 6. Branch / PR 方針

### 6.1 Epic Branch

- **Branch名**: `feature/epic-1508-mod-reco-018-risk-scorer`
- **Branch base**: `develop`
- **PR target**: `develop`

### 6.2 子Task Branch

各子Taskは、以下のBranch命名規則に従う。

```
<type>/<unit>-<issue-number>-<english-summary>
```

例:
```
docs/task-<issue-number>-mod-reco-018-module-spec
feature/task-<issue-number>-mod-reco-018-implementation
test/task-<issue-number>-mod-reco-018-unit-test
```

### 6.3 子Task PR target

子TaskのPRは、すべて **Epic Branch**（`feature/epic-1508-mod-reco-018-risk-scorer`）に向ける。

`develop` に直接向けてはならない。

---

## 7. 依存関係

### 7.1 前提Epic

- #260: [Epic]MOD-RECO-001:Recommendation Orchestrator
  - 目的: ポート契約（ExecutionContext入出力）の正本
  - 状態: 完了想定

### 7.2 関連Issue

なし（MOD-* Epic は原則 dependencies.epics なし。成果物化方針書 §3.5.3）

---

## 8. 並列着手ウェーブ

**ウェーブ 4**（bootstrap Issue 参照）

MOD-RECO-018 は、以下の理由でウェーブ 4 に分類される。

- MOD-RECO-001 Orchestrator（ウェーブ 1）完了後に着手可能
- Ranking責務（後続処理）のため、Retrieval / Matching（ウェーブ 2〜3）後に配置

---

## 9. レビュー観点

### 9.1 Epic全体

- [ ] Epic の作業範囲が MOD-RECO-018 本体に閉じているか
- [ ] epic_scope.allowed_paths / forbidden_paths が成果物化方針書 §3.5.2 と整合しているか
- [ ] Epic PR target が develop であるか
- [ ] 子 Task 候補が整理されているか

### 9.2 子Task共通

- [ ] Task Definition の scope 内に収まっているか
- [ ] forbidden_paths への変更が含まれていないか
- [ ] PR target が Epic Branch であるか
- [ ] MOD-RECO-001 Orchestrator のポート契約と整合しているか
- [ ] Recoモジュール一覧・Ranking定義書と矛盾していないか

---

## 10. 関連ドキュメント

| ドキュメント | パス | 役割 |
|-------------|------|------|
| Recoモジュール一覧 | `docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md` | モジュール設計・実装の前提 |
| モジュール一覧 | `docs/05_アプリケーション設計/アプリ/モジュール一覧.md` | モジュール設計・実装の前提 |
| Ranking定義書 | `docs/04_ドメインモデル設計/Ranking定義書.md` | リスク補正スコア算出の前提 |
| MOD-RECO-001仕様書 | `docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md` | ポート契約・ExecutionContext |
| 成果物一覧×Task Definition化方針書 | `docs/00_共通/AIエージェント運用/成果物一覧×Task Definition化方針書.md` | Epic Scope・Task Definition方針 |
| Task Definition設計書 | `docs/00_共通/AIエージェント運用/Task Definition設計書.md` | Task Definition構造・命名規則 |

---

## 11. 備考

- Epic は作業管理単位。成果物正本は子 Task で作成する。
- 命名の正本は Task Definition設計書 §15.0・§15.1。
- MOD-* Epic は原則 dependencies.epics なし（成果物化方針書 §3.5.3）。#260 は関連 Issue として記載。
- bootstrap: `prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml`
- 物理配置パス（application/risk-scorer/**）の最終確定は実装Task着手時に行う。
- domain/** / infrastructure/** への横断変更が必要になった場合は別 Task 化を検討する。
