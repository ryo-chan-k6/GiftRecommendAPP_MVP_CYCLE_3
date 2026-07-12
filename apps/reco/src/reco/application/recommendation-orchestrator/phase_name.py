"""Orchestrator 集約 phase_name 正規化（Observability §10.3 / recommendation_run_phase_name 14 値）。"""

from __future__ import annotations

# packages/code-definitions/batch/recommendation_run_phase_name.yaml / 028 constants と一致
ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES = frozenset(
    {
        "request_received",
        "config_resolved",
        "semantic_extracted",
        "user_feature_generated",
        "user_meaning_projected",
        "query_embedding_generated",
        "pre_hard_filter_completed",
        "retrieval_completed",
        "post_hard_filter_completed",
        "matching_completed",
        "ranking_completed",
        "result_generated",
        "reason_generated",
        "response_built",
    }
)

# module_id → 028 へ渡す集約 phase_name。None は Orchestrator から record_phase しない。
MODULE_AGGREGATED_PHASE_NAME: dict[str, str | None] = {
    "MOD-RECO-002": None,
    "MOD-RECO-003": "config_resolved",
    "MOD-RECO-004": "semantic_extracted",
    "MOD-RECO-005": None,
    "MOD-RECO-006": None,
    "MOD-RECO-007": "user_feature_generated",
    "MOD-RECO-008": "user_meaning_projected",
    "MOD-RECO-009": "user_meaning_projected",
    "MOD-RECO-010": "query_embedding_generated",
    "MOD-RECO-012": "retrieval_completed",
    "MOD-RECO-013": "post_hard_filter_completed",
    "MOD-RECO-014": None,
    "MOD-RECO-015": None,
    "MOD-RECO-016": "matching_completed",
    "MOD-RECO-017": None,
    "MOD-RECO-018": None,
    "MOD-RECO-019": None,
    "MOD-RECO-020": "ranking_completed",
    "MOD-RECO-021": "result_generated",
    "MOD-RECO-022": None,
    "MOD-RECO-023": "reason_generated",
}

# 下位モジュール内部名称 → 14 集約名（module_id 不明時のフォールバック）
RAW_PHASE_NAME_TO_AGGREGATED: dict[str, str] = {
    "run_recorded": "request_received",
    "pipeline_failed": "response_built",
    "pipeline_control": "response_built",
    "external_feature_estimated": "user_feature_generated",
    "internal_feature_estimated": "user_feature_generated",
    "user_context_built": "user_meaning_projected",
    "feature_matched": "matching_completed",
    "meaning_match_aggregated": "matching_completed",
    "context_scored": "matching_completed",
    "popularity_scored": "ranking_completed",
    "risk_scored": "ranking_completed",
    "final_score_calculated": "ranking_completed",
    "ranked": "ranking_completed",
    "final_ranked": "ranking_completed",
    "result_built": "result_generated",
    "snapshot_built": "result_generated",
    "post_hard_filtered": "post_hard_filter_completed",
}

MATCHING_PHASE_MODULE_IDS: frozenset[str] = frozenset(
    {"MOD-RECO-014", "MOD-RECO-015", "MOD-RECO-016"}
)
RANKING_PHASE_MODULE_IDS: frozenset[str] = frozenset(
    {"MOD-RECO-017", "MOD-RECO-018", "MOD-RECO-019", "MOD-RECO-020"}
)


def resolve_aggregated_phase_name(
    module_id: str,
    raw_phase_name: str,
    *,
    matching_short_circuit: bool = False,
) -> str | None:
    """module_id と下位名称から 028 へ渡す集約 phase_name を解決する。

    None を返した場合、Orchestrator は当該 module 実行に対する record_phase を行わない。
    matching_short_circuit が True のとき MOD-RECO-014 完了時点で matching_completed を記録する。
    """
    if module_id == "MOD-RECO-014" and matching_short_circuit:
        return "matching_completed"

    if module_id in MODULE_AGGREGATED_PHASE_NAME:
        return MODULE_AGGREGATED_PHASE_NAME[module_id]

    if raw_phase_name in ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES:
        return raw_phase_name

    return RAW_PHASE_NAME_TO_AGGREGATED.get(raw_phase_name)


def normalize_orchestrator_phase_name(
    module_id: str | None,
    raw_phase_name: str | None,
) -> str:
    """error_handler / 例外経路向けに、必ず enum 妥当な phase_name を返す。"""
    if module_id is not None:
        resolved = resolve_aggregated_phase_name(module_id, raw_phase_name or "")
        if resolved is not None:
            return resolved

    if raw_phase_name in ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES:
        return raw_phase_name

    if raw_phase_name is not None:
        mapped = RAW_PHASE_NAME_TO_AGGREGATED.get(raw_phase_name)
        if mapped is not None:
            return mapped

    return "response_built"
