"""Reason generation engine for MOD-RECO-023."""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import uuid4

from reco.application.feature_matcher.models import FeatureMatchEntry, FeatureMatchResult
from reco.application.meaning_match_aggregator.models import MeaningMatchEntry, MeaningMatchResult
from reco.application.recommendation_orchestrator.ports import ReasonGenerationOutcome
from reco.application.risk_scorer.models import RiskPenaltyEntry, RiskPenaltyResult
from reco.domain.recommendation.request import RecommendationRequest
from reco.infrastructure.external_ai.client import ExternalAiClient

from .constants import (
    AVOID_SIMILARITY_CAUTION_THRESHOLD,
    DEFAULT_OCCASION_LABEL,
    DEFAULT_RELATIONSHIP_LABEL,
    DEFAULT_TEMPLATE_NAME,
    DEFAULT_TEMPLATE_VERSION,
    FEATURE_BADGE_MAP,
    FORBIDDEN_EXPRESSIONS,
    GENERATION_METHOD_INTERNAL_FALLBACK,
    GENERATION_METHOD_TEMPLATE,
    GENERIC_REASON_SUMMARY,
    IMPORTANT_FEATURES_FOR_WEAK_MATCH,
    LLM_REFINEMENT_ENV,
    RISK_PENALTY_CAUTION_THRESHOLD,
    SOCIAL_MATCH_CAUTION_THRESHOLD,
    STRONG_MATCH_THRESHOLD,
    WEAK_MATCH_MAX,
    WEAK_MATCH_MIN,
)
from .models import (
    GeneratedReason,
    ItemSemanticRecord,
    ReasonGeneratorInput,
    ReasonGeneratorInputItem,
    ReasonGeneratorRunMetrics,
    ReasonTemplateRecord,
    RecommendationReasonInsertRow,
    SelectedFeature,
    SemanticEvidence,
)
from .ports import (
    ItemSemanticReadPort,
    ReasonTemplateReadPort,
    RecommendationReasonRepositoryPort,
)


def generate_reasons_for_run(
    reason_input: ReasonGeneratorInput,
    *,
    recommendation_request: RecommendationRequest,
    feature_match_result: FeatureMatchResult | None,
    meaning_match_result: MeaningMatchResult | None,
    risk_penalty_result: RiskPenaltyResult | None,
    semantic_records: dict[str, ItemSemanticRecord],
    template_reader: ReasonTemplateReadPort,
    reason_repository: RecommendationReasonRepositoryPort,
    llm_client: ExternalAiClient | None = None,
) -> tuple[tuple[GeneratedReason, ...], ReasonGeneratorRunMetrics]:
    """全 Item の Reason を生成し INSERT する。"""
    relationship_code, relationship_label = _resolve_relationship(recommendation_request)
    occasion_code, occasion_label = _resolve_occasion(recommendation_request)

    feature_by_item = _index_feature_matches(feature_match_result)
    meaning_by_item = _index_meaning_matches(meaning_match_result)
    risk_by_item = _index_risk_penalties(risk_penalty_result)

    llm_enabled = _is_llm_refinement_enabled()
    llm_used_for_run = False

    generated: list[GeneratedReason] = []
    success_count = 0
    fallback_count = 0

    for item in reason_input.items:
        reason = _generate_item_reason(
            item,
            relationship_code=relationship_code,
            relationship_label=relationship_label,
            occasion_code=occasion_code,
            occasion_label=occasion_label,
            feature_entry=feature_by_item.get(item.item_id),
            meaning_entry=meaning_by_item.get(item.item_id),
            risk_entry=risk_by_item.get(item.item_id),
            semantic_record=semantic_records.get(item.item_id),
            template_reader=template_reader,
            reason_repository=reason_repository,
            llm_client=llm_client,
            llm_enabled=llm_enabled and not llm_used_for_run,
        )
        if reason.is_fallback:
            fallback_count += 1
        else:
            success_count += 1
        if reason.reason_basis_json.get("generation_method") in {"llm_refined", "hybrid"}:
            llm_used_for_run = True
        generated.append(reason)

    metrics = ReasonGeneratorRunMetrics(
        reason_generator_item_count=len(generated),
        reason_generator_success_count=success_count,
        reason_generator_fallback_count=fallback_count,
        reason_generator_persisted=all(
            reason.recommendation_reason_id is not None for reason in generated
        ),
        reason_generation_latency_ms=0,
    )
    return tuple(generated), metrics


def aggregate_outcome(
    generated: tuple[GeneratedReason, ...],
) -> ReasonGenerationOutcome:
    if not generated:
        return ReasonGenerationOutcome.UNRECOVERABLE
    if any(reason.is_fallback for reason in generated):
        return ReasonGenerationOutcome.INTERNAL_FALLBACK
    return ReasonGenerationOutcome.SUCCESS


def _generate_item_reason(
    item: ReasonGeneratorInputItem,
    *,
    relationship_code: str | None,
    relationship_label: str,
    occasion_code: str | None,
    occasion_label: str,
    feature_entry: FeatureMatchEntry | None,
    meaning_entry: MeaningMatchEntry | None,
    risk_entry: RiskPenaltyEntry | None,
    semantic_record: ItemSemanticRecord | None,
    template_reader: ReasonTemplateReadPort,
    reason_repository: RecommendationReasonRepositoryPort,
    llm_client: ExternalAiClient | None,
    llm_enabled: bool,
) -> GeneratedReason:
    strong_features = _select_strong_match_features(feature_entry)
    weak_features = _select_weak_match_features(feature_entry)
    semantic_evidence = _collect_semantic_evidence(semantic_record)

    primary_feature = strong_features[0] if strong_features else None
    template = template_reader.resolve_summary_template(
        relationship_code=relationship_code,
        occasion_code=occasion_code,
        feature_code=primary_feature.feature_code if primary_feature else None,
    )

    is_fallback = False
    generation_method = GENERATION_METHOD_TEMPLATE

    if not strong_features:
        reason_summary = GENERIC_REASON_SUMMARY
        reason_points: tuple[str, ...] = (GENERIC_REASON_SUMMARY,)
        reason_badges: tuple[str, ...] = ()
        is_fallback = True
        generation_method = GENERATION_METHOD_INTERNAL_FALLBACK
        template_id = template.reason_template_id if template else str(uuid4())
        template_name = template.template_name if template else DEFAULT_TEMPLATE_NAME
        template_version = template.template_version if template else DEFAULT_TEMPLATE_VERSION
    else:
        reason_badges = _generate_badges(strong_features)
        primary_reason = "と".join(reason_badges[:2]) if reason_badges else "条件に合いやすさ"
        if template is None:
            reason_summary = (
                f"{relationship_label}への{occasion_label}として、"
                f"{primary_reason}がある候補です。"
            )
            template_id = str(uuid4())
            template_name = DEFAULT_TEMPLATE_NAME
            template_version = DEFAULT_TEMPLATE_VERSION
        else:
            reason_summary = _render_template(
                template.template_body,
                relationship_label=relationship_label,
                occasion_label=occasion_label,
                primary_reason=primary_reason,
            )
            template_id = template.reason_template_id
            template_name = template.template_name
            template_version = template.template_version

        reason_points = _generate_reason_points(
            strong_features,
            semantic_evidence,
        )

    reason_summary = _sanitize_text(reason_summary)
    if not reason_summary or _contains_forbidden_expression(reason_summary):
        reason_summary = GENERIC_REASON_SUMMARY
        is_fallback = True
        generation_method = GENERATION_METHOD_INTERNAL_FALLBACK

    if llm_enabled and llm_client is not None and not is_fallback:
        refined = _try_llm_refinement(
            llm_client,
            reason_summary=reason_summary,
            reason_points=reason_points,
            relationship_label=relationship_label,
            occasion_label=occasion_label,
        )
        if refined is not None:
            reason_summary = refined.summary
            reason_points = refined.points
            generation_method = "llm_refined"

    caution_note = _build_caution_note(
        weak_features=weak_features,
        meaning_entry=meaning_entry,
        risk_entry=risk_entry,
        feature_entry=feature_entry,
    )
    if caution_note is not None:
        caution_note = _sanitize_text(caution_note)

    reason_basis_json = _build_reason_basis_json(
        template_name=template_name,
        template_version=template_version,
        strong_features=strong_features,
        weak_features=weak_features,
        semantic_evidence=semantic_evidence,
        item=item,
        generation_method=generation_method,
    )

    insert_row = RecommendationReasonInsertRow(
        recommendation_reason_id=str(uuid4()),
        recommendation_result_item_id=item.recommendation_result_item_id,
        template_id=template_id,
        reason_summary=reason_summary,
        reason_detail=None,
        reason_points_json=list(reason_points) if reason_points else None,
        reason_badges_json=list(reason_badges) if reason_badges else None,
        caution_note=caution_note,
        reason_basis_json=reason_basis_json,
    )

    persisted = _insert_with_retry(
        reason_repository,
        insert_row,
        item=item,
        template_id=template_id,
    )

    return GeneratedReason(
        recommendation_result_item_id=item.recommendation_result_item_id,
        item_id=item.item_id,
        template_id=template_id,
        reason_summary=persisted.reason_summary,
        reason_detail=persisted.reason_detail,
        reason_points=tuple(persisted.reason_points_json or ()),
        reason_badges=tuple(persisted.reason_badges_json or ()),
        caution_note=persisted.caution_note,
        reason_basis_json=persisted.reason_basis_json,
        is_fallback=is_fallback or persisted.reason_summary == GENERIC_REASON_SUMMARY,
        recommendation_reason_id=persisted.recommendation_reason_id,
    )


def _insert_with_retry(
    repository: RecommendationReasonRepositoryPort,
    row: RecommendationReasonInsertRow,
    *,
    item: ReasonGeneratorInputItem,
    template_id: str,
) -> RecommendationReasonInsertRow:
    try:
        return repository.insert(row)
    except Exception:
        fallback_row = RecommendationReasonInsertRow(
            recommendation_reason_id=str(uuid4()),
            recommendation_result_item_id=item.recommendation_result_item_id,
            template_id=template_id,
            reason_summary=GENERIC_REASON_SUMMARY,
            reason_detail=None,
            reason_points_json=[GENERIC_REASON_SUMMARY],
            reason_badges_json=None,
            caution_note=None,
            reason_basis_json={
                "template_name": DEFAULT_TEMPLATE_NAME,
                "template_version": DEFAULT_TEMPLATE_VERSION,
                "used_features": [],
                "used_scores": {
                    "final_score": item.final_score,
                    "context_score": item.context_score,
                },
                "used_semantic_evidence": [],
                "generation_method": GENERATION_METHOD_INTERNAL_FALLBACK,
            },
        )
        return repository.insert(fallback_row)


def _select_strong_match_features(
    feature_entry: FeatureMatchEntry | None,
) -> tuple[SelectedFeature, ...]:
    if feature_entry is None:
        return ()

    selected = [
        SelectedFeature(feature_code=feature_code, match_score=axis.match)
        for feature_code, axis in feature_entry.features.items()
        if axis.match >= STRONG_MATCH_THRESHOLD
    ]
    selected.sort(key=lambda feature: feature.match_score, reverse=True)
    return tuple(selected[:3])


def _select_weak_match_features(
    feature_entry: FeatureMatchEntry | None,
) -> tuple[SelectedFeature, ...]:
    if feature_entry is None:
        return ()

    selected = [
        SelectedFeature(feature_code=feature_code, match_score=axis.match)
        for feature_code, axis in feature_entry.features.items()
        if (
            WEAK_MATCH_MIN <= axis.match < WEAK_MATCH_MAX
            and feature_code in IMPORTANT_FEATURES_FOR_WEAK_MATCH
        )
    ]
    selected.sort(key=lambda feature: feature.match_score, reverse=True)
    return tuple(selected)


def _collect_semantic_evidence(
    semantic_record: ItemSemanticRecord | None,
) -> tuple[SemanticEvidence, ...]:
    if semantic_record is None:
        return ()
    return semantic_record.concepts


def _generate_badges(selected_features: tuple[SelectedFeature, ...]) -> tuple[str, ...]:
    badges: list[str] = []
    for feature in selected_features:
        badge = FEATURE_BADGE_MAP.get(feature.feature_code)
        if badge and badge not in badges:
            badges.append(badge)
    return tuple(badges)


def _generate_reason_points(
    strong_features: tuple[SelectedFeature, ...],
    semantic_evidence: tuple[SemanticEvidence, ...],
) -> tuple[str, ...]:
    points: list[str] = []
    for feature in strong_features[:2]:
        badge = FEATURE_BADGE_MAP.get(feature.feature_code, feature.feature_code)
        points.append(f"{badge}の観点で条件に合いやすい候補です。")

    if semantic_evidence and len(points) < 3:
        evidence = semantic_evidence[0]
        points.append(f"商品説明では「{evidence.evidence_text}」という根拠があります。")

    if not points:
        return (GENERIC_REASON_SUMMARY,)
    return tuple(points[:3])


def _build_caution_note(
    *,
    weak_features: tuple[SelectedFeature, ...],
    meaning_entry: MeaningMatchEntry | None,
    risk_entry: RiskPenaltyEntry | None,
    feature_entry: FeatureMatchEntry | None,
) -> str | None:
    if risk_entry is not None and risk_entry.risk_penalty >= RISK_PENALTY_CAUTION_THRESHOLD:
        return "リスク要因があるため、用途や相手との関係性を踏まえてご検討ください。"

    if feature_entry is not None:
        avoid_similarity = feature_entry.avoid_similarity
        if (
            avoid_similarity is not None
            and avoid_similarity >= AVOID_SIMILARITY_CAUTION_THRESHOLD
        ):
            return "避けたい傾向に近い要素があるため、用途に合うか確認してください。"

    if meaning_entry is not None and meaning_entry.social_match < SOCIAL_MATCH_CAUTION_THRESHOLD:
        return "関係性によっては用途の確認をおすすめします。"

    if weak_features:
        badge = FEATURE_BADGE_MAP.get(weak_features[0].feature_code, "条件")
        return f"{badge}の観点ではやや控えめな候補です。"

    return None


def _build_reason_basis_json(
    *,
    template_name: str,
    template_version: int,
    strong_features: tuple[SelectedFeature, ...],
    weak_features: tuple[SelectedFeature, ...],
    semantic_evidence: tuple[SemanticEvidence, ...],
    item: ReasonGeneratorInputItem,
    generation_method: str,
) -> dict[str, object]:
    return {
        "template_name": template_name,
        "template_version": template_version,
        "template_type": "summary",
        "used_features": [
            {
                "feature_code": feature.feature_code,
                "match_score": feature.match_score,
                "strength": "strong",
            }
            for feature in strong_features
        ]
        + [
            {
                "feature_code": feature.feature_code,
                "match_score": feature.match_score,
                "strength": "weak",
            }
            for feature in weak_features
        ],
        "used_scores": {
            "final_score": item.final_score,
            "context_score": item.context_score,
        },
        "used_semantic_evidence": [
            {
                "concept_code": evidence.concept_code,
                "evidence_text": evidence.evidence_text,
                "confidence": evidence.confidence,
            }
            for evidence in semantic_evidence
        ],
        "generation_method": generation_method,
        "generated_text": None,
    }


def _resolve_relationship(
    request: RecommendationRequest,
) -> tuple[str | None, str]:
    relationship = request.relationship
    if relationship is None:
        return None, DEFAULT_RELATIONSHIP_LABEL
    label = relationship.relationship_label or relationship.relationship_code
    return relationship.relationship_code, label


def _resolve_occasion(
    request: RecommendationRequest,
) -> tuple[str | None, str]:
    occasion = request.occasion
    if occasion is None:
        return None, DEFAULT_OCCASION_LABEL
    label = occasion.occasion_label or occasion.occasion_code
    return occasion.occasion_code, label


def _index_feature_matches(
    feature_match_result: FeatureMatchResult | None,
) -> dict[str, FeatureMatchEntry]:
    if feature_match_result is None:
        return {}
    return {entry.item_id: entry for entry in feature_match_result.entries}


def _index_meaning_matches(
    meaning_match_result: MeaningMatchResult | None,
) -> dict[str, MeaningMatchEntry]:
    if meaning_match_result is None:
        return {}
    return {entry.item_id: entry for entry in meaning_match_result.entries}


def _index_risk_penalties(
    risk_penalty_result: RiskPenaltyResult | None,
) -> dict[str, RiskPenaltyEntry]:
    if risk_penalty_result is None:
        return {}
    return {entry.item_id: entry for entry in risk_penalty_result.entries}


def _render_template(
    template_body: str,
    *,
    relationship_label: str,
    occasion_label: str,
    primary_reason: str,
) -> str:
    return template_body.format(
        relationship_label=relationship_label,
        occasion_label=occasion_label,
        primary_reason=primary_reason,
    )


def _sanitize_text(text: str) -> str:
    sanitized = text.strip()
    for forbidden in FORBIDDEN_EXPRESSIONS:
        sanitized = sanitized.replace(forbidden, "")
    return sanitized.strip()


def _contains_forbidden_expression(text: str) -> bool:
    return any(forbidden in text for forbidden in FORBIDDEN_EXPRESSIONS)


def _is_llm_refinement_enabled() -> bool:
    raw = os.environ.get(LLM_REFINEMENT_ENV, "false")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class _LlmRefinedReason:
    summary: str
    points: tuple[str, ...]


def _try_llm_refinement(
    llm_client: ExternalAiClient,
    *,
    reason_summary: str,
    reason_points: tuple[str, ...],
    relationship_label: str,
    occasion_label: str,
) -> _LlmRefinedReason | None:
    prompt = (
        "Refine the following gift recommendation reason without adding new facts.\n"
        f"relationship={relationship_label}\n"
        f"occasion={occasion_label}\n"
        f"summary={reason_summary}\n"
        f"points={list(reason_points)}"
    )
    try:
        response = llm_client.generate(prompt, purpose="reason_refinement")
    except Exception:
        return None

    refined_summary = response.text.strip()
    if not refined_summary or _contains_forbidden_expression(refined_summary):
        return None
    return _LlmRefinedReason(summary=refined_summary, points=reason_points)
