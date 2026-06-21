from reco.domain import (
    MVP_FEATURE_CODES,
    RecommendationRequest,
    RecommendationResult,
    RecommendationResultItem,
    RecommendationRun,
    RunStatus,
)


def test_mvp_feature_codes_has_eight_dimensions() -> None:
    assert len(MVP_FEATURE_CODES) == 8
    assert MVP_FEATURE_CODES[:3] == ("formality", "safety", "brand_appropriateness")
    assert MVP_FEATURE_CODES[3:] == (
        "emotion",
        "novelty",
        "intimacy",
        "symbolic_identity",
        "story_richness",
    )


def test_recommendation_request_detects_gift_context() -> None:
    with_context = RecommendationRequest(
        request_id="req-1",
        relationship="friend",
        occasion="birthday",
    )
    without_context = RecommendationRequest(request_id="req-2")

    assert with_context.has_gift_context() is True
    assert without_context.has_gift_context() is False


def test_recommendation_run_status_transition() -> None:
    run = RecommendationRun(run_id="run-1", request_id="req-1")

    updated = run.with_status(RunStatus.RUNNING)

    assert run.status is RunStatus.PENDING
    assert updated.status is RunStatus.RUNNING
    assert updated.run_id == "run-1"


def test_recommendation_result_item_count() -> None:
    result = RecommendationResult(
        run_id="run-1",
        items=(
            RecommendationResultItem(item_id="item-1", rank=1, final_score=0.9),
            RecommendationResultItem(item_id="item-2", rank=2, final_score=0.8),
        ),
    )

    assert result.item_count == 2
