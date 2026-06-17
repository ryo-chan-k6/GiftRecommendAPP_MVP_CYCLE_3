#!/usr/bin/env python3
"""Epic #435 Phase2 終盤横断整合チェック（Task #633 用）。

事実ベースの機械チェック。結果は stdout に JSON 風サマリを出力する。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PHASE2_DOCS = {
    "物理ER": ROOT / "docs/06_実装設計/database/物理ER.md",
    "enum定義書": ROOT / "docs/06_実装設計/database/enum定義書.md",
    "コード定義書": ROOT / "docs/06_実装設計/database/コード定義書.md",
    "マイグレーション方針書": ROOT / "docs/06_実装設計/database/マイグレーション方針書.md",
    "初期データ定義書": ROOT / "docs/06_実装設計/database/初期データ定義書.md",
    "データ保持・削除方針書": ROOT / "docs/06_実装設計/database/データ保持・削除方針書.md",
    "DDLバッチ分割表": ROOT / "docs/06_実装設計/database/DDLバッチ分割表.md",
}

DDL_BATCHES = [
    "d01_extensions_and_enums.sql",
    "d02_semantic_feature_definitions.sql",
    "d03_master_config.sql",
    "d04_item.sql",
    "d05_external_product_integration.sql",
    "d06_item_derived.sql",
    "d07_online_recommendation.sql",
    "d08_user_meaning.sql",
    "d09_evaluation.sql",
    "d10_log_observability.sql",
    "d11_metric.sql",
    "d12_deferred_fk_indexes.sql",
    "d13_ddl_cross_check.sql",
]

MASTER_SEEDS = [
    "01_relationship_occasion_master.sql",
    "02_pair_master.sql",
    "03_semantic_config.sql",
    "04_feature_definition.sql",
    "05_semantic_concept.sql",
    "06_relationship_rule.sql",
    "07_occasion_rule.sql",
    "08_pair_rule.sql",
    "09_config_versions.sql",
]

PLACEHOLDER_RETENTION = ROOT / "docs/06_実装設計/database/（未作成）データ保持・削除方針書.md"


def table_spec_files() -> list[Path]:
    return sorted((ROOT / "docs/06_実装設計/database").glob("*_テーブル定義書.md"))


def migration_files() -> list[Path]:
    return sorted((ROOT / "supabase/migrations").glob("*.sql"))


def extract_tables_from_ddl() -> set[str]:
    tables: set[str] = set()
    ddl_dir = ROOT / "db/ddl"
    for name in DDL_BATCHES:
        if name == "d13_ddl_cross_check.sql":
            continue
        path = ddl_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r"CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)", text, re.I):
            tables.add(m.group(1))
    return tables


def extract_tables_from_migration() -> set[str]:
    migrations = migration_files()
    if not migrations:
        return set()
    text = migrations[0].read_text(encoding="utf-8")
    tables: set[str] = set()
    for m in re.finditer(r"CREATE TABLE(?: IF NOT EXISTS)?\s+(\w+)", text, re.I):
        tables.add(m.group(1))
    return tables


def main() -> int:
    findings: list[dict] = []
    blockers = 0
    musts = 0

    # Phase2 docs existence
    for label, path in PHASE2_DOCS.items():
        if not path.exists() or path.stat().st_size < 100:
            findings.append(
                {
                    "severity": "Blocker",
                    "category": "phase2_doc",
                    "fact": f"{label} が存在しないか空: {path.relative_to(ROOT)}",
                }
            )
            blockers += 1

    # Table specs count
    specs = table_spec_files()
    if len(specs) != 62:
        findings.append(
            {
                "severity": "Blocker",
                "category": "table_spec_count",
                "fact": f"テーブル定義書件数が 62 ではない: {len(specs)}",
            }
        )
        blockers += 1

    # DDL batches
    ddl_dir = ROOT / "db/ddl"
    for name in DDL_BATCHES:
        p = ddl_dir / name
        if not p.exists():
            findings.append(
                {
                    "severity": "Blocker",
                    "category": "ddl_missing",
                    "fact": f"DDL 欠落: db/ddl/{name}",
                }
            )
            blockers += 1

    # Migration
    migs = migration_files()
    if not migs:
        findings.append(
            {
                "severity": "Blocker",
                "category": "migration_missing",
                "fact": "supabase/migrations/*.sql が存在しない",
            }
        )
        blockers += 1

    # Master seeds
    seed_dir = ROOT / "db/seeds/masters"
    for name in MASTER_SEEDS:
        if not (seed_dir / name).exists():
            findings.append(
                {
                    "severity": "Blocker",
                    "category": "seed_missing",
                    "fact": f"master seed 欠落: db/seeds/masters/{name}",
                }
            )
            blockers += 1

    # Placeholder vs created retention doc
    retention = PHASE2_DOCS["データ保持・削除方針書"]
    if PLACEHOLDER_RETENTION.exists():
        size = PLACEHOLDER_RETENTION.stat().st_size
        if retention.exists() and size == 0:
            findings.append(
                {
                    "severity": "Must",
                    "category": "placeholder_stale",
                    "fact": "（未作成）データ保持・削除方針書.md が空のまま残存（作成済み正本と重複）",
                }
            )
            musts += 1
        elif retention.exists() and size > 0:
            findings.append(
                {
                    "severity": "Must",
                    "category": "placeholder_stale",
                    "fact": "（未作成）データ保持・削除方針書.md が非空で残存",
                }
            )
            musts += 1

    # DDL vs migration table count
    ddl_tables = extract_tables_from_ddl()
    mig_tables = extract_tables_from_migration()
    if ddl_tables and mig_tables and ddl_tables != mig_tables:
        only_ddl = sorted(ddl_tables - mig_tables)
        only_mig = sorted(mig_tables - ddl_tables)
        findings.append(
            {
                "severity": "Blocker",
                "category": "ddl_migration_mismatch",
                "fact": "db/ddl と supabase/migrations の CREATE TABLE 集合が不一致",
                "only_in_ddl": only_ddl[:20],
                "only_in_migration": only_mig[:20],
                "ddl_count": len(ddl_tables),
                "migration_count": len(mig_tables),
            }
        )
        blockers += 1

    # 成果物一覧 §4.1 stale markers
    artifacts = ROOT / "docs/00_共通/成果物管理/成果物一覧.md"
    if artifacts.exists():
        section = artifacts.read_text(encoding="utf-8")
        if "## 4.1 db-physical-design" in section:
            part = section.split("## 4.1 db-physical-design", 1)[1].split("## 5.", 1)[0]
            stale_rows = []
            for row_label in ("DDL", "初期データ定義書", "マイグレーション方針書", "データ保持・削除方針書"):
                if f"| {row_label} | 未作成 |" in part:
                    stale_rows.append(row_label)
            if stale_rows:
                findings.append(
                    {
                        "severity": "Must",
                        "category": "artifacts_list_stale",
                        "fact": f"成果物一覧 §4.1 で未作成のまま: {', '.join(stale_rows)}",
                    }
                )
                musts += 1

    summary = {
        "blockers": blockers,
        "musts": musts,
        "table_spec_count": len(specs),
        "ddl_table_count": len(ddl_tables),
        "migration_table_count": len(mig_tables),
        "migration_files": [p.name for p in migs],
        "findings": findings,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if blockers > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
