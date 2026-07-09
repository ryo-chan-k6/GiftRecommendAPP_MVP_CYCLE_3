"""Shared fixtures for MOD-RECO-027 unit tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

DEFAULT_ITEM_ID = "item-feature-1"
DEFAULT_TRACE_ID = "trace-item-feature-1"
DEFAULT_BATCH_RUN_ID = "batch-run-1"
DEFAULT_QUEUE_ID = "queue-row-1"
DEFAULT_FEATURE_INPUT_HASH = "a" * 64


def _load_item_feature_generator_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/item-feature-generator/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.item_feature_generator",
        init_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_item_feature_generator_package()

from reco.application.item_feature_generator import (  # noqa: E402
    ItemFeatureGenerationContext,
    ItemFeatureGenerator,
    ItemSemanticInput,
)
from reco.application.item_feature_generator.in_memory_repository import (  # noqa: E402
    InMemoryConceptFeatureRuleRepository,
    InMemoryFeatureDefinitionRepository,
    InMemoryItemFeatureRepository,
    InMemoryItemValidation,
    InMemoryNormalizationRuleRepository,
    build_default_in_memory_repositories,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger  # noqa: E402


def _sample_item_semantic(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    semantic_config_version_id: str = DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    concepts: list[dict[str, object]] | None = None,
) -> ItemSemanticInput:
    return ItemSemanticInput(
        item_id=item_id,
        semantic_config_version_id=semantic_config_version_id,
        semantic_json={"concepts": concepts or []},
    )


def _sample_context(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    feature_input_hash: str = DEFAULT_FEATURE_INPUT_HASH,
    concepts: list[dict[str, object]] | None = None,
    skip_if_unchanged: bool = True,
) -> ItemFeatureGenerationContext:
    return ItemFeatureGenerationContext(
        trace_id=DEFAULT_TRACE_ID,
        batch_run_id=DEFAULT_BATCH_RUN_ID,
        item_generation_queue_id=DEFAULT_QUEUE_ID,
        item_id=item_id,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        feature_input_hash=feature_input_hash,
        item_semantic=_sample_item_semantic(
            item_id=item_id,
            concepts=concepts,
        ),
        skip_if_unchanged=skip_if_unchanged,
    )


def build_generator_with_registered_item(
    context: ItemFeatureGenerationContext,
    *,
    should_fail_upsert: bool = False,
) -> ItemFeatureGenerator:
    concept_rules, normalization_rules, feature_definitions, item_validation, _ = (
        build_default_in_memory_repositories()
    )
    assert isinstance(item_validation, InMemoryItemValidation)
    item_validation.register_item(context.item_id)
    return ItemFeatureGenerator(
        concept_feature_rules=concept_rules,
        normalization_rules=normalization_rules,
        feature_definitions=feature_definitions,
        item_validation=item_validation,
        item_feature_repository=InMemoryItemFeatureRepository(
            should_fail_on_upsert=should_fail_upsert,
        ),
        logger=ScaffoldRecoLogger(),
    )
