"""MOD-RECO-003 Config Version Resolver smoke tests."""

from __future__ import annotations

import pytest

from reco.application.config_version_resolver import (
    BatchResolveContext,
    ConfigResolveError,
    ConfigVersionResolver,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    GenerationType,
    build_default_config_resolver,
    build_default_in_memory_repository,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import ExecutionCondition, ExecutionMode, RecommendationRequest


def _ui_context() -> ExecutionContext:
    return ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id="req-config-1",
            execution=ExecutionCondition(mode=ExecutionMode.UI),
        ),
        trace_id="trace-config-1",
        execution_mode=ExecutionMode.UI,
    )


def test_ui_mode_resolves_default_config_versions() -> None:
    resolver = build_default_config_resolver()
    context = resolver.resolve(_ui_context())

    assert context.config_versions["semantic_config_version_id"] == (
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert "model_versions.embedding" in context.config_versions
    assert "model_versions.llm" in context.config_versions
    assert "model_versions.ranking" in context.config_versions
    assert context.config_versions["reason_template_catalog_ok"] == "true"
    assert "MOD-RECO-003" in context.completed_modules


def test_explicit_semantic_config_version_id_is_adopted() -> None:
    resolver = build_default_config_resolver()
    explicit_id = "a1111111-1111-4111-8111-111111111199"
    context = ExecutionContext(
        recommendation_request=RecommendationRequest(
            request_id="req-eval-1",
            execution=ExecutionCondition(
                mode=ExecutionMode.EVALUATION,
                semantic_config_version_id=explicit_id,
            ),
        ),
        trace_id="trace-eval-1",
        execution_mode=ExecutionMode.EVALUATION,
    )

    updated = resolver.resolve(context)
    assert updated.config_versions["semantic_config_version_id"] == explicit_id


def test_missing_feature_definition_raises_cfg_006() -> None:
    repository = build_default_in_memory_repository()
    repository.feature_definition_counts[DEFAULT_SEMANTIC_CONFIG_VERSION_ID] = 0
    resolver = ConfigVersionResolver(repository=repository)

    with pytest.raises(ConfigResolveError) as exc_info:
        resolver.resolve(_ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-006"


def test_batch_semantic_generation_resolves_embedding_and_llm() -> None:
    resolver = build_default_config_resolver()
    resolved = resolver.resolve_batch(
        BatchResolveContext(
            item_generation_queue_id="queue-1",
            item_id="item-1",
            generation_type=GenerationType.SEMANTIC,
        )
    )

    assert resolved.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert "embedding" in resolved.model_versions
    assert "llm" in resolved.model_versions
    assert resolved.ranking_config_id is None
