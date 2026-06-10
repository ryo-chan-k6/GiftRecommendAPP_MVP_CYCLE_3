#!/usr/bin/env python3
"""Generate Wave2 Semantic/Feature Rule table-spec Task and Review Definition YAML files."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "prompts/definitions/tasks/db-physical-design"
REVIEW_DIR = ROOT / "prompts/definitions/reviews/db-physical-design"

WAVE2 = [
    {
        "table": "feature_definition",
        "logical": "Feature Definition",
        "summary_extra": "MVP 8 軸 Feature 定義。API-PUB-007 featureDefinitions 表面。",
        "wave_order": 1,
        "partial": False,
        "priority": "high",
        "deps": [462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md", "featureDefinitions Response マッピング"),
        ],
        "feature_section": "§10.3",
        "acceptance_extra": [
            "論理ER §10.2・物理ER §11 chk_feature_code_mvp と矛盾しない",
            "API-PUB-007 featureDefinitions マッピングが明記されている",
            "semantic_config_version_id への FK 方針が明記されている",
        ],
        "human_points": [
            "feature_group（social / symbolic）enum 採用",
            "MVP 8 軸固定と将来拡張の境界",
            "semantic_config_version 単位の UNIQUE（feature_code）",
        ],
        "manual_checks": [
            "物理ER §8–§11 とカラム・CHECK の整合",
            "enum定義書 §6.16 feature_code 8 値との整合",
            "API-PUB-007 featureDefinitions マッピング",
        ],
    },
    {
        "table": "semantic_concept",
        "logical": "Semantic Concept",
        "summary_extra": "Semantic Concept 定義。API-PUB-007 semanticConcepts 表面。",
        "wave_order": 2,
        "partial": False,
        "priority": "high",
        "deps": [462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md", "semanticConcepts Response マッピング"),
            ("docs/04_ドメインモデル設計/SemanticConcept定義書.md", "Concept コード・意味"),
        ],
        "feature_section": "§17.4 前後",
        "acceptance_extra": [
            "semantic_config_version_id への FK 方針が明記されている",
            "API-PUB-007 semanticConcepts マッピングが明記されている",
        ],
        "human_points": [
            "concept_code UNIQUE 単位（version 内）",
            "is_active フィルタと Public API 返却方針",
        ],
        "manual_checks": [
            "論理ER §10.2 semantic_concept 属性との整合",
            "SemanticConcept定義書とのコード整合",
        ],
    },
    {
        "table": "semantic_rule",
        "logical": "Semantic Rule",
        "summary_extra": "入力文→Concept 抽出ルール。Public API 非公開（source_text_pattern）。",
        "wave_order": 3,
        "partial": False,
        "priority": "high",
        "deps": [462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md", "非公開項目（semantic_rule）確認"),
        ],
        "feature_section": "§17 前後",
        "acceptance_extra": [
            "semantic_concept_id への FK 方針が明記されている",
            "Public API 非公開（source_text_pattern / weight）が明記されている",
        ],
        "human_points": [
            "rule_type enum 候補",
            "semantic_concept_id FK 物理 ON 要否",
        ],
        "manual_checks": [
            "論理ER §10.2 semantic_rule 属性との整合",
            "API-PUB-007 非公開項目との整合",
        ],
    },
    {
        "table": "relationship_rule",
        "logical": "Relationship Rule",
        "summary_extra": "Relationship→Feature 基準値。Featureルール定義書 §17.1。",
        "wave_order": 4,
        "partial": False,
        "priority": "high",
        "deps": [442, 462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md", "baseValueRules ruleType=relationship"),
            ("docs/06_実装設計/database/relationship_master_テーブル定義書.md", "relationship_code 参照"),
        ],
        "feature_section": "§17.1",
        "acceptance_extra": [
            "relationship_code の LOGICAL 参照（relationship_master）が明記されている",
            "API-PUB-008 baseValueRules マッピングが明記されている",
        ],
        "human_points": [
            "version 内 (relationship_code, feature_code) UNIQUE",
            "feature_base_value 値域 0.0–1.0 CHECK",
        ],
        "manual_checks": [
            "Featureルール定義書 §17.1 属性との整合",
            "relationship_master コード体系との整合",
        ],
    },
    {
        "table": "occasion_rule",
        "logical": "Occasion Rule",
        "summary_extra": "Occasion→Feature 基準値。Featureルール定義書 §17.2。",
        "wave_order": 5,
        "partial": False,
        "priority": "high",
        "deps": [445, 462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md", "baseValueRules ruleType=occasion"),
            ("docs/06_実装設計/database/occasion_master_テーブル定義書.md", "occasion_code 参照"),
        ],
        "feature_section": "§17.2",
        "acceptance_extra": [
            "occasion_code の LOGICAL 参照（occasion_master）が明記されている",
            "API-PUB-008 baseValueRules マッピングが明記されている",
        ],
        "human_points": [
            "version 内 (occasion_code, feature_code) UNIQUE",
            "feature_base_value 値域 CHECK",
        ],
        "manual_checks": [
            "Featureルール定義書 §17.2 属性との整合",
            "occasion_master コード体系との整合",
        ],
    },
    {
        "table": "pair_rule",
        "logical": "Pair Rule",
        "summary_extra": "Relationship×Occasion Feature 補正。Public API 非公開。",
        "wave_order": 6,
        "partial": False,
        "priority": "high",
        "deps": [449, 462, 463, 442, 445],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md", "pair_rule 非公開確認"),
        ],
        "feature_section": "§17.3",
        "acceptance_extra": [
            "pair_master / relationship_code / occasion_code 参照方針が明記されている",
            "Public API 非公開が明記されている",
        ],
        "human_points": [
            "pair_id vs relationship_code+occasion_code 参照",
            "feature_delta 値域 CHECK",
        ],
        "manual_checks": [
            "Featureルール定義書 §17.3 属性との整合",
            "pair_master merge 後の FK 方針突合",
        ],
    },
    {
        "table": "concept_feature_rule",
        "logical": "Concept Feature Rule",
        "summary_extra": "Concept→Feature 補正。API-PUB-008 conceptFeatureRules 表面。",
        "wave_order": 7,
        "partial": False,
        "priority": "high",
        "deps": [462, 463],
        "extra_input_docs": [
            ("docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md", "conceptFeatureRules マッピング"),
        ],
        "feature_section": "§17.4",
        "acceptance_extra": [
            "concept_code / feature_code 参照方針が明記されている",
            "polarity enum 候補が明記されている",
        ],
        "human_points": [
            "polarity（positive/negative/mixed）enum 正本化タイミング",
            "feature_delta 値域 CHECK",
        ],
        "manual_checks": [
            "Featureルール定義書 §17.4 属性との整合",
            "API-PUB-008 conceptFeatureRules マッピング",
        ],
    },
    {
        "table": "input_type_rule",
        "logical": "Input Type Rule",
        "summary_extra": "入力種別ごとの Feature 適用。MVP partial（テーブル一覧 △）。",
        "wave_order": 8,
        "partial": True,
        "priority": "medium",
        "deps": [462, 463],
        "extra_input_docs": [],
        "feature_section": "§2 Rule 一覧",
        "acceptance_extra": [
            "MVP partial 採用方針が §17 に明記されている",
            "Public API 非公開が明記されている",
        ],
        "human_points": [
            "MVP でテーブル作成するか（物理ER partial）",
            "DDL Task との関係",
        ],
        "manual_checks": [
            "物理ER §8 input_type_rule partial 方針との整合",
        ],
    },
    {
        "table": "feature_integration_rule",
        "logical": "Feature Integration Rule",
        "summary_extra": "複数 Feature 入力統合。MVP partial（テーブル一覧 △）。",
        "wave_order": 9,
        "partial": True,
        "priority": "medium",
        "deps": [462, 463],
        "extra_input_docs": [],
        "feature_section": "§18 統合フロー",
        "acceptance_extra": [
            "MVP partial 採用方針が §17 に明記されている",
            "Public API 非公開が明記されている",
        ],
        "human_points": [
            "MVP でテーブル作成するか（物理ER partial）",
            "integration ロジックと DB 境界",
        ],
        "manual_checks": [
            "物理ER §8 feature_integration_rule partial 方針との整合",
        ],
    },
]


def yaml_list(items, indent=2):
    pad = " " * indent
    return "\n".join(f'{pad}- "{item}"' for item in items)


def yaml_deps(deps):
    lines = []
    for n in deps:
        lines.append(f"    - number: {n}")
        lines.append(f'      purpose: "先行 Task / Wave1 merge 済み前提"')
    return "\n".join(lines)


def yaml_extra_docs(docs):
    if not docs:
        return ""
    lines = []
    for path, purpose in docs:
        lines.append(f"    - path: \"{path}\"")
        lines.append(f"      required: true")
        lines.append(f"      purpose: \"{purpose}\"")
    return "\n".join(lines)


def gen_task(t):
    table = t["table"]
    slug = table.replace("_", "-")
    partial_note = (
        f"  - \"MVP partial テーブル（テーブル一覧 △）。Human Review で MVP 作成要否を確認\""
        if t["partial"]
        else ""
    )
    acceptance = [
        f"{table} テーブル定義書が docs/06_実装設計/database/ に存在する",
        "物理ER §8–§11・論理ER §10.2・テーブル一覧 §8 と矛盾しない",
        "apps/** 変更がない",
        "Task PR target が親 Epic Branch",
    ] + t["acceptance_extra"]

    return f"""schema_version: "1.0"
definition_type: "task"

task:
  id: "task-db-physical-design-table-spec-{slug}"
  title: "{table}:{t['logical']}テーブル定義書作成"
  summary: "物理ER・論理ER・Featureルール定義書・テーブル一覧を入力に、{table} のテーブル定義書を作成する。Phase2 子 Task ③ Wave2（Semantic / Feature Rule 群）No.{t['wave_order']}。"
  phase: "06_実装設計"

work_mode: "ai-agent"

parent:
  epic_id: "epic-db-physical-design"
  epic_issue: "[Epic]db-physical-design:DB物理設計・構築"
  epic_issue_number: 435
  epic_branch: "docs/epic-435-db-physical-design"
  related_issues:
{yaml_deps(t['deps'])}

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
    - "support-ai"
  review:
    - "reviewer-ai"
    - "docs-reviewer-ai"

background: |
  Phase2 子 Task ③ Wave2（Semantic / Feature 定義系 Rule 群）。
  Wave1（semantic_config / semantic_config_version）merge 済み前提。
  推奨着手順: feature_definition → semantic_concept → semantic_rule → relationship_rule / occasion_rule / pair_rule → concept_feature_rule → partial 2 件。

objective: |
  `{table}` の物理カラム・制約・Index・更新仕様を table-spec.md テンプレ準拠で定義する。
  後続 DDL Task が migration を作成できる粒度まで確定する。

scope:
  - "table-spec.md テンプレ準拠の {table} テーブル定義書作成"
  - "物理ER §8–§11・論理ER §10.2・Featureルール定義書 {t['feature_section']} との突合"
  - "Task / Review Definition の整備"

out_of_scope:
  - "他テーブルのテーブル定義書"
  - "DDL・migration（Task ④⑤）"
  - "db/seeds ファイルの作成（Task ⑤）"
  - "apps/** 実装"
  - "OpenAPI / generated 変更（#469 へ委譲）"
{partial_note}

input:
  docs:
    - path: "docs/06_実装設計/database/物理ER.md"
      required: true
      purpose: "テーブル分類・FK・Index・CHECK 方針（§8–§11）"
    - path: "docs/06_実装設計/database/enum定義書.md"
      required: true
      purpose: "enum 参照（feature_code 等）"
    - path: "docs/05_アプリケーション設計/アプリ/database/論理ER.md"
      required: true
      purpose: "§10.2 Semantic / Feature 系エンティティ属性"
    - path: "docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md"
      required: true
      purpose: "§8 Semantic / Feature 定義系"
    - path: "docs/04_ドメインモデル設計/Featureルール定義書.md"
      required: true
      purpose: "Rule 定義 {t['feature_section']}"
{yaml_extra_docs(t['extra_input_docs'])}
  templates:
    - path: "prompts/templates/docs/table-spec.md"
      required: true
      purpose: "成果物テンプレート"

output:
  docs:
    - path: "docs/06_実装設計/database/{table}_テーブル定義書.md"
      action: "create"
      required: true
      template: "prompts/templates/docs/table-spec.md"
  files:
    - path: "prompts/definitions/tasks/db-physical-design/table-spec-{slug}.yaml"
      action: "create"
      required: true
    - path: "prompts/definitions/reviews/db-physical-design/table-spec-{slug}/pr-review.yaml"
      action: "create"
      required: true

acceptance_criteria:
{yaml_list(acceptance, 2)}

branch:
  no_branch: false
  summary: "{slug}-table-spec"
  base: null
  target: null
  worktree_required: true

project:
  fields:
    phase: "06_実装設計"
    status: "Todo"
    priority: "{t['priority']}"

issue:
  unit: "task"
  type: "docs"
  area: "db"

dependencies:
  issues:
    - number: 463
      purpose: "Wave1 semantic_config_version 完了"
  blocking: true

parallel_control:
  exclusive_files:
    - "docs/06_実装設計/database/{table}_テーブル定義書.md"
  conflict_risk: "low"
  db_impact: false

test_policy:
  manual_checks:
{yaml_list(t['manual_checks'], 4)}
  not_required:
    - "unit test"
  skip_reason:
    "unit test": "Phase2 docs 整備 Task のため"

review:
  human_review_required: true
  ai_review_required: true
  specialist_reviews:
    docs: true

notes:
  - "Wave2 着手順 No.{t['wave_order']}"
  - "{t['summary_extra']}"
  - "OpenAPI / generated は Epic 終盤 Task #469 で一括同期"
"""


def gen_review(t):
    table = t["table"]
    slug = table.replace("_", "-")
    return f"""schema_version: "1.0"
definition_type: "review"

review:
  id: "review-db-physical-design-table-spec-{slug}-pr"
  title: "{table} テーブル定義書 PRレビュー"
  summary: "{table} テーブル定義書 Task の PR を AI Review する。物理ER・論理ER・Featureルール定義書との整合と table-spec テンプレ準拠を確認する。"
  type: "task_pr_review"
  status: "ready"

work_mode: "ai-agent"

branch:
  no_branch: false
  name: "docs/task-XXX-{slug}-table-spec"
  base: "docs/epic-435-db-physical-design"
  target: "docs/epic-435-db-physical-design"
  worktree_required: true

target:
  pr: null
  issue: null
  task_definition: "prompts/definitions/tasks/db-physical-design/table-spec-{slug}.yaml"
  source_branch: "docs/task-XXX-{slug}-table-spec"
  target_branch: "docs/epic-435-db-physical-design"
  parent_epic_issue: "[Epic]db-physical-design:DB物理設計・構築"
  parent_epic_branch: "docs/epic-435-db-physical-design"

commands:
  primary: "/review-pr"
  allowed:
    - "/review-pr"
    - "/fix-review-comments"
    - "/summarize-work"
  next:
    approve_for_human_review: "Human Review"
    request_changes: "/fix-review-comments"
    needs_human_decision: "Human Decision"
    split_required: "/start-task"
    blocked: null

agent:
  primary: "reviewer-ai"
  support:
    - "support-ai"
  specialist:
    docs: "docs-reviewer-ai"
    test: null
    contract: null
    security: null
  next:
    fixer: "fixer-ai"
    human: "human-reviewer"

review_scope:
  docs: true
  source: false
  tests: false
  api_contract: false
  db: true
  generated: false
  cicd: false
  security: true
  project_operation: true

input:
  task_definition:
    path: "prompts/definitions/tasks/db-physical-design/table-spec-{slug}.yaml"
    required: true
  issue:
    number: null
    required: true
  pr:
    number: null
    required: true
  diff:
    required: true
    compare_with: "docs/epic-435-db-physical-design"
  docs:
    - path: "docs/06_実装設計/database/{table}_テーブル定義書.md"
      required: true
      purpose: "作成成果物の内容確認"
    - path: "docs/06_実装設計/database/物理ER.md"
      required: true
      purpose: "§8–§11 整合"
    - path: "docs/05_アプリケーション設計/アプリ/database/論理ER.md"
      required: true
      purpose: "§10.2 整合"
    - path: "docs/04_ドメインモデル設計/Featureルール定義書.md"
      required: true
      purpose: "{t['feature_section']}"
  test_results:
    required: true
    source: "pr_body"
  ci_results:
    required: false
    source: "not_required"

review_points:
  common:
    - "Task Definition scope を満たしているか"
    - "OpenAPI / generated が含まれていないか（#469 委譲）"
    - "acceptance_criteria を満たしているか"
  docs:
    - "table-spec.md テンプレ主要章が充足しているか"
    - "論理ER §10.2 属性と矛盾しないか"
    - "Public API 公開/非公開方針が明記されているか"
  db:
    - "PK / Index / CHECK が DDL Task へ展開できる粒度か"
    - "semantic_config_version_id FK 方針が明記されているか"

acceptance_criteria:
  review_outputs:
    - "AI Review 結論"
    - "Blocker / Must / Should / Question の整理"
    - "Human Review 観点の明示"

human_decision_points:
{yaml_list(t['human_points'], 2)}

notes:
  - "Wave2 No.{t['wave_order']}: {table}"
"""


def main():
    for t in WAVE2:
        slug = t["table"].replace("_", "-")
        task_path = TASK_DIR / f"table-spec-{slug}.yaml"
        review_path = REVIEW_DIR / f"table-spec-{slug}" / "pr-review.yaml"
        task_path.write_text(gen_task(t), encoding="utf-8")
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(gen_review(t), encoding="utf-8")
        print(f"generated: {task_path.relative_to(ROOT)}")
        print(f"generated: {review_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
