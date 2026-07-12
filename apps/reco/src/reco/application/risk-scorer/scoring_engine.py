"""Risk Penalty 算出ロジック（MOD-RECO-018 §8.3）。"""

from __future__ import annotations

from datetime import UTC, datetime

from reco.application.feature_matcher.models import FeatureAxisMatch, FeatureMatchResult
from reco.application.meaning_match_aggregator.models import MeaningMatchResult
from reco.application.popularity_scorer.models import PopularityScoreResult
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES

from .constants import (
    DEFAULT_ITEM_FEATURE_CONFIDENCE,
    DEFAULT_SOCIAL_THRESHOLD,
    DEFAULT_W_AVOID,
    DEFAULT_W_DATA_QUALITY,
    DEFAULT_W_SOCIAL,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    MVP_FEATURE_AXIS_COUNT,
    RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED,
    RISK_FORMULA_DEFAULT,
    RISK_PENALTY_DECIMAL_PLACES,
)
from .errors import RiskScorerError
from .models import (
    RiskPenaltyEntry,
    RiskPenaltyResult,
    RiskScorerRunMetrics,
    RiskWeights,
)


def guard_clip(value: float, lower: float, upper: float) -> float:
    return min(upper, max(lower, value))


def round_to_scale(value: float, decimal_places: int) -> float:
    return round(value, decimal_places)


def run_risk_scoring(
    *,
    popularity_score_result: PopularityScoreResult,
    feature_match_result: FeatureMatchResult,
    meaning_match_result: MeaningMatchResult,
    config_versions: dict[str, str],
) -> tuple[RiskPenaltyResult, RiskScorerRunMetrics]:
    """Matching 結果と popularity_score_result から risk_penalty を算出する。"""
    if not popularity_score_result.entries:
        empty = RiskPenaltyResult(entries=(), total_scored=0)
        metrics = RiskScorerRunMetrics(
            risk_scorer_candidate_count=0,
            risk_scorer_latency_ms=0,
            risk_missing_signal_count=0,
            risk_penalty_value_out_of_range_count=0,
            avoid_risk_nonzero_count=0,
        )
        return empty, metrics

    formula = _resolve_risk_formula(config_versions)
    if formula != RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED:
        raise RiskScorerError(f"unsupported risk_formula: {formula}")

    weights = _resolve_risk_weights(config_versions)
    social_threshold = _resolve_social_threshold(config_versions)
    ranking_config_id = config_versions.get("ranking_config_id", "")

    feature_map = {entry.item_id: entry for entry in feature_match_result.entries}
    meaning_map = {entry.item_id: entry for entry in meaning_match_result.entries}

    scored_entries: list[RiskPenaltyEntry] = []
    missing_signal_count = 0
    out_of_range_count = 0
    avoid_risk_nonzero_count = 0
    calculated_at = datetime.now(UTC)

    for pop_entry in popularity_score_result.entries:
        item_id = pop_entry.item_id
        feature_entry = feature_map.get(item_id)
        if feature_entry is None:
            raise RiskScorerError(
                f"feature_match_result missing item_id for risk scoring: {item_id}",
            )
        meaning_entry = meaning_map.get(item_id)
        if meaning_entry is None:
            raise RiskScorerError(
                f"meaning_match_result missing item_id for risk scoring: {item_id}",
            )

        (
            risk_penalty,
            avoid_risk,
            social_low_risk,
            data_quality_risk,
            avoid_similarity_used,
            social_match_used,
            item_feature_confidence_used,
            signal_missing,
            entry_out_of_range,
        ) = _calculate_entry_risk(
            avoid_similarity=feature_entry.avoid_similarity,
            social_match=meaning_entry.social_match,
            features=feature_entry.features,
            weights=weights,
            social_threshold=social_threshold,
        )
        if signal_missing:
            missing_signal_count += 1
        out_of_range_count += entry_out_of_range
        if avoid_risk > 0.0:
            avoid_risk_nonzero_count += 1

        scored_entries.append(
            RiskPenaltyEntry(
                item_id=item_id,
                risk_penalty=risk_penalty,
                risk_formula=formula,
                calculated_at=calculated_at,
                ranking_config_id=ranking_config_id,
                signal_missing=signal_missing,
                avoid_risk=avoid_risk,
                social_low_risk=social_low_risk,
                data_quality_risk=data_quality_risk,
                avoid_similarity_used=avoid_similarity_used,
                social_match_used=social_match_used,
                item_feature_confidence_used=item_feature_confidence_used,
            ),
        )

    if popularity_score_result.total_scored != len(popularity_score_result.entries):
        raise RiskScorerError(
            "popularity_score_result.total_scored is inconsistent with entries length",
        )

    result = RiskPenaltyResult(
        entries=tuple(scored_entries),
        total_scored=len(scored_entries),
    )
    metrics = RiskScorerRunMetrics(
        risk_scorer_candidate_count=len(scored_entries),
        risk_scorer_latency_ms=0,
        risk_missing_signal_count=missing_signal_count,
        risk_penalty_value_out_of_range_count=out_of_range_count,
        avoid_risk_nonzero_count=avoid_risk_nonzero_count,
    )
    return result, metrics


def _resolve_risk_formula(config_versions: dict[str, str]) -> str:
    formula = config_versions.get("risk_formula")
    if not formula:
        return RISK_FORMULA_DEFAULT
    return formula


def _resolve_risk_weights(config_versions: dict[str, str]) -> RiskWeights:
    return RiskWeights(
        w_avoid=_parse_optional_float(
            config_versions.get("risk_weights.avoid"),
            default=DEFAULT_W_AVOID,
        ),
        w_social=_parse_optional_float(
            config_versions.get("risk_weights.social"),
            default=DEFAULT_W_SOCIAL,
        ),
        w_data_quality=_parse_optional_float(
            config_versions.get("risk_weights.data_quality"),
            default=DEFAULT_W_DATA_QUALITY,
        ),
    )


def _resolve_social_threshold(config_versions: dict[str, str]) -> float:
    return _parse_optional_float(
        config_versions.get("social_threshold"),
        default=DEFAULT_SOCIAL_THRESHOLD,
    )


def _parse_optional_float(raw: str | None, *, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RiskScorerError(f"invalid risk config value: {raw}") from exc


def _calculate_entry_risk(
    *,
    avoid_similarity: float | None,
    social_match: float,
    features: dict[str, FeatureAxisMatch],
    weights: RiskWeights,
    social_threshold: float,
) -> tuple[
    float,
    float,
    float,
    float,
    float | None,
    float,
    float,
    bool,
    int,
]:
    signal_missing = False
    out_of_range_count = 0

    if avoid_similarity is None:
        avoid_risk = 0.0
        avoid_similarity_used: float | None = None
    else:
        clipped_avoid, avoid_clip = _clip_unit_value(avoid_similarity)
        out_of_range_count += avoid_clip
        avoid_risk = clipped_avoid
        avoid_similarity_used = clipped_avoid

    clipped_social, social_clip = _clip_unit_value(social_match)
    out_of_range_count += social_clip
    social_match_used = clipped_social

    if clipped_social >= social_threshold:
        social_low_risk = 0.0
    else:
        social_low_risk = (social_threshold - clipped_social) / social_threshold

    item_feature_confidence, confidence_missing = _derive_item_feature_confidence(
        features,
    )
    if confidence_missing:
        signal_missing = True

    data_quality_risk = 1.0 - item_feature_confidence

    raw_penalty = (
        weights.w_avoid * avoid_risk
        + weights.w_social * social_low_risk
        + weights.w_data_quality * data_quality_risk
    )
    clipped_penalty = guard_clip(raw_penalty, GUARD_CLIP_MIN, GUARD_CLIP_MAX)
    if clipped_penalty != raw_penalty:
        out_of_range_count += 1

    risk_penalty = round_to_scale(clipped_penalty, RISK_PENALTY_DECIMAL_PLACES)

    return (
        risk_penalty,
        round_to_scale(avoid_risk, RISK_PENALTY_DECIMAL_PLACES),
        round_to_scale(social_low_risk, RISK_PENALTY_DECIMAL_PLACES),
        round_to_scale(data_quality_risk, RISK_PENALTY_DECIMAL_PLACES),
        avoid_similarity_used,
        social_match_used,
        item_feature_confidence,
        signal_missing,
        out_of_range_count,
    )


def _derive_item_feature_confidence(
    features: dict[str, FeatureAxisMatch],
) -> tuple[float, bool]:
    """MVP 代理式: (8 - imputed_count) / 8.0。全軸 imputed 情報欠損時は 0.5。"""
    if not features:
        return DEFAULT_ITEM_FEATURE_CONFIDENCE, True

    axes_with_imputed_info = [
        code for code in MVP_FEATURE_CODES if code in features
    ]
    if not axes_with_imputed_info:
        return DEFAULT_ITEM_FEATURE_CONFIDENCE, True

    imputed_count = sum(
        1 for code in MVP_FEATURE_CODES
        if code in features and features[code].imputed
    )
    confidence = (MVP_FEATURE_AXIS_COUNT - imputed_count) / float(
        MVP_FEATURE_AXIS_COUNT,
    )
    return confidence, False


def _clip_unit_value(value: float) -> tuple[float, int]:
    if value < GUARD_CLIP_MIN or value > GUARD_CLIP_MAX:
        return guard_clip(value, GUARD_CLIP_MIN, GUARD_CLIP_MAX), 1
    return value, 0
