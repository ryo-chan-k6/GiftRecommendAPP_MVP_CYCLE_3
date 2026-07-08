"""MOD-RECO-009 User Context Builder smoke tests (implementation Task)."""

from __future__ import annotations

import pytest

from conftest import build_builder_with_registered_run, _sample_context
from reco.application.user_context_builder import (
    LAMBDA_CTX_FALLBACK,
    SURFACE_ERROR_CODE,
    UserContextBuildError,
)


def test_execute_builds_user_context_with_lambda_ctx_fallback() -> None:
    context = _sample_context(run_id="run-smoke-success")
    builder, user_meaning_repo, _, _ = build_builder_with_registered_run(context)

    result_context = builder.execute(context)

    user_context = result_context.user_context  # type: ignore[attr-defined]
    user_meaning = result_context.user_meaning  # type: ignore[attr-defined]

    assert user_context.lambda_ctx == pytest.approx(LAMBDA_CTX_FALLBACK)
    assert user_meaning.lambda_ctx == pytest.approx(LAMBDA_CTX_FALLBACK)
    assert "恋人" in user_context.preferred_context.context_query
    assert "誕生日" in user_context.preferred_context.context_query
    assert "実用的なギフト" in user_context.preferred_context.embedding_query_text
    assert "避けたい" not in user_context.preferred_context.embedding_query_text
    assert context.run_id in user_meaning_repo.rows_by_run
    assert "MOD-RECO-009" in result_context.completed_modules


def test_execute_raises_when_user_meaning_missing() -> None:
    context = _sample_context(run_id="run-smoke-no-meaning")
    builder, _, _, _ = build_builder_with_registered_run(context)
    del context.user_meaning  # type: ignore[attr-defined]

    with pytest.raises(UserContextBuildError) as exc_info:
        builder.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "user_meaning is required" in exc_info.value.message
