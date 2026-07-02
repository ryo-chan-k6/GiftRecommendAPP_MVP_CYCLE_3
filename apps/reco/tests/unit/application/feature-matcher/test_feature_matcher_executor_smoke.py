"""MOD-RECO-014 Feature Matcher smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import (
    _sample_context,
    _sample_internal_estimate,
    _sample_user_feature,
    _uniform_user_features,
    build_matcher_with_repository,
)
from reco.application.feature_matcher import (
    FeatureMatcherError,
    InMemoryItemFeatureRecord,
    InMemoryItemFeatureRepository,
    SURFACE_ERROR_CODE,
)
from reco.application.post_hard_filter_executor.models import (
    ValidatedRetrievalCandidate,
    ValidatedRetrievalCandidateItem,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def test_execute_with_empty_validated_candidate_succeeds() -> None:
    context = _sample_context(
        validated_candidate=ValidatedRetrievalCandidate(
            candidates=(),
            total_validated=0,
            total_excluded=0,
        ),
    )
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    result = result_context.feature_match_result  # type: ignore[attr-defined]
    assert result.total_matched == 0
    assert result_context.feature_matcher_candidate_count == 0  # type: ignore[attr-defined]
    assert "MOD-RECO-014" in result_context.completed_modules


def test_execute_computes_feature_match_distance() -> None:
    context = _sample_context(
        user_feature=_sample_user_feature(features=_uniform_user_features(0.8)),
    )
    context.validated_retrieval_candidate = ValidatedRetrievalCandidate(  # type: ignore[attr-defined]
        candidates=(
            ValidatedRetrievalCandidateItem(item_id="item-001", similarity_score=0.95),
        ),
        total_validated=1,
        total_excluded=0,
    )
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    entry = result_context.feature_match_result.entries[0]  # type: ignore[attr-defined]
    assert entry.features["formality"].distance == pytest.approx(0.15)
    assert entry.features["formality"].match == pytest.approx(0.85)
    assert entry.meaning_distance > 0


def test_execute_excludes_item_without_features() -> None:
    context = _sample_context()
    repo = InMemoryItemFeatureRepository(
        records={
            "item-001": InMemoryItemFeatureRecord(
                item_id="item-001",
                semantic_config_version_id=context.config_versions[
                    "semantic_config_version_id"
                ],
                features={
                    axis: 0.5
                    for axis in MVP_FEATURE_CODES
                },
            ),
        },
    )
    matcher, _ = build_matcher_with_repository(context, item_repository=repo)

    result_context = matcher.execute(context)

    result = result_context.feature_match_result  # type: ignore[attr-defined]
    assert result.total_matched == 1
    assert result.total_excluded == 1
    assert result_context.feature_matcher_excluded_count == 1  # type: ignore[attr-defined]


def test_execute_omits_avoid_similarity_when_delta_all_zero() -> None:
    context = _sample_context()
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    for entry in result_context.feature_match_result.entries:  # type: ignore[attr-defined]
        assert entry.avoid_similarity is None


def test_execute_sets_avoid_similarity_when_delta_non_zero() -> None:
    avoid_delta = {axis: 0.0 for axis in MVP_FEATURE_CODES}
    avoid_delta["formality"] = 0.2
    context = _sample_context(
        internal_estimate=_sample_internal_estimate(avoid_delta=avoid_delta),
    )
    matcher, _ = build_matcher_with_repository(context)

    result_context = matcher.execute(context)

    entry = result_context.feature_match_result.entries[0]  # type: ignore[attr-defined]
    assert entry.avoid_similarity is not None
    assert 0.0 <= entry.avoid_similarity <= 1.0


def test_execute_raises_on_missing_user_feature_axis() -> None:
    partial = _uniform_user_features()
    del partial["formality"]
    context = _sample_context(user_feature=_sample_user_feature(features=partial))
    matcher, _ = build_matcher_with_repository(context)

    with pytest.raises(FeatureMatcherError) as exc_info:
        matcher.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_raises_on_repository_failure() -> None:
    context = _sample_context()
    repo = InMemoryItemFeatureRepository(should_fail_on_fetch=True)
    matcher, _ = build_matcher_with_repository(context, item_repository=repo)

    with pytest.raises(FeatureMatcherError) as exc_info:
        matcher.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
