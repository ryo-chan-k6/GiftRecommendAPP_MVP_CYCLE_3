"""MOD-RECO-023 Reason Generator smoke tests (implementation Task)."""

from __future__ import annotations

from reco.application.recommendation_orchestrator.ports import ReasonGenerationOutcome

from conftest import (
    DEFAULT_ITEM_ID,
    DEFAULT_RESULT_ITEM_ID,
    _sample_context,
    build_reason_generator,
)
from reco.application.reason_generator import (
    GENERIC_REASON_SUMMARY,
    InMemoryRecommendationReasonRepository,
)


def test_generate_creates_reason_and_persists_row() -> None:
    context = _sample_context()
    reason_repository = InMemoryRecommendationReasonRepository()
    generator = build_reason_generator(reason_repository=reason_repository)

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.SUCCESS
    assert "MOD-RECO-023" in context.completed_modules
    item = context.recommendation_result.items[0]
    assert item.reason_summary
    assert item.reason_summary != GENERIC_REASON_SUMMARY
    assert item.reason_status is not None
    assert item.is_fallback is False
    assert DEFAULT_RESULT_ITEM_ID in reason_repository.rows_by_result_item_id
    version_info = context.recommendation_result.version_info or {}
    assert version_info["reason_generator_persisted"] == "true"
    assert version_info["reason_generator_item_count"] == "1"
    assert version_info[f"item:{DEFAULT_ITEM_ID}:recommendation_reason_id"]


def test_generate_uses_internal_fallback_without_strong_match() -> None:
    context = _sample_context(include_feature_match=False)
    generator = build_reason_generator()

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK
    item = context.recommendation_result.items[0]
    assert item.reason_summary == GENERIC_REASON_SUMMARY
    assert item.is_fallback is True


def test_generate_succeeds_with_zero_result_item_count() -> None:
    from reco.domain.recommendation.result import ResultStatus

    context = _sample_context()
    assert context.recommendation_result is not None
    context.recommendation_result = type(context.recommendation_result)(
        run_id=context.recommendation_result.run_id,
        request_id=context.recommendation_result.request_id,
        items=(),
        result_status=ResultStatus.EMPTY,
        version_info={
            **(context.recommendation_result.version_info or {}),
            "result_item_count": "0",
        },
    )
    generator = build_reason_generator()

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.SUCCESS
    assert "MOD-RECO-023" in context.completed_modules
    assert context.reason_generator_item_count == 0


def test_generate_returns_unrecoverable_on_items_count_mismatch() -> None:
    context = _sample_context()
    assert context.recommendation_result is not None
    context.recommendation_result.version_info["result_item_count"] = "2"
    generator = build_reason_generator()

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.UNRECOVERABLE


def test_generate_does_not_mutate_rank_or_final_score() -> None:
    context = _sample_context()
    before = context.recommendation_result.items[0]
    generator = build_reason_generator()

    generator.generate(context)

    after = context.recommendation_result.items[0]
    assert after.rank == before.rank
    assert after.final_score == before.final_score
