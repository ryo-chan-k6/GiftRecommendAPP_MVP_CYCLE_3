"""MOD-RECO-008 User Meaning Projector minimal smoke tests."""

from __future__ import annotations

from conftest import _sample_context, build_projector_with_registered_run
from reco.application.user_meaning_projector import (
    SURFACE_ERROR_CODE,
    UserMeaningProjectionError,
    project_user_meaning_coordinates,
)
from reco.application.user_meaning_projector.models import MeaningProjectionWeights


def test_project_user_meaning_coordinates_simple_average() -> None:
    features = {axis: 0.2 for axis in ("formality", "safety", "brand_appropriateness", "emotion", "novelty", "intimacy", "symbolic_identity", "story_richness")}

    user_social, user_symbolic, stats = project_user_meaning_coordinates(
        features,
        MeaningProjectionWeights(),
    )

    assert user_social == 0.2
    assert user_symbolic == 0.2
    assert stats.guard_clip_applied_count == 0


def test_execute_projects_user_meaning_onto_execution_context() -> None:
    context = _sample_context()
    projector = build_projector_with_registered_run(context)

    result_context = projector.execute(context)

    projection = result_context.user_meaning  # type: ignore[attr-defined]
    assert projection.user_social == 0.5
    assert projection.user_symbolic == 0.5
    assert projection.recommendation_run_id == context.run_id
    assert getattr(projection, "lambda_ctx", None) is None
    assert "MOD-RECO-008" in result_context.completed_modules


def test_execute_fails_when_user_feature_missing() -> None:
    context = _sample_context()
    projector = build_projector_with_registered_run(context)
    del context.user_feature  # type: ignore[attr-defined]

    try:
        projector.execute(context)
    except UserMeaningProjectionError as exc:
        assert exc.error_code == SURFACE_ERROR_CODE
    else:
        raise AssertionError("expected UserMeaningProjectionError")
