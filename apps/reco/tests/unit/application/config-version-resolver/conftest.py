"""Shared fixtures for MOD-RECO-003 unit tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from reco.application.config_version_resolver import (
    ConfigVersionResolver,
    InMemoryConfigRepository,
    build_default_in_memory_repository,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import ExecutionCondition, ExecutionMode, RecommendationRequest


@pytest.fixture
def default_repository() -> InMemoryConfigRepository:
    return build_default_in_memory_repository()


@pytest.fixture
def default_resolver(default_repository: InMemoryConfigRepository) -> ConfigVersionResolver:
    return ConfigVersionResolver(repository=default_repository)


def build_resolver(
    repository: InMemoryConfigRepository | None = None,
    **repository_overrides: object,
) -> ConfigVersionResolver:
    repo = repository or build_default_in_memory_repository()
    if repository_overrides:
        repo = replace(repo, **repository_overrides)
    return ConfigVersionResolver(repository=repo)


def ui_context(*, request_id: str = "req-config-1", trace_id: str = "trace-config-1") -> ExecutionContext:
    return ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id=request_id,
            execution=ExecutionCondition(mode=ExecutionMode.UI),
        ),
        trace_id=trace_id,
        execution_mode=ExecutionMode.UI,
    )


def evaluation_context(
    *,
    semantic_config_version_id: str | None = None,
    config_name: str | None = None,
    version_label: str | None = None,
    model_version_id: str | None = None,
    request_id: str = "req-eval-1",
    trace_id: str = "trace-eval-1",
) -> ExecutionContext:
    return ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id=request_id,
            execution=ExecutionCondition(
                mode=ExecutionMode.EVALUATION,
                semantic_config_version_id=semantic_config_version_id,
                config_name=config_name,
                version_label=version_label,
                model_version_id=model_version_id,
            ),
        ),
        trace_id=trace_id,
        execution_mode=ExecutionMode.EVALUATION,
    )
