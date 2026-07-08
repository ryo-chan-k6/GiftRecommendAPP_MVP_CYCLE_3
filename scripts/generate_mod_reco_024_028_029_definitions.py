#!/usr/bin/env python3
"""Generate Epic/Task/Review Definition scaffolds for MOD-RECO-024 / 028 / 029."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "prompts" / "definitions"

# Recommended start order: 024 → 029 → 028 (024→029 collaboration first).
MODULES: list[dict[str, object]] = [
    {
        "id": "024",
        "name_ja": "Reco Error処理",
        "physical": "Reco Error Handler",
        "category": "ログ・観測",
        "ptype": "OL",
        "mvp": True,
        "slug": "reco-error-handler",
        "wave": "log-1",
        "start_order": 1,
        "extra_docs": [
            "docs/05_アプリケーション設計/アプリ/エラーコード定義書.md",
            "docs/06_実装設計/database/error_log_テーブル定義書.md",
        ],
        "domain_docs": [],
        "orchestrator_relation": "Orchestrator から直接呼び出し。例外を GRS-REC-* へ標準化し、MOD-RECO-029 Error Log Writer へ記録を委譲する。",
    },
    {
        "id": "029",
        "name_ja": "Error Log記録",
        "physical": "Error Log Writer",
        "category": "ログ・観測",
        "ptype": "共通",
        "mvp": True,
        "slug": "error-log-writer",
        "wave": "log-2",
        "start_order": 2,
        "extra_docs": [
            "docs/06_実装設計/database/error_log_テーブル定義書.md",
        ],
        "domain_docs": [],
        "orchestrator_relation": "MOD-RECO-024 Reco Error Handler 経由の間接呼び出しが原則。error_log 永続化を担う。",
        "depends_on_epic": "mod-reco-024-reco-error-handler",
    },
    {
        "id": "028",
        "name_ja": "Phase Log記録",
        "physical": "Phase Log Writer",
        "category": "ログ・観測",
        "ptype": "共通",
        "mvp": True,
        "slug": "phase-log-writer",
        "wave": "log-3",
        "start_order": 3,
        "extra_docs": [
            "docs/06_実装設計/database/phase_log_テーブル定義書.md",
        ],
        "domain_docs": [],
        "orchestrator_relation": "Orchestrator から各フェーズ境界で直接呼び出し。phase_log 永続化を担う（029 より独立）。",
    },
]

ALL_RECO_SLUGS: list[str] = [
    "recommendation-run-recorder",
    "config-version-resolver",
    "user-semantic-extractor",
    "external-condition-feature-estimator",
    "internal-condition-feature-estimator",
    "user-feature-generator",
    "user-meaning-projector",
    "user-context-builder",
    "query-embedding-generator",
    "pre-hard-filter-executor",
    "candidate-retriever",
    "post-hard-filter-executor",
    "feature-matcher",
    "meaning-match-aggregator",
    "context-scorer",
    "popularity-scorer",
    "risk-scorer",
    "final-score-calculator",
    "final-ranker",
    "recommendation-result-builder",
    "result-snapshot-builder",
    "reason-generator",
    "reco-error-handler",
    "metric-logger",
    "phase-log-writer",
    "error-log-writer",
    "item-semantic-generator",
    "item-feature-generator",
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
    lines: list[str] = []
    for index, p in enumerate(paths):
        req = "true" if p in COMMON_DOCS[:4] or "Recoモジュール一覧" in p else "false"
        item_indent = "    " if index == 0 else "            "
        field_indent = "              "
        lines.append(f'{item_indent}- path: "{p}"')
        lines.append(f"{field_indent}required: {req}")
        lines.append(f'{field_indent}purpose: "{purpose}"')
    return "\n".join(lines)


def output_file_entries(paths: list[str], *, first_row_embedded: bool = True) -> str:
    lines: list[str] = []
    for index, path in enumerate(paths):
        item_indent = "    " if first_row_embedded and index == 0 else "            "
        field_indent = "              "
        lines.append(f'{item_indent}- path: "{path}"')
        lines.append(f'{field_indent}action: "create"')
        lines.append(f'{field_indent}required: true')
    return "\n".join(lines)


def sibling_forbidden_paths(m: dict[str, object]) -> str:
    slug = m["slug"]
    paths = ["apps/reco/src/reco/application/recommendation-orchestrator/**"]
    for other in ALL_RECO_SLUGS:
        if other != slug:
            paths.append(f"apps/reco/src/reco/application/{other}/**")
    paths.extend(["apps/reco/src/modules/**", "apps/reco/src/app/**"])
    lines: list[str] = []
    for index, path in enumerate(paths):
        indent = "    " if index == 0 else "            "
        lines.append(f'{indent}- "{path}"')
    return "\n".join(lines)


def epic_depends_on_block(m: dict[str, object]) -> str:
    if m.get("depends_on_epic"):
        return '          depends_on:\n            - "epic-mod-reco-024-reco-error-handler"'
    return "          depends_on: []"


def epic_collab_note(m: dict[str, object]) -> str:
    if m["id"] == "024":
        return '          - "024→029 連携: 標準化エラー生成後、Error Log Writer（MOD-RECO-029）へ記録を委譲する。"'
    if m["id"] == "029":
        return '          - "024→029 連携: MOD-RECO-024 実装・Epic 完了後に着手する（間接呼び出しが原則）。"'
    if m["id"] == "028":
        return '          - "028 は Orchestrator 直接呼び出しで 029 より独立。029 完了を必須としない。"'
    return ""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def validate_yaml_files(paths: list[Path]) -> None:
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            yaml.safe_load(fh)


def gen_epic(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    name_ja = m["name_ja"]
    category = m["category"]
    ptype = m["ptype"]
    slug = m["slug"]
    depends_on = epic_depends_on_block(m)
    dep_issue_block = ""
    if m.get("depends_on_epic"):
        dep_issue_block = (
            "\n            - number: null\n"
            '              purpose: "MOD-RECO-024 Reco Error Handler Epic 完了（024→029 連携の前提）"'
        )
    collab_note = epic_collab_note(m)
    collab_note_line = f"\n{collab_note}" if collab_note else ""
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
          本モジュールは Recoモジュール一覧 §4 / §6.23 の {category} 分類モジュール（処理種別: {ptype}、MVP対象 ○）である。
          MOD-RECO-001 Recommendation Orchestrator から `ExecutionContext` 経由で呼び出される。
          {m["orchestrator_relation"]}
          本 Epic は **Recoモジュール本体**（`apps/reco/src/reco/application/{slug}/**`）に限定し、エンドポイント層（`apps/reco/src/reco/api/**`）は [Epic]API-INT-002 配下とする。
          並列着手ウェーブ目安: {m["wave"]}（bootstrap Issue #1011 参照。推奨着手順 {m["start_order"]}: 024 → 029 → 028）。

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
          - "MOD-RECO-025 Metric Logger（MVP △・別 Task 化）"
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
            {dep_issue_block}
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
          - "Branch base / PR target が develop である"
          - "子 Task の PR target が親 Epic Branch である方針が明記されている"
          - "epic_scope.allowed_paths が apps/reco/src/reco/application/** 等のモジュール層と整合している（成果物化方針書 §3.5.2）"
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
            - "apps/reco/src/reco/domain/**"
            - "apps/reco/src/reco/pipeline/**"
            - "apps/reco/tests/unit/application/{slug}/**"
            - "apps/reco/tests/module/{slug}/**"
            - "prompts/definitions/tasks/{ws}/**"
            - "prompts/definitions/reviews/{ws}/**"
          forbidden_paths:
            - "apps/reco/src/reco/api/**"
        {sibling_forbidden_paths(m)}
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
{depends_on}
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
            - "MOD-RECO-001 §8.4 / §14 との Port・委譲関係整合"
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
          - "Orchestrator スタブ差し替えタイミングとの整合（§8.4.2）"
          - "024→029 連携の I/F 確定（{mid}）"
          - "domain/** / infrastructure/** への横断変更が必要になった場合の別 Task 化"

        human_decision_points:
          - "物理配置パス（application/{slug}/** vs pipeline/**）の採用可否"
          - "並列ウェーブ {m['wave']}（着手順 {m['start_order']}）での着手タイミング"

        stop_conditions:
          - "必須 input.docs が存在しない場合"
          - "Recoモジュール一覧 §6.23 に {mid} が存在しない場合"
          - "epic_scope.allowed_paths が空または未記載の場合"
          - "apps/reco/src/reco/api 配下への変更を本 Epic 配下 Task で実施する必要が出た場合"

        notes:
          - "Epic は作業管理単位。成果物正本は子 Task で作成する。"
          - "命名の正本は Task Definition設計書 §15.0・§15.1。"
          - "子 Task: prompts/definitions/tasks/{ws}/module-spec.yaml"
          - "MOD-* Epic は原則 dependencies.epics なし（成果物化方針書 §3.5.3）。#260 は関連 Issue として記載。"
          - "{m["orchestrator_relation"]}"
          - "Recoモジュール一覧 §6.23 正本。推奨着手順: 024 → 029 → 028（bootstrap #1011）。"{collab_note_line}
          - "MOD-RECO-025 Metric Logger は本 bootstrap の scope 外（MVP △・別 Task 化）。"
          - "bootstrap: prompts/definitions/tasks/mod-reco-024-028-029-definitions-bootstrap.yaml"
        """
    )


def gen_module_spec(m: dict[str, object]) -> str:
    mid = mod_id(m)
    ws = workstream(m)
    physical = m["physical"]
    name_ja = m["name_ja"]
    spec = spec_doc_path(m)
    docs = list(dict.fromkeys([*COMMON_DOCS, *m["extra_docs"], *m["domain_docs"]]))
    extra_scope = ""
    if m["id"] == "024":
        extra_scope = (
            '- "GRS-REC-* 標準化エラーへの変換方針・Error Log Writer（MOD-RECO-029）への委譲を整理する"'
        )
    elif m["id"] == "029":
        extra_scope = '- "MOD-RECO-024 から受け取る error_log 入力 I/F を整理する"'
    elif m["id"] == "028":
        extra_scope = '- "Orchestrator 各フェーズ境界からの phase_log 記録 I/F を整理する"'
    return dedent(
        f"""\
        schema_version: "1.0"
        definition_type: "task"

        task:
          id: "task-{ws}-module-spec"
          title: "{mid}:{physical}モジュール仕様書作成"
          summary: "{mid}（{physical} / {name_ja}）のモジュール仕様書（{spec}）を、Recoモジュール一覧 §6.23 および関連ドメイン定義書に基づいて作成する。"

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
          {m["orchestrator_relation"]}
          MOD-RECO-001 Orchestrator 仕様書 §8.4 / §14 のポート契約（`ExecutionContext` 入出力）と整合させる。

        objective: |
          {mid} について、apps/reco 実装・単体テスト・レビューが可能な粒度のモジュール仕様書を作成する。
          作成する仕様書は prompts/templates/docs/module-spec.md に準拠する。

        scope:
          - "{mid} のモジュール仕様書を新規作成する"
          - "モジュール基本情報・主責務・対象外責務・入出力・処理フロー・例外・ログ・テスト観点を整理する"
          - "Orchestrator（MOD-RECO-001）との呼び出し関係・失敗時の扱いを整理する"
          {extra_scope}

        out_of_scope:
          - "他 Recoモジュール本体のモジュール仕様書作成"
          - "MOD-RECO-025 Metric Logger"
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
          - "Recoモジュール一覧 §6.23 の {mid} と矛盾しない"
          - "MOD-RECO-001 §8.4 / §14 との Port・委譲関係が明確である"
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
            - "Recoモジュール一覧 §6.23 との整合"
            - "MOD-RECO-001 §8.4 / §14 との Port・委譲関係整合"
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
    if m.get("depends_on_epic"):
        dep_tasks_block = (
            '            - "MOD-RECO-024 実装 Task が Epic Branch にマージ済みであること（024→029 連携）"\n'
            f'            - "{mid} モジュール仕様書 Task が Human Review 完了していること"'
        )
        parallel_dep_block = (
            "          depends_on:\n"
            '            - "task-mod-reco-024-reco-error-handler-implementation"\n'
            '            - "task-mod-reco-029-error-log-writer-module-spec"'
        )
    else:
        dep_tasks_block = f'            - "{mid} モジュール仕様書 Task が Human Review 完了していること"'
        parallel_dep_block = (
            "          depends_on:\n"
            f'            - "task-{ws}-module-spec"'
        )
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
          {m["orchestrator_relation"]}
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
          - "MOD-RECO-025 Metric Logger"
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
{dep_tasks_block}
          blocking: true

        parallel_control:
{parallel_dep_block}
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
            - "MOD-RECO-001 §8.4 ポート契約との整合"
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
    extra_review = ""
    if m["id"] == "024":
        extra_review = '- "024→029 連携のテスト観点（Error Log 委譲）"'
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
            {extra_review}
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
    extra = ""
    if m["id"] == "029":
        extra = '- "024→029 連携が Epic / Task Definition に反映されていること"'
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
          - "MOD-RECO-001 §8.4 / §14 との Port・委譲関係整合"
          - "apps/reco/src/reco/api/** 非含有"
          - "secret 非含有"
          {extra}

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


def main(issue_number: int | None = None, pr_number: int | None = None, *, skip_bootstrap: bool = False) -> None:
    created = 0
    touched: list[Path] = []
    for m in MODULES:
        ws = workstream(m)
        epic_path = PROMPTS / "epics" / ws / "epic.yaml"
        write(epic_path, gen_epic(m))
        touched.append(epic_path)
        created += 1
        for name, gen in (
            ("module-spec.yaml", gen_module_spec),
            ("implementation.yaml", gen_implementation),
            ("unit-test.yaml", gen_unit_test),
        ):
            task_path = PROMPTS / "tasks" / ws / name
            write(task_path, gen(m))
            touched.append(task_path)
            created += 1
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
        touched.extend(
            [
                PROMPTS / "reviews" / ws / "epic" / "pr-review.yaml",
                PROMPTS / "reviews" / ws / "module-spec" / "pr-review.yaml",
                PROMPTS / "reviews" / ws / "implementation" / "pr-review.yaml",
                PROMPTS / "reviews" / ws / "unit-test" / "pr-review.yaml",
            ]
        )
        created += 4

    if not skip_bootstrap:
        bootstrap_review_path = (
            PROMPTS / "reviews" / "mod-reco-024-028-029-definitions-bootstrap" / "pr-review.yaml"
        )
        if bootstrap_review_path.exists():
            touched.append(bootstrap_review_path)

    validate_yaml_files(touched)
    print(
        f"Generated definitions for {len(MODULES)} modules. "
        f"YAML files touched: {created} (+ bootstrap review preserved)"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-number", type=int, default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--skip-bootstrap", action="store_true")
    args = parser.parse_args()
    main(args.issue_number, args.pr_number, skip_bootstrap=args.skip_bootstrap)
