"""MOD-RECO-003 Config Version Resolver unit tests (module spec §14)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from conftest import build_resolver, evaluation_context, ui_context
from reco.application.config_version_resolver import (
    BatchResolveContext,
    ConfigResolveError,
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    GenerationType,
    build_default_config_resolver,
    build_default_in_memory_repository,
)
from reco.application.config_version_resolver.in_memory_repository import (
    DEFAULT_LLM_MODEL_VERSION_ID,
    DEFAULT_RANKING_MODEL_VERSION_ID,
)
from reco.application.config_version_resolver.models import (
    ModelVersionRecord,
    SemanticConfigVersionRecord,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import ExecutionCondition, ExecutionMode, RecommendationRequest


TREATMENT_SEMANTIC_CONFIG_VERSION_ID = "a1111111-1111-4111-8111-111111111199"
TREATMENT_SEMANTIC_CONFIG_ID = "a1111111-1111-4111-8111-111111111199"
OVERRIDE_EMBEDDING_MODEL_VERSION_ID = "b1111111-1111-4111-8111-111111111199"


# §14 No.1 正常系（ui）
def test_ui_mode_resolves_default_config_versions() -> None:
    resolver = build_default_config_resolver()
    context = resolver.resolve(ui_context())

    assert context.config_versions["semantic_config_version_id"] == (
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert context.config_versions["model_versions.embedding"] == (
        DEFAULT_EMBEDDING_MODEL_VERSION_ID
    )
    assert context.config_versions["model_versions.llm"] == DEFAULT_LLM_MODEL_VERSION_ID
    assert context.config_versions["model_versions.ranking"] == (
        DEFAULT_RANKING_MODEL_VERSION_ID
    )
    assert context.config_versions["ranking_config_id"] == DEFAULT_RANKING_CONFIG_ID
    assert context.config_versions["matching_config_id"] == DEFAULT_MATCHING_CONFIG_ID
    assert context.config_versions["social_feature_weights.formality"] == "0.333"
    assert context.config_versions["symbolic_feature_weights.emotion"] == "0.2"
    assert context.config_versions["reason_template_catalog_ok"] == "true"
    assert context.config_versions["resolution_metadata.resolution_path"] == (
        "default_series_current"
    )
    assert "MOD-RECO-003" in context.completed_modules


# §14 No.2 正常系（evaluation）
def test_explicit_semantic_config_version_id_is_adopted() -> None:
    resolver = build_default_config_resolver()
    updated = resolver.resolve(
        evaluation_context(semantic_config_version_id=TREATMENT_SEMANTIC_CONFIG_VERSION_ID)
    )
    assert updated.config_versions["semantic_config_version_id"] == (
        TREATMENT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert updated.config_versions["resolution_metadata.resolution_path"] == (
        "explicit_semantic_config_version_id"
    )


# §14 No.3 正常系（composite）
def test_composite_config_name_and_version_label_resolve_uuid() -> None:
    resolver = build_default_config_resolver()
    updated = resolver.resolve(
        evaluation_context(
            config_name="treatment_semantic_config",
            version_label="v1.0.0",
        )
    )

    assert updated.config_versions["semantic_config_version_id"] == (
        TREATMENT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert updated.config_versions["resolution_metadata.semantic_config_name"] == (
        "treatment_semantic_config"
    )
    assert updated.config_versions["resolution_metadata.version_label"] == "v1.0.0"
    assert updated.config_versions["resolution_metadata.resolution_path"] == (
        "composite_config_name_version_label"
    )


# §14 No.4 系列選択（複数 is_active 時の default fallback）
def test_multiple_active_series_fallback_to_mvp_semantic_config() -> None:
    repository = build_default_in_memory_repository()
    assert sum(1 for config in repository.semantic_configs if config.is_active) >= 2

    updated = build_resolver(repository).resolve(ui_context())

    assert updated.config_versions["semantic_config_version_id"] == (
        DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert updated.config_versions["resolution_metadata.semantic_config_name"] == (
        "mvp_semantic_config"
    )


# §14 No.5 Treatment 明示割当（config_name 系列）
def test_treatment_config_name_selects_explicit_series() -> None:
    updated = build_default_config_resolver().resolve(
        evaluation_context(config_name="treatment_semantic_config")
    )

    assert updated.config_versions["semantic_config_version_id"] == (
        TREATMENT_SEMANTIC_CONFIG_VERSION_ID
    )
    assert updated.config_versions["resolution_metadata.resolution_path"] == (
        "config_name_current"
    )


# §14 No.6 非 active 系列
def test_inactive_series_is_rejected_when_explicitly_requested() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        semantic_configs=[
            replace(config, is_active=False) if config.config_name == "treatment_semantic_config"
            else config
            for config in repository.semantic_configs
        ],
    )
    resolver = build_resolver(repository)

    with pytest.raises(ConfigResolveError) as exc_info:
        resolver.resolve(evaluation_context(config_name="treatment_semantic_config"))

    assert exc_info.value.detail_code == "GRS-CFG-002"


# §14 No.7 Semantic 失敗（current 0 件）
def test_zero_current_semantic_versions_raises_cfg_001() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        semantic_config_versions=[
            replace(version, is_current=False) for version in repository.semantic_config_versions
        ],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-001"


# §14 No.7 Semantic 失敗（current 2 件以上）
def test_ambiguous_current_semantic_versions_raises_cfg_002() -> None:
    repository = build_default_in_memory_repository()
    duplicate_current = SemanticConfigVersionRecord(
        semantic_config_version_id="a1111111-1111-4111-8111-111111111188",
        semantic_config_id="a1111111-1111-4111-8111-111111111101",
        version_label="v1.0.1",
        is_current=True,
    )
    repository = replace(
        repository,
        semantic_config_versions=[*repository.semantic_config_versions, duplicate_current],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-002"


# §14 No.7 Semantic 失敗（存在しない UUID）
def test_unknown_semantic_config_version_id_raises_cfg_002() -> None:
    with pytest.raises(ConfigResolveError) as exc_info:
        build_default_config_resolver().resolve(
            evaluation_context(semantic_config_version_id="00000000-0000-4000-8000-000000000000")
        )

    assert exc_info.value.detail_code == "GRS-CFG-002"


# §14 No.8 Model 失敗
def test_missing_required_model_type_raises_cfg_003() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        model_versions=[
            record for record in repository.model_versions if record.model_type != "llm"
        ],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-003"


# §14 No.9 Ranking 失敗
def test_missing_ranking_config_raises_cfg_004() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(repository, ranking_configs=[])

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-004"


# matching_config 失敗
def test_missing_matching_config_raises_cfg_007() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(repository, matching_configs=[])

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-007"


def test_invalid_matching_feature_weights_raises_cfg_007() -> None:
    repository = build_default_in_memory_repository()
    invalid_matching = replace(
        repository.matching_configs[0],
        parameter_json={"social_feature_weights": {}, "symbolic_feature_weights": {}},
    )
    repository = replace(
        repository,
        matching_configs=[invalid_matching],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-007"


# §14 No.10 Feature 定義不足
def test_missing_feature_definition_raises_cfg_006() -> None:
    repository = build_default_in_memory_repository()
    repository.feature_definition_counts[DEFAULT_SEMANTIC_CONFIG_VERSION_ID] = 0

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-006"


# §14 No.11 Reason カタログ
def test_missing_active_reason_template_raises_cfg_006() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        reason_templates=[
            record
            for record in repository.reason_templates
            if record.template_type != "summary"
        ],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(ui_context())

    assert exc_info.value.detail_code == "GRS-CFG-006"
    assert "summary" in exc_info.value.message


# §14 No.12 execution_context 更新
def test_resolve_populates_execution_context_config_versions() -> None:
    context = ui_context()
    assert context.config_versions == {}

    updated = build_default_config_resolver().resolve(context)

    assert updated is context
    assert updated.config_versions
    assert "semantic_config_version_id" in updated.config_versions
    assert updated.config_versions["model_versions.embedding"]
    assert updated.config_versions["ranking_config_id"]
    assert updated.config_versions["matching_config_id"]
    assert "MOD-RECO-003" in updated.completed_modules


# §14 No.14 batch semantic
def test_batch_semantic_generation_resolves_embedding_and_llm() -> None:
    resolved = build_default_config_resolver().resolve_batch(
        BatchResolveContext(
            item_generation_queue_id="queue-1",
            item_id="item-1",
            generation_type=GenerationType.SEMANTIC,
        )
    )

    assert resolved.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert resolved.model_versions["embedding"] == DEFAULT_EMBEDDING_MODEL_VERSION_ID
    assert resolved.model_versions["llm"] == DEFAULT_LLM_MODEL_VERSION_ID
    assert resolved.ranking_config_id is None
    assert resolved.matching_config_id is None
    assert resolved.reason_template_catalog_ok is None


# §14 No.15 batch embedding（hint 付き embedding 上書き）
def test_batch_embedding_generation_overrides_embedding_model() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        model_versions=[
            *repository.model_versions,
            ModelVersionRecord(
                model_version_id=OVERRIDE_EMBEDDING_MODEL_VERSION_ID,
                model_type="embedding",
                is_current=False,
            ),
        ],
    )
    resolver = build_resolver(repository)

    resolved = resolver.resolve_batch(
        BatchResolveContext(
            item_generation_queue_id="queue-2",
            item_id="item-2",
            generation_type=GenerationType.EMBEDDING,
            embedding_model_version_id=OVERRIDE_EMBEDDING_MODEL_VERSION_ID,
        )
    )

    assert resolved.model_versions == {
        "embedding": OVERRIDE_EMBEDDING_MODEL_VERSION_ID,
    }
    assert "llm" not in resolved.model_versions


# §14 No.18 冪等性
def test_same_input_produces_identical_resolution() -> None:
    resolver = build_default_config_resolver()
    context = ui_context(request_id="req-idempotent", trace_id="trace-idempotent")

    first = resolver.resolve(context)
    second = resolver.resolve(
        ExecutionContext(
            recommendation_request=RecommendationRequest(
                request_id="req-idempotent",
                execution=ExecutionCondition(mode=ExecutionMode.UI),
            ),
            trace_id="trace-idempotent",
            execution_mode=ExecutionMode.UI,
        )
    )

    assert first.config_versions == second.config_versions


def test_inactive_parent_series_rejects_explicit_uuid() -> None:
    repository = build_default_in_memory_repository()
    repository = replace(
        repository,
        semantic_configs=[
            replace(config, is_active=False)
            if config.semantic_config_id == TREATMENT_SEMANTIC_CONFIG_ID
            else config
            for config in repository.semantic_configs
        ],
    )

    with pytest.raises(ConfigResolveError) as exc_info:
        build_resolver(repository).resolve(
            evaluation_context(semantic_config_version_id=TREATMENT_SEMANTIC_CONFIG_VERSION_ID)
        )

    assert exc_info.value.detail_code == "GRS-CFG-002"
