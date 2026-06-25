#!/usr/bin/env python3
"""Generate Epic/Task/Review Definition scaffolds for MOD-RECO-002..027."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts" / "definitions"

MODULES: list[dict[str, object]] = [
    {
        "id": "002",
        "name_ja": "Recommendation Run記録",
        "physical": "Recommendation Run Recorder",
        "category": "ログ・観測",
        "ptype": "OL",
        "mvp": True,
        "slug": "recommendation-run-recorder",
        "wave": 0,
        "extra_docs": ["docs/06_実装設計/database/recommendation_run_テーブル定義書.md"],
        "domain_docs": ["docs/04_ドメインモデル設計/RecommendationRequest定義書.md"],
    },
    {
        "id": "003",
        "name_ja": "Config / Version解決",
        "physical": "Config Version Resolver",
        "category": "設定解決",
        "ptype": "共通",
        "mvp": True,
        "slug": "config-version-resolver",
        "wave": 0,
        "extra_docs": [
            "docs/06_実装設計/database/model_version_テーブル定義書.md",
            "docs/06_実装設計/database/semantic_config_version_テーブル定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "004",
        "name_ja": "Semantic抽出",
        "physical": "User Semantic Extractor",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "user-semantic-extractor",
        "wave": 1,
        "extra_docs": [
            "docs/04_ドメインモデル設計/Semantic Concept定義書.md",
            "docs/04_ドメインモデル設計/Semanticルール定義書.md",
        ],
        "domain_docs": ["docs/04_ドメインモデル設計/RecommendationRequest定義書.md"],
    },
    {
        "id": "005",
        "name_ja": "外部条件特徴量推定",
        "physical": "External Condition Feature Estimator",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "external-condition-feature-estimator",
        "wave": 1,
        "extra_docs": [
            "docs/04_ドメインモデル設計/Feature定義書.md",
            "docs/04_ドメインモデル設計/Featureルール定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "006",
        "name_ja": "内部条件特徴量推定",
        "physical": "Internal Condition Feature Estimator",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "internal-condition-feature-estimator",
        "wave": 1,
        "extra_docs": [
            "docs/04_ドメインモデル設計/Feature定義書.md",
            "docs/04_ドメインモデル設計/Featureルール定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "007",
        "name_ja": "User Feature生成",
        "physical": "User Feature Generator",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "user-feature-generator",
        "wave": 1,
        "extra_docs": ["docs/04_ドメインモデル設計/Feature定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "008",
        "name_ja": "User Meaning射影",
        "physical": "User Meaning Projector",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "user-meaning-projector",
        "wave": 1,
        "extra_docs": ["docs/04_ドメインモデル設計/Gift Meaning Space定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "009",
        "name_ja": "User Context生成",
        "physical": "User Context Builder",
        "category": "User Meaning",
        "ptype": "OL",
        "mvp": True,
        "slug": "user-context-builder",
        "wave": 1,
        "extra_docs": ["docs/04_ドメインモデル設計/Retrieval定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "010",
        "name_ja": "Query Embedding生成",
        "physical": "Query Embedding Generator",
        "category": "Retrieval",
        "ptype": "OL",
        "mvp": True,
        "slug": "query-embedding-generator",
        "wave": 2,
        "extra_docs": ["docs/04_ドメインモデル設計/Retrieval定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "011",
        "name_ja": "Pre Hard Filter",
        "physical": "Pre Hard Filter Executor",
        "category": "Retrieval",
        "ptype": "OL",
        "mvp": True,
        "slug": "pre-hard-filter-executor",
        "wave": 2,
        "extra_docs": ["docs/04_ドメインモデル設計/Retrieval定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "012",
        "name_ja": "候補商品抽出",
        "physical": "Candidate Retriever",
        "category": "Retrieval",
        "ptype": "OL",
        "mvp": True,
        "slug": "candidate-retriever",
        "wave": 2,
        "extra_docs": ["docs/04_ドメインモデル設計/Retrieval定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "013",
        "name_ja": "Post Hard Filter",
        "physical": "Post Hard Filter Executor",
        "category": "Retrieval",
        "ptype": "OL",
        "mvp": True,
        "slug": "post-hard-filter-executor",
        "wave": 2,
        "extra_docs": ["docs/04_ドメインモデル設計/Retrieval定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "014",
        "name_ja": "feature一致度計算",
        "physical": "Feature Matcher",
        "category": "Matching",
        "ptype": "OL",
        "mvp": True,
        "slug": "feature-matcher",
        "wave": 3,
        "extra_docs": ["docs/04_ドメインモデル設計/Matching定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "015",
        "name_ja": "意味マッチ集約",
        "physical": "Meaning Match Aggregator",
        "category": "Matching",
        "ptype": "OL",
        "mvp": True,
        "slug": "meaning-match-aggregator",
        "wave": 3,
        "extra_docs": ["docs/04_ドメインモデル設計/Matching定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "016",
        "name_ja": "文脈スコア算出",
        "physical": "Context Scorer",
        "category": "Matching",
        "ptype": "OL",
        "mvp": True,
        "slug": "context-scorer",
        "wave": 3,
        "extra_docs": ["docs/04_ドメインモデル設計/Matching定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "017",
        "name_ja": "人気補正算出",
        "physical": "Popularity Scorer",
        "category": "Ranking",
        "ptype": "OL",
        "mvp": True,
        "slug": "popularity-scorer",
        "wave": 4,
        "extra_docs": [
            "docs/04_ドメインモデル設計/Ranking定義書.md",
            "docs/06_実装設計/database/item_popularity_signal_テーブル定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "018",
        "name_ja": "リスク補正算出",
        "physical": "Risk Scorer",
        "category": "Ranking",
        "ptype": "OL",
        "mvp": True,
        "slug": "risk-scorer",
        "wave": 4,
        "extra_docs": ["docs/04_ドメインモデル設計/Ranking定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "019",
        "name_ja": "最終スコア算出",
        "physical": "Final Score Calculator",
        "category": "Ranking",
        "ptype": "OL",
        "mvp": True,
        "slug": "final-score-calculator",
        "wave": 4,
        "extra_docs": ["docs/04_ドメインモデル設計/Ranking定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "020",
        "name_ja": "最終順位生成",
        "physical": "Final Ranker",
        "category": "Ranking",
        "ptype": "OL",
        "mvp": True,
        "slug": "final-ranker",
        "wave": 4,
        "extra_docs": ["docs/04_ドメインモデル設計/Ranking定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "021",
        "name_ja": "Recommendation Result生成",
        "physical": "Recommendation Result Builder",
        "category": "出力処理",
        "ptype": "OL",
        "mvp": True,
        "slug": "recommendation-result-builder",
        "wave": 5,
        "extra_docs": ["docs/04_ドメインモデル設計/RecommendationResult定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "022",
        "name_ja": "Result Snapshot生成",
        "physical": "Result Snapshot Builder",
        "category": "出力処理",
        "ptype": "OL",
        "mvp": True,
        "slug": "result-snapshot-builder",
        "wave": 5,
        "extra_docs": ["docs/04_ドメインモデル設計/RecommendationResult定義書.md"],
        "domain_docs": [],
    },
    {
        "id": "023",
        "name_ja": "Reason生成",
        "physical": "Reason Generator",
        "category": "出力処理",
        "ptype": "OL",
        "mvp": True,
        "slug": "reason-generator",
        "wave": 5,
        "extra_docs": [
            "docs/04_ドメインモデル設計/Reason生成定義書.md",
            "docs/06_実装設計/database/recommendation_reason_テーブル定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "026",
        "name_ja": "Item Semantic抽出",
        "physical": "Item Semantic Generator",
        "category": "商品意味推定支援",
        "ptype": "BT",
        "mvp": True,
        "slug": "item-semantic-generator",
        "wave": "bt",
        "extra_docs": [
            "docs/04_ドメインモデル設計/Semantic Concept定義書.md",
            "docs/04_ドメインモデル設計/Semanticルール定義書.md",
        ],
        "domain_docs": [],
    },
    {
        "id": "027",
        "name_ja": "Item Feature生成",
        "physical": "Item Feature Generator",
        "category": "商品意味推定支援",
        "ptype": "BT",
        "mvp": True,
        "slug": "item-feature-generator",
        "wave": "bt",
        "extra_docs": ["docs/04_ドメインモデル設計/Feature定義書.md"],
        "domain_docs": [],
    },
]

COMMON_DOCS = [
    "docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md",
    "docs/05_アプリケーション設計/アプリ/モジュール一覧.md",
    "docs/05_アプリケーション設計/アプリ/エラーコード定義書.md",
    "docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md",
    "docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md",
    "docs/00_共通/AIエージェント運用/成果物一覧×Task Definition化方針書.md",
    "docs/00_共通/AIエージェント運用/Task Definition設計書.md",
]


def mod_id(m: dict[str, object]) -> str:
    return f"MOD-RECO-{m['id']}"


def workstream(m: dict[str, object]) -> str:
    return f"mod-reco-{m['id']}-{m['slug']}"


def spec_doc_path(m: dict[str, object]) -> str:
    return f"docs/06_実装設計/reco/{mod_id(m)}_{m['physical']}モジュール仕様書.md"


def app_path(m: dict[str, object]) -> str:
    return f"apps/reco/src/reco/application/{m['slug']}/**"


def yaml_docs(paths: list[str], purpose: str = "モジュール設計・実装の前提確認") -> str:
    lines = []
    for p in paths:
        req = "true" if p in COMMON_DOCS[:4] or "Recoモジュール一覧" in p else "false"
        lines.append(f'    - path: "{p}"')
        lines.append(f"      required: {req}")
        lines.append(f'      purpose: "{purpose}"')
    return "\n".join(lines)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).rstrip() + "\n", encoding="utf-8")


def gen_epic(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    name_ja = m["name_ja"]
    category = m["category"]
    ptype = m["ptype"]
    slug = m["slug"]
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "epic"

        epic:
          id: "epic-{ws}"
          title: "{mid}:{physical}"
          summary: "{mid}（{physical} / {name_ja}）に関するモジュール仕様書・実装・単体テストを管理するEpic。MOD-RECO-001 Orchestrator から呼び出され、推薦パイプラインの {category} 責務を担う（処理種別: {ptype}）。"

        work_mode: "ai-agent"

        commands:
          primary: "/start-epic"
          allowed:
            - "/start-epic"
            - "/start-task"
            - "/summarize-work"
          next:
            success: "/start-task"
            review_fix: null
            blocked: null

        agent:
          primary: "orchestrator-ai"
          support:
            - "support-ai"
          review:
            - "reviewer-ai"

        background: |
          06_実装設計および 07_開発・単体テストにおいて、{mid}（{physical}）に関する設計・実装・テストを、Epic Issue と Epic Branch で一元管理する。
          本モジュールは Recoモジュール一覧 §4 / §6 の {category} 分類モジュール（処理種別: {ptype}、MVP対象 ○）である。
          MOD-RECO-001 Recommendation Orchestrator から `ExecutionContext` 経由で呼び出される。
          本 Epic は **Recoモジュール本体**（`apps/reco/src/reco/application/{slug}/**`）に限定し、エンドポイント層（`apps/reco/src/reco/api/**`）は [Epic]API-INT-002 配下とする。
          並列着手ウェーブ目安: {m["wave"]}（bootstrap Issue 参照）。

        objective: |
          {mid} に関する Epic Issue と Epic Branch を作成し、配下 Task（モジュール仕様書 / 実装 / 単体テスト）の作業単位を整理する。
          配下 Task の差分が epic_scope.allowed_paths から外れないことをガードする。
          develop への統合は本 Epic PR のみで行う。

        scope:
          - "{mid} に関する子 Task の作業単位を整理する（モジュール仕様書 / 実装 / 単体テスト）"
          - "Epic Issue を作成する"
          - "Epic Branch を develop から作成する"
          - "子 Task Definition の配置方針（prompts/definitions/tasks/{ws}/**）を整理する"

        out_of_scope:
          - "API-INT-002 エンドポイント層（`apps/reco/src/reco/api/**`）"
          - "API-PUB-002 Public API 実装"
          - "MOD-RECO-001 Orchestrator 本体の変更（別 Epic #260）"
          - "他 Recoモジュール（当該 {mid} 以外）本体の設計・実装"
          - "画面（SCR-*）の設計・実装"
          - "OpenAPI / Orval / generated 変更"
          - "DB schema 変更（専用 Task へ切り出し）"

        input:
          docs:
        {yaml_docs(list(dict.fromkeys([*COMMON_DOCS, *m["extra_docs"], *m["domain_docs"]])))}
          templates: []
          files: []
          issues:
            - number: 260
              purpose: "前提 Epic（MOD-RECO-001 Recommendation Orchestrator 完了）"
          prs: []

        output:
          docs: []
          files: []
          tests: []
          generated:
            expected: false
            paths: []
            handling: "none"
          logs:
            ai_logs_required: false
            path: null

        deliverables:
          - "Epic Issue（タイトル: [Epic]{mid}:{physical}）"
          - "Epic Branch（develop 起点 / feature/epic-<issue-number>-{ws}）"
          - "子 Task 候補一覧（モジュール仕様書 / 実装 / 単体テスト）"

        acceptance_criteria:
          - "Epic Issue が作成されている"
          - "Issue タイトルが [Epic]{mid}:{physical} 形式である"
          - "Epic Branch が develop から作成されている"
          - "子 Task の PR target が親 Epic Branch である方針が明記されている"
          - "epic_scope.forbidden_paths に apps/reco/src/reco/api/** が明示されている"

        branch:
          no_branch: false
          name: "feature/epic-<issue-number>-{ws}"
          base: "develop"
          target: "develop"
          worktree_required: false

        project:
          project_name: "Gift Recommendation Service MVP Cycle 3"
          fields:
            phase: "07_開発・単体テスト"
            status: "Todo"
            priority: "high"
            planned_start: null
            due_date: null

        issue:
          unit: "epic"
          type: "feature"
          area: "reco"

        epic_scope:
          artifact_id: "{mid}"
          allowed_paths:
            - "{spec_doc_path(m)}"
            - "{app_path(m)}"
            - "apps/reco/tests/unit/application/{slug}/**"
            - "apps/reco/tests/module/{slug}/**"
            - "prompts/definitions/tasks/{ws}/**"
            - "prompts/definitions/reviews/{ws}/**"
          forbidden_paths:
            - "apps/reco/src/reco/api/**"
            - "apps/reco/src/reco/application/recommendation-orchestrator/**"
            - "apps/api/**"
            - "apps/web/**"
            - "apps/batch/**"
            - "packages/contracts/**"
            - "openapi/**"
            - "db/**"
          child_task_areas:
            - "module-spec"
            - "implementation"
            - "unit-test"

        dependencies:
          epics: []
          issues:
            - number: 260
              purpose: "MOD-RECO-001 Orchestrator 完了（ポート契約・処理順序の正本）"
          prs: []
          tasks: []
          blocking: false

        parallel_control:
          depends_on: []
          blocks: []
          exclusive_files:
            - "{app_path(m)}"
            - "{spec_doc_path(m)}"
          conflict_risk: "medium"
          contract_impact: false
          generated_impact: false
          db_impact: false

        test_policy:
          required: []
          commands: []
          manual_checks:
            - "Epic scope が {mid} モジュール本体に閉じているか確認する"
            - "apps/reco/src/reco/api/** への変更が混入していないか確認する"
          not_required:
            - "unit test"
          skip_reason:
            "unit test": "Epic は作業管理単位のため対象外"

        review:
          human_review_required: true
          ai_review_required: false
          review_points:
            - "Epic の作業範囲が {mid} 本体に閉じているか"
            - "epic_scope.allowed_paths / forbidden_paths が成果物化方針書 §3.5.2 と整合しているか"
            - "Epic PR target が develop であるか"
          specialist_reviews:
            docs: false
            test: false
            contract: false
            security: false

        operation_logging:
          level: "standard"
          ai_logs:
            intake: false
            incidents: false
            cross_cutting: false
            experiments: true
          reason: "識別子単位 Epic Definition bootstrap 由来のスキャフォールド。"

        risk_points:
          - "物理配置パス（application/{slug}/**）の最終確定"
          - "Orchestrator スタブ差し替えタイミングとの整合"
          - "domain/** / infrastructure/** への横断変更が必要になった場合の別 Task 化"

        human_decision_points:
          - "物理配置パス（application/{slug}/** vs pipeline/**）の採用可否"
          - "並列ウェーブ {m['wave']} での着手タイミング"

        stop_conditions:
          - "必須 input.docs が存在しない場合"
          - "Recoモジュール一覧に {mid} が存在しない場合"
          - "epic_scope.allowed_paths が空または未記載の場合"
          - "apps/reco/src/reco/api 配下への変更を本 Epic 配下 Task で実施する必要が出た場合"

        notes:
          - "Epic は作業管理単位。成果物正本は子 Task で作成する。"
          - "命名の正本は Task Definition設計書 §15.0・§15.1。"
          - "子 Task: prompts/definitions/tasks/{ws}/module-spec.yaml"
          - "MOD-* Epic は原則 dependencies.epics なし（成果物化方針書 §3.5.3）。#260 は関連 Issue として記載。"
          - "bootstrap: prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml"
        """
    )


def gen_module_spec(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    name_ja = m["name_ja"]
    spec = spec_doc_path(m)
    docs = list(dict.fromkeys([*COMMON_DOCS, *m["extra_docs"], *m["domain_docs"]]))
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "task"

        task:
          id: "task-{ws}-module-spec"
          title: "{mid}:{physical}モジュール仕様書作成"
          summary: "{mid}（{physical} / {name_ja}）のモジュール仕様書（{spec}）を、Recoモジュール一覧および関連ドメイン定義書に基づいて作成する。"

        work_mode: "ai-agent"

        parent:
          epic_issue: "[Epic]{mid}:{physical}"
          epic_issue_number: null
          epic_branch: "feature/epic-<issue-number>-{ws}"
          related_issues:
            - number: 260
              purpose: "MOD-RECO-001 Orchestrator（呼び出し元・ポート契約）"
          related_prs: []

        commands:
          primary: "/start-task"
          allowed:
            - "/start-task"
            - "/work-issue"
            - "/create-pr"
            - "/fix-review-comments"
            - "/summarize-work"
          next:
            success: "/work-issue"
            review_fix: "/fix-review-comments"
            blocked: null

        agent:
          primary: "worker-ai"
          support:
            - "orchestrator-ai"
            - "support-ai"
          review:
            - "reviewer-ai"
            - "docs-reviewer-ai"

        background: |
          06_実装設計において、{mid}（{physical}）の Recoモジュール仕様書を作成する。
          本 Task は当該モジュール本体に責務を限定し、API-INT-002 エンドポイント層や他 Recoモジュール本体の仕様は別 Epic / Task とする。
          MOD-RECO-001 Orchestrator 仕様書のポート契約（`ExecutionContext` 入出力）と整合させる。

        objective: |
          {mid} について、apps/reco 実装・単体テスト・レビューが可能な粒度のモジュール仕様書を作成する。
          作成する仕様書は prompts/templates/docs/module-spec.md に準拠する。

        scope:
          - "{mid} のモジュール仕様書を新規作成する"
          - "モジュール基本情報・主責務・対象外責務・入出力・処理フロー・例外・ログ・テスト観点を整理する"
          - "Orchestrator（MOD-RECO-001）との呼び出し関係・失敗時の扱いを整理する"

        out_of_scope:
          - "他 Recoモジュール本体のモジュール仕様書作成"
          - "apps/reco の実装"
          - "OpenAPI / DB schema 変更"
          - "Recoモジュール一覧そのものの変更"

        input:
          docs:
        {yaml_docs(docs)}
          templates:
            - path: "prompts/templates/docs/module-spec.md"
              required: true
              purpose: "モジュール仕様書標準フォーマット"
              applies_to:
                - "{spec}"
          files: []
          issues: []
          prs: []

        output:
          docs:
            - path: "{spec}"
              action: "create"
              required: true
              template: "prompts/templates/docs/module-spec.md"
          files: []
          tests: []
          generated:
            expected: false
            paths: []
            handling: "none"
          logs:
            ai_logs_required: false
            path: null

        deliverables:
          - "{mid} モジュール仕様書"
          - "Orchestrator との I/F 整理"
          - "テスト観点・未決事項"

        acceptance_criteria:
          - "{spec} が作成されている"
          - "prompts/templates/docs/module-spec.md の章構成に準拠している"
          - "Recoモジュール一覧の {mid} と矛盾しない"
          - "API-INT-002 エンドポイント層を責務範囲に含めていない"
          - "secret、APIキー、.env 実値が含まれていない"

        branch:
          no_branch: false
          name: "docs/task-<issue-number>-{ws}-module-spec"
          base: "feature/epic-<issue-number>-{ws}"
          target: "feature/epic-<issue-number>-{ws}"
          worktree_required: true

        project:
          project_name: "Gift Recommendation Service MVP Cycle 3"
          fields:
            phase: "06_実装設計"
            status: "Todo"
            priority: "high"

        issue:
          unit: "task"
          type: "docs"
          area: "reco"

        dependencies:
          epics: []
          issues:
            - number: 260
              purpose: "Orchestrator ポート契約の正本"
          prs: []
          tasks: []
          blocking: false

        parallel_control:
          exclusive_files:
            - "{spec}"
          conflict_risk: "low"
          contract_impact: false
          generated_impact: false
          db_impact: false

        test_policy:
          required:
            - "docs review"
            - "markdown format check"
            - "secret check"
          not_required:
            - "unit test"
          skip_reason:
            "unit test": "docs作成Taskのため対象外"

        review:
          human_review_required: true
          ai_review_required: true
          review_points:
            - "Recoモジュール一覧との整合"
            - "Orchestrator との I/F 明確性"
            - "epic_scope 内に収まっているか"
          specialist_reviews:
            docs: true
            test: false
            contract: false
            security: false

        operation_logging:
          level: "standard"
          ai_logs:
            experiments: true

        notes:
          - "Definition bootstrap 由来スキャフォールド。Epic Issue 番号確定後に parent を更新する。"
          - "workstream: {ws}"
        """
    )


def gen_implementation(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    slug = m["slug"]
    spec = spec_doc_path(m)
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "task"

        task:
          id: "task-{ws}-implementation"
          title: "{mid}:{physical}実装"
          summary: "{mid}（{physical}）のモジュール仕様書に基づき、`apps/reco/src/reco/application/{slug}/**` にモジュール本体を実装する。"

        work_mode: "ai-agent"

        parent:
          epic_issue: "[Epic]{mid}:{physical}"
          epic_issue_number: null
          epic_branch: "feature/epic-<issue-number>-{ws}"
          related_issues: []
          related_prs: []

        commands:
          primary: "/work-issue"
          allowed:
            - "/work-issue"
            - "/create-pr"
            - "/fix-review-comments"
            - "/summarize-work"
          next:
            success: "/create-pr"
            review_fix: "/fix-review-comments"
            blocked: null

        agent:
          primary: "worker-ai"
          support:
            - "orchestrator-ai"
            - "support-ai"
            - "test-ai"
          review:
            - "reviewer-ai"

        background: |
          Epic 配下で {mid} モジュール仕様書 Task 完了後、モジュール本体を `apps/reco/src/reco/application/{slug}/**` に実装する。
          Orchestrator（MOD-RECO-001）のポート契約に適合する実装とし、スタブ差し替えは別 Task または Orchestrator 側 wiring Task で扱う。

        objective: |
          {mid} モジュール本体を実装し、モジュール仕様書の責務・入出力・例外方針を満たす。
          単体テストの網羅的追加は後続 unit-test Task に委譲する。

        scope:
          - "`apps/reco/src/reco/application/{slug}/**` へのモジュール本体実装"
          - "Orchestrator ポート（PipelineModulePort 等）に適合する公開 I/F"
          - "必要最小限の domain / infrastructure 利用（epic_scope 内）"
          - "実装スモークテスト（最小限）"

        out_of_scope:
          - "Orchestrator 本体のスタブ差し替え（別 Task）"
          - "API-INT-002 エンドポイント層"
          - "他 Recoモジュール本体"
          - "OpenAPI / DB schema 変更"
          - "網羅的単体テスト（unit-test Task）"

        input:
          docs:
            - path: "{spec}"
              required: true
              purpose: "実装正本"
            - path: "docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md"
              required: true
              purpose: "ポート契約・呼び出し関係"
            - path: "docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md"
              required: true
              purpose: "モジュール責務境界"
          templates: []
          files:
            - path: "apps/reco/src/reco/application/recommendation-orchestrator/ports.py"
              required: true
              purpose: "下位モジュールポート契約"
          issues: []
          prs: []

        output:
          docs: []
          files:
            - path: "apps/reco/src/reco/application/{slug}/**"
              action: "create"
              required: true
          tests: []
          generated:
            expected: false
            paths: []
            handling: "none"
          logs:
            ai_logs_required: false
            path: null

        deliverables:
          - "{mid} モジュール本体実装"
          - "最小スモークテスト（任意・実装 PR 内）"

        acceptance_criteria:
          - "`apps/reco/src/reco/application/{slug}/**` に実装がある"
          - "モジュール仕様書と矛盾しない"
          - "apps/reco/src/reco/api/** を変更していない"
          - "他 MOD 本体ディレクトリを変更していない"
          - "secret、APIキー、.env 実値が含まれていない"

        branch:
          no_branch: false
          name: "feature/task-<issue-number>-{ws}-implementation"
          base: "feature/epic-<issue-number>-{ws}"
          target: "feature/epic-<issue-number>-{ws}"
          worktree_required: true

        project:
          project_name: "Gift Recommendation Service MVP Cycle 3"
          fields:
            phase: "07_開発・単体テスト"
            status: "Todo"
            priority: "high"

        issue:
          unit: "task"
          type: "feature"
          area: "reco"

        dependencies:
          epics: []
          issues: []
          prs: []
          tasks:
            - "{mid} モジュール仕様書 Task が Human Review 完了していること"
          blocking: true

        parallel_control:
          depends_on:
            - "task-{ws}-module-spec"
          exclusive_files:
            - "{app_path(m)}"
          conflict_risk: "medium"
          contract_impact: false
          generated_impact: false
          db_impact: false

        test_policy:
          required:
            - "typecheck"
            - "unit test（最小スモーク）"
            - "secret check"
          commands:
            - "cd apps/reco && python -m compileall src/reco/application/{slug}"
          not_required:
            - "integration test"
          skip_reason:
            "integration test": "下位モジュール単体のため後続または API-INT 接続後"

        review:
          human_review_required: true
          ai_review_required: true
          review_points:
            - "モジュール仕様書との整合"
            - "Orchestrator ポート契約との整合"
            - "epic_scope 内に差分が収まっているか"
          specialist_reviews:
            docs: false
            test: false
            contract: false
            security: false

        operation_logging:
          level: "standard"

        notes:
          - "Definition bootstrap 由来スキャフォールド。"
          - "workstream: {ws}"
        """
    )


def gen_unit_test(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    slug = m["slug"]
    spec = spec_doc_path(m)
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "task"

        task:
          id: "task-{ws}-unit-test"
          title: "{mid}:{physical}単体テスト"
          summary: "{mid}（{physical}）実装に対し、モジュール仕様書 §14 の unit 観点を満たす単体テストを追加する。"

        work_mode: "ai-agent"

        parent:
          epic_issue: "[Epic]{mid}:{physical}"
          epic_issue_number: null
          epic_branch: "feature/epic-<issue-number>-{ws}"
          related_issues: []
          related_prs: []

        commands:
          primary: "/work-issue"
          allowed:
            - "/work-issue"
            - "/create-pr"
            - "/fix-review-comments"
            - "/summarize-work"
          next:
            success: "/create-pr"
            review_fix: "/fix-review-comments"
            blocked: null

        agent:
          primary: "test-ai"
          support:
            - "worker-ai"
            - "support-ai"
          review:
            - "reviewer-ai"
            - "test-ai"

        background: |
          {mid} 実装 Task 完了後、モジュール仕様書 §14 の unit 観点に沿った pytest テストを整備する。
          本番 DB / 外部 API に依存しない fixture / mock を用いる。

        objective: |
          {mid} の単体テストを整備し、pytest で再現可能な検証を提供する。
          §14 unit 観点とテストケースの対応表を PR に記載する。

        scope:
          - "`apps/reco/tests/unit/application/{slug}/**` または `apps/reco/tests/module/{slug}/**` へのテスト追加"
          - "モジュール仕様書 §14 unit 観点のカバレッジ整理"
          - "テスト用 fixture / mock（モジュール専用）"

        out_of_scope:
          - "integration test / e2e test"
          - "Orchestrator 統合テスト（別 Task）"
          - "モジュール本体の機能追加（テスト成立に必要な最小修正のみ可）"
          - "OpenAPI / DB schema 変更"

        input:
          docs:
            - path: "{spec}"
              required: true
              purpose: "§14 テスト観点の正本"
            - path: "docs/05_アプリケーション設計/アプリ/エラーコード定義書.md"
              required: true
              purpose: "エラー期待値"
          templates: []
          files:
            - path: "apps/reco/src/reco/application/{slug}/**"
              required: true
              purpose: "テスト対象"
          issues: []
          prs: []

        output:
          docs: []
          files: []
          tests:
            - path: "apps/reco/tests/unit/application/{slug}/**"
              action: "create_or_update"
              required: true
          generated:
            expected: false
            paths: []
            handling: "none"
          logs:
            ai_logs_required: false
            path: null

        deliverables:
          - "§14 unit 観点に対応する pytest テストスイート"
          - "観点とテストケースの対応表（PR 本文）"
          - "pytest 実行結果"

        acceptance_criteria:
          - "モジュール仕様書 §14 unit 観点がテストでカバーされている"
          - "`cd apps/reco && python -m pytest tests/unit/ -q` が成功する"
          - "本番 DB / 外部 API / secret に依存していない"
          - "epic_scope 外の変更を含まない"

        branch:
          no_branch: false
          name: "test/task-<issue-number>-{ws}-unit-test"
          base: "feature/epic-<issue-number>-{ws}"
          target: "feature/epic-<issue-number>-{ws}"
          worktree_required: true

        project:
          project_name: "Gift Recommendation Service MVP Cycle 3"
          fields:
            phase: "07_開発・単体テスト"
            status: "Todo"
            priority: "high"

        issue:
          unit: "task"
          type: "test"
          area: "reco"

        dependencies:
          epics: []
          issues: []
          prs: []
          tasks:
            - "{mid} 実装 Task が Epic Branch にマージ済みであること"
          blocking: true

        parallel_control:
          depends_on:
            - "task-{ws}-implementation"
          exclusive_files:
            - "apps/reco/tests/unit/application/{slug}/**"
            - "apps/reco/tests/module/{slug}/**"
          conflict_risk: "low"
          contract_impact: false
          generated_impact: false
          db_impact: false

        test_policy:
          required:
            - "unit test"
            - "pytest"
            - "coverage mapping"
          commands:
            - "cd apps/reco && python -m pytest tests/unit/application/{slug}/ -v --tb=short"
            - "cd apps/reco && python -m pytest tests/unit/ -q --tb=short"
          not_required:
            - "integration test"

        review:
          human_review_required: true
          ai_review_required: true
          review_points:
            - "§14 unit 観点のカバレッジ"
            - "テストの再現性・安定性"
            - "epic_scope 外変更の有無"
          specialist_reviews:
            docs: false
            test: true
            contract: false
            security: false

        operation_logging:
          level: "standard"

        notes:
          - "Definition bootstrap 由来スキャフォールド。"
          - "workstream: {ws}"
        """
    )


def gen_review_epic(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "review"

        review:
          id: "review-{ws}-epic-pr"
          title: "{mid} Epic PRレビュー"
          summary: "{mid}（{physical}）Epic の develop 向け統合 PR を AI Review する"
          type: "epic_pr_review"
          status: "draft"

        work_mode: "ai-agent"

        branch:
          worktree_required: true

        target:
          pr: null
          issue:
            number: null
          task_definition: "prompts/definitions/epics/{ws}/epic.yaml"
          source_branch: "feature/epic-<issue-number>-{ws}"
          target_branch: "develop"

        commands:
          primary: "/review-pr"

        agent:
          primary: "reviewer-ai"
          specialist:
            docs: "docs-reviewer-ai"
            test: "test-ai"

        review_scope:
          docs: true
          project_operation: true
          security: true

        input:
          task_definition:
            path: "prompts/definitions/epics/{ws}/epic.yaml"
            required: true

        review_points:
          - "scope / epic_scope.allowed_paths 整合"
          - "子 Task 3件（module-spec / implementation / unit-test）完了"
          - "apps/reco/src/reco/api/** 非含有"
          - "secret 非含有"

        notes:
          - "Epic Issue / PR 確定後に target.issue.number / target.pr を更新する"
        """
    )


def gen_review_task(m: dict[str, object], task_kind: str, task_file: str, title_suffix: str) -> str:
    ws = workstream(m)
    mid = mod_id(m)
    physical = m["physical"]
    review_id = f"review-{ws}-{task_kind}-pr"
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "review"

        review:
          id: "{review_id}"
          title: "{mid} {title_suffix} PRレビュー"
          summary: "{mid}（{physical}）{title_suffix} Task の PR を AI Review する"
          type: "task_pr_review"
          status: "draft"

        work_mode: "ai-agent"

        branch:
          worktree_required: true

        target:
          pr: null
          issue:
            number: null
          task_definition: "prompts/definitions/tasks/{ws}/{task_file}"
          source_branch: null
          target_branch: "feature/epic-<issue-number>-{ws}"
          parent_epic_issue: null
          parent_epic_branch: "feature/epic-<issue-number>-{ws}"

        commands:
          primary: "/review-pr"

        agent:
          primary: "reviewer-ai"
          specialist:
            docs: "docs-reviewer-ai"
            test: "test-ai"

        review_scope:
          docs: {"true" if task_kind == "module-spec" else "false"}
          source: {"false" if task_kind == "module-spec" else "true"}
          tests: {"true" if task_kind == "unit-test" else "false"}
          project_operation: true
          security: true

        input:
          task_definition:
            path: "prompts/definitions/tasks/{ws}/{task_file}"
            required: true

        review_points:
          - "Task Definition scope / acceptance_criteria 充足"
          - "epic_scope 内に差分が収まっているか"
          - "secret 非含有"

        notes:
          - "Issue / PR 確定後に target.* / input.issue.number / input.pr.number を更新する"
        """
    )


def gen_bootstrap(issue_number: int | None = None) -> str:
    issue_line = f"  number: {issue_number}" if issue_number else "  number: null"
    branch_name = (
        f"chore/task-{issue_number}-mod-reco-002-027-definitions-bootstrap"
        if issue_number
        else "chore/task-<issue-number>-mod-reco-002-027-definitions-bootstrap"
    )
    epic_outputs = "\n".join(
        f'    - path: "prompts/definitions/epics/{workstream(m)}/epic.yaml"\n      action: "create"\n      required: true'
        for m in MODULES
    )
    task_globs = "\n".join(
        f'    - path: "prompts/definitions/tasks/{workstream(m)}/**"\n      action: "create"\n      required: true'
        for m in MODULES
    )
    review_globs = "\n".join(
        f'    - path: "prompts/definitions/reviews/{workstream(m)}/**"\n      action: "create"\n      required: true'
        for m in MODULES
    )
    module_list = ", ".join(mod_id(m) for m in MODULES)
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "task"

        task:
          id: "task-mod-reco-002-027-definitions-bootstrap"
          title: "MOD-RECO-002〜027:RecoモジュールDefinition bootstrap"
          summary: "MOD-RECO-002〜027（24モジュール、024/025/028/029除く）の識別子単位 Epic Definition + 子 Task 3件（module-spec / implementation / unit-test）+ Review Definition を整備し、各 `/start-epic` 前提を満たす bootstrap chore Task。"
          phase: "06_実装設計"

        work_mode: "ai-agent"

        parent:
          epic_id: null
          epic_issue: null
          epic_issue_number: null
          epic_branch: null
          related_issues:
            - number: 260
              purpose: "MOD-RECO-001 Recommendation Orchestrator Epic 完了"
            - number: 698
              purpose: "Phase4a reco-foundation 完了"
          related_prs: []

        commands:
          primary: "/start-task"
          allowed:
            - "/start-task"
            - "/work-issue"
            - "/create-pr"
            - "/fix-review-comments"
            - "/summarize-work"
          next:
            success: "/work-issue"
            review_fix: "/fix-review-comments"
            blocked: null

        agent:
          primary: "worker-ai"
          support:
            - "orchestrator-ai"
            - "support-ai"
          review:
            - "reviewer-ai"
            - "docs-reviewer-ai"

        background: |
          MOD-RECO-001（Epic #260）完了後、残り Reco パイプラインモジュール {module_list} および BT モジュール（026 / 027）を
          識別子単位 Epic として `/start-epic` する前に Definition 一式を prompts/definitions に整備する。
          実装フェーズ実行プロセス設計書 §6.6 / 成果物化方針書 §3.5.2 に整合させる。
          24 Epic は **並列** `/start-epic` 可だが、推奨ウェーブ（0: 002-003 / 1: 004-009 / 2: 010-013 / 3: 014-016 / 4: 017-020 / 5: 021-023 / bt: 026-027）に従い着手する。
          生成スクリプト: scripts/generate_mod_reco_002_027_definitions.py

        objective: |
          MOD-RECO-002〜027 の Epic Definition 24件 + 子 Task Definition 72件 + Review Definition 97件 + 本 bootstrap を作成する。
          merge 後、各 workstream で `/start-epic @prompts/definitions/epics/<workstream>/epic.yaml` へ進める状態にする。

        scope:
          - "Epic Definition 24件（MOD-RECO-002〜027、024/025/028/029 は対象外）"
          - "子 Task Definition 72件（各 Epic × module-spec / implementation / unit-test）"
          - "Review Definition 97件（Epic×24 + Task×72 + bootstrap×1）"
          - "本 bootstrap Task / Review Definition"
          - "生成スクリプト scripts/generate_mod_reco_002_027_definitions.py"

        out_of_scope:
          - "各 MOD-RECO Epic の実装（モジュール仕様書・コード・テスト本体）"
          - "MOD-RECO-024 / 025 / 028 / 029 の Definition（別 bootstrap 候補）"
          - "Orchestrator スタブ差し替え wiring Task"
          - "packages/contracts/** 変更・generated 手編集"
          - "secret 実値の commit"

        input:
          docs:
            - path: "docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md"
              required: true
              purpose: "モジュール名・物理名・分類・処理種別の正本"
            - path: "docs/00_共通/プロジェクト管理/実装フェーズ実行プロセス設計書.md"
              required: true
              purpose: "Phase4b 縦串・並列方針"
            - path: "docs/00_共通/AIエージェント運用/成果物一覧×Task Definition化方針書.md"
              required: true
              purpose: "識別子単位 Epic 方針 §3.5"
            - path: "docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md"
              required: true
              purpose: "ポート契約・処理順序の正本"
          files:
            - path: "prompts/definitions/epics/mod-reco-001-recommendation-orchestrator/epic.yaml"
              required: true
              purpose: "Epic Definition 構造参考"
            - path: "prompts/definitions/tasks/phase4a/phase4a-definitions-bootstrap.yaml"
              required: true
              purpose: "bootstrap Task 構造参考"

        output:
          docs: []
          files:
        {epic_outputs}
        {task_globs}
        {review_globs}
            - path: "prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml"
              action: "create"
              required: true
            - path: "prompts/definitions/reviews/mod-reco-002-027-definitions-bootstrap/pr-review.yaml"
              action: "create"
              required: true
            - path: "scripts/generate_mod_reco_002_027_definitions.py"
              action: "create"
              required: true

        deliverables:
          - "Epic Definition 24件"
          - "子 Task Definition 72件"
          - "Review Definition 97件（Epic/Task Review + bootstrap Review）"
          - "生成スクリプト 1件"
          - "merge 後 各 `/start-epic` 実行可能"

        acceptance_criteria:
          - "MOD-RECO-002〜027 の Epic / Task / Review Definition が存在する"
          - "各 Epic に child_task_areas（module-spec / implementation / unit-test）がある"
          - "epic_scope.forbidden_paths に apps/reco/src/reco/api/** が含まれる"
          - "MOD-RECO-001 epic.yaml 構造と整合（識別子単位 Epic）"
          - "生成スクリプトで再生成可能である"
          - "secret 実値が含まれていない"
          - "Task PR target が develop（親 Epic なし chore）"

        branch:
          no_branch: false
          name: "{branch_name}"
          summary: "mod-reco-002-027-definitions-bootstrap"
          base: "develop"
          target: "develop"
          worktree_required: true

        project:
          project_name: "Gift Recommendation Service MVP Cycle 3"
          fields:
            phase: "06_実装設計"
            status: "Todo"
            priority: "high"

        issue:
        {issue_line}
          unit: "task"
          type: "chore"
          area: "reco"

        dependencies:
          epics: []
          issues:
            - number: 260
              purpose: "MOD-RECO-001 完了"
            - number: 698
              purpose: "reco-foundation 完了"
          blocking: false

        parallel_control:
          exclusive_files:
            - "prompts/definitions/epics/mod-reco-00*/**"
            - "prompts/definitions/epics/mod-reco-01*/**"
            - "prompts/definitions/epics/mod-reco-02*/**"
            - "prompts/definitions/tasks/mod-reco-00*/**"
            - "prompts/definitions/tasks/mod-reco-01*/**"
            - "prompts/definitions/tasks/mod-reco-02*/**"
            - "prompts/definitions/reviews/mod-reco-00*/**"
            - "prompts/definitions/reviews/mod-reco-01*/**"
            - "prompts/definitions/reviews/mod-reco-02*/**"
            - "prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml"
            - "scripts/generate_mod_reco_002_027_definitions.py"
          conflict_risk: "low"
          contract_impact: false
          generated_impact: false
          db_impact: false

        test_policy:
          manual_checks:
            - "Epic 24件 / Task 72件 / Review 97件のファイル数"
            - "各 Epic の epic_scope.allowed_paths 目視"
            - "YAML 必須項目目視"
          not_required:
            - "unit test"
          skip_reason:
            "unit test": "Definition のみ chore"

        review:
          human_review_required: true
          ai_review_required: true
          review_points:
            - "Recoモジュール一覧とのモジュール ID / 物理名整合"
            - "MOD-RECO-001 Definition 構造との整合"
            - "並列ウェーブ注記の妥当性"
            - "024/025/028/029 が scope 外であること"
            - "Review Definition 4点セット（Epic + 3 Task）×24"
          specialist_reviews:
            docs: true
            security: false

        contract_gate:
          required: false

        operation_logging:
          level: "minimal"

        notes:
          - "親 Epic なし・develop 直 Task（bootstrap chore）"
          - "対象: {module_list}"
          - "merge 後: `/start-epic @prompts/definitions/epics/mod-reco-002-recommendation-run-recorder/epic.yaml` 等"
          - "workstream_key: mod-reco-002-027-definitions-bootstrap"
        """
    )


def gen_bootstrap_review(issue_number: int | None = None) -> str:
    branch = (
        f"chore/task-{issue_number}-mod-reco-002-027-definitions-bootstrap"
        if issue_number
        else "chore/task-<issue-number>-mod-reco-002-027-definitions-bootstrap"
    )
    issue_block = f"    number: {issue_number}" if issue_number else "    number: null"
    pr_block = "  pr: null"
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "review"

        review:
          id: "review-mod-reco-002-027-definitions-bootstrap-pr"
          title: "MOD-RECO-002〜027 Definition bootstrap PRレビュー"
          summary: "MOD-RECO-002〜027 Epic/Task/Review Definition 作成 chore PR の AI Review"
          type: "task_pr_review"
          status: "draft"

        work_mode: "ai-agent"

        branch:
          no_branch: false
          name: "{branch}"
          base: "develop"
          target: "develop"
          worktree_required: true

        target:
          {pr_block}
          issue:
        {issue_block}
          task_definition: "prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml"
          source_branch: "{branch}"
          target_branch: "develop"

        commands:
          primary: "/review-pr"

        agent:
          primary: "reviewer-ai"
          specialist:
            docs: "docs-reviewer-ai"

        review_scope:
          docs: false
          project_operation: true
          security: false

        input:
          task_definition:
            path: "prompts/definitions/tasks/mod-reco-002-027-definitions-bootstrap.yaml"
            required: true

        review_points:
          - "Epic 24 / Task 72 / Review 97 のファイル数"
          - "MOD-RECO-001 構造との整合"
          - "024/025/028/029 が含まれていないこと"
          - "生成スクリプトの再現性"

        notes:
          - "PR 作成後に target.pr / input.pr.number を更新"
        """
    )


def main(issue_number: int | None = None) -> None:
    created = 0
    for m in MODULES:
        ws = workstream(m)
        write(PROMPTS / "epics" / ws / "epic.yaml", gen_epic(m))
        created += 1
        write(PROMPTS / "tasks" / ws / "module-spec.yaml", gen_module_spec(m))
        write(PROMPTS / "tasks" / ws / "implementation.yaml", gen_implementation(m))
        write(PROMPTS / "tasks" / ws / "unit-test.yaml", gen_unit_test(m))
        created += 3
        write(PROMPTS / "reviews" / ws / "epic" / "pr-review.yaml", gen_review_epic(m))
        write(
            PROMPTS / "reviews" / ws / "module-spec" / "pr-review.yaml",
            gen_review_task(m, "module-spec", "module-spec.yaml", "モジュール仕様書"),
        )
        write(
            PROMPTS / "reviews" / ws / "implementation" / "pr-review.yaml",
            gen_review_task(m, "implementation", "implementation.yaml", "実装"),
        )
        write(
            PROMPTS / "reviews" / ws / "unit-test" / "pr-review.yaml",
            gen_review_task(m, "unit-test", "unit-test.yaml", "単体テスト"),
        )
        created += 4

    write(
        PROMPTS / "tasks" / "mod-reco-002-027-definitions-bootstrap.yaml",
        gen_bootstrap(issue_number),
    )
    write(
        PROMPTS / "reviews" / "mod-reco-002-027-definitions-bootstrap" / "pr-review.yaml",
        gen_bootstrap_review(issue_number),
    )
    print(f"Generated definitions for {len(MODULES)} modules (+ bootstrap). YAML files touched: {created + 2}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-number", type=int, default=None)
    args = parser.parse_args()
    main(args.issue_number)
