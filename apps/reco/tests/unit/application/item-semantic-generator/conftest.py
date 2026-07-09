"""Shared fixtures for MOD-RECO-026 unit tests."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID

DEFAULT_ITEM_ID = "item-semantic-1"
DEFAULT_TRACE_ID = "trace-item-semantic-1"
DEFAULT_BATCH_RUN_ID = "batch-run-1"
DEFAULT_QUEUE_ID = "queue-row-1"


def _load_item_semantic_generator_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/item-semantic-generator/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.item_semantic_generator",
        init_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_item_semantic_generator_package()

from reco.application.item_semantic_generator import (  # noqa: E402
    InMemorySemanticCatalog,
    ItemSemanticGenerationContext,
    ItemSemanticGenerator,
    build_default_semantic_catalog,
)
from reco.application.item_semantic_generator.in_memory_repository import (  # noqa: E402
    InMemoryItemValidation,
    InMemorySemanticConfigVersion,
)
from reco.application.item_semantic_generator.models import (  # noqa: E402
    SemanticConceptRecord,
    SemanticRuleRecord,
)
from reco.infrastructure.external_ai.client import ScaffoldExternalAiClient  # noqa: E402
from reco.infrastructure.logger.logger import ScaffoldRecoLogger  # noqa: E402


def _sample_context(
    *,
    item_id: str = DEFAULT_ITEM_ID,
    item_description: str | None = "上質な包装の贈答用ギフトセット",
    item_name: str | None = None,
    skip_if_unchanged: bool = True,
) -> ItemSemanticGenerationContext:
    return ItemSemanticGenerationContext(
        trace_id=DEFAULT_TRACE_ID,
        batch_run_id=DEFAULT_BATCH_RUN_ID,
        item_generation_queue_id=DEFAULT_QUEUE_ID,
        item_id=item_id,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        item_name=item_name,
        item_description=item_description,
        skip_if_unchanged=skip_if_unchanged,
    )


def build_generator_with_registered_item(
    context: ItemSemanticGenerationContext,
    *,
    should_fail_upsert: bool = False,
    catalog: InMemorySemanticCatalog | None = None,
    logger: ScaffoldRecoLogger | None = None,
    llm_client: ScaffoldExternalAiClient | None = None,
) -> ItemSemanticGenerator:
    resolved_catalog = catalog or build_default_semantic_catalog()
    item_validation = InMemoryItemValidation()
    version_validation = InMemorySemanticConfigVersion()
    version_validation.register_version(context.semantic_config_version_id)
    item_validation.register_item(context.item_id)
    from reco.application.item_semantic_generator.in_memory_repository import (
        InMemoryItemSemanticRepository,
    )

    generator = ItemSemanticGenerator(
        catalog=resolved_catalog,
        item_validation=item_validation,
        semantic_config_version=version_validation,
        item_semantic_repository=InMemoryItemSemanticRepository(
            should_fail_on_upsert=should_fail_upsert,
        ),
        llm_client=llm_client or ScaffoldExternalAiClient(),
        logger=logger or ScaffoldRecoLogger(),
    )
    assert isinstance(generator.item_validation, InMemoryItemValidation)
    assert isinstance(generator.semantic_config_version, InMemorySemanticConfigVersion)
    return generator


def build_threshold_boundary_catalog() -> InMemorySemanticCatalog:
    """Catalog with rules at confidence 0.59 (excluded) and 0.60 (adopted)."""
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[
            SemanticConceptRecord("below_threshold", version_id),
            SemanticConceptRecord("at_threshold", version_id),
        ],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="低信頼",
                concept_code="below_threshold",
                confidence=0.59,
                source_types=("item_description",),
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="高信頼",
                concept_code="at_threshold",
                confidence=0.60,
                source_types=("item_description",),
            ),
        ],
    )


def build_below_threshold_only_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[SemanticConceptRecord("weak_concept", version_id)],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="微妙",
                concept_code="weak_concept",
                confidence=0.55,
                source_types=("item_description",),
            ),
        ],
    )


def build_dedupe_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[SemanticConceptRecord("formal_refined", version_id)],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="上品",
                concept_code="formal_refined",
                confidence=0.70,
                source_types=("item_description",),
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="phrase",
                match_value="落ち着",
                concept_code="formal_refined",
                confidence=0.92,
                source_types=("item_description",),
            ),
        ],
    )


def build_genre_tag_catalog() -> InMemorySemanticCatalog:
    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    return InMemorySemanticCatalog(
        concepts=[
            SemanticConceptRecord("formal_refined", version_id),
            SemanticConceptRecord("safe_classic", version_id),
        ],
        rules=[
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="スイーツ",
                concept_code="formal_refined",
                confidence=0.75,
                source_types=("item_genre",),
            ),
            SemanticRuleRecord(
                semantic_config_version_id=version_id,
                rule_type="keyword",
                match_value="ギフト",
                concept_code="safe_classic",
                confidence=0.72,
                source_types=("item_tag",),
            ),
        ],
    )
