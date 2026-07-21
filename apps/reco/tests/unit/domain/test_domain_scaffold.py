from reco.domain import (
    BudgetCondition,
    ExecutionCondition,
    ExecutionMode,
    MVP_FEATURE_CODES,
    NonPreferredCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RecommendationResult,
    RecommendationResultItem,
    RecommendationRun,
    RelationshipCondition,
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
        relationship=RelationshipCondition(relationship_code="friend"),
        occasion=OccasionCondition(occasion_code="birthday"),
    )
    without_context = RecommendationRequest(request_id="req-2")

    assert with_context.has_gift_context() is True
    assert without_context.has_gift_context() is False


def test_recommendation_request_detects_search_condition() -> None:
    with_preferred = RecommendationRequest(
        request_id="req-3",
        preferred_condition=PreferredCondition(preferred_text="上品なもの"),
    )
    with_budget = RecommendationRequest(
        request_id="req-4",
        budget=BudgetCondition(budget_max=5000),
    )

    assert with_preferred.has_search_condition() is True
    assert with_budget.has_search_condition() is True


def test_recommendation_request_minimum_input_rq01() -> None:
    gift_context_only = RecommendationRequest(
        request_id="req-5",
        relationship=RelationshipCondition(relationship_code="boss"),
    )
    search_only = RecommendationRequest(
        request_id="req-6",
        non_preferred_condition=NonPreferredCondition(
            non_preferred_text="カジュアルすぎるものは避けたい",
        ),
    )
    empty = RecommendationRequest(request_id="req-7")

    assert gift_context_only.has_minimum_input() is True
    assert search_only.has_minimum_input() is True
    assert empty.has_minimum_input() is False


def test_recommendation_request_optional_execution_fields() -> None:
    request = RecommendationRequest(
        request_id="req-8",
        relationship=RelationshipCondition(relationship_code="boss"),
        occasion=OccasionCondition(occasion_code="thanks"),
        execution=ExecutionCondition(mode=ExecutionMode.UI, top_k=10),
    )

    assert request.execution is not None
    assert request.execution.mode is ExecutionMode.UI
    assert request.execution.top_k == 10


def test_recommendation_run_status_transition() -> None:
    run = RecommendationRun(run_id="run-1", request_id="req-1")

    updated = run.with_status(RunStatus.RUNNING)

    assert run.status is RunStatus.ACCEPTED
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
