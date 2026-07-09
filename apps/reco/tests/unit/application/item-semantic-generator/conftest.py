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
    ItemSemanticGenerationContext,
    ItemSemanticGenerator,
    build_scaffold_item_semantic_generator,
)
from reco.application.item_semantic_generator.in_memory_repository import (  # noqa: E402
    InMemoryItemValidation,
    InMemorySemanticConfigVersion,
)


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
) -> ItemSemanticGenerator:
    generator = build_scaffold_item_semantic_generator(
        should_fail_upsert=should_fail_upsert,
    )
    assert isinstance(generator.item_validation, InMemoryItemValidation)
    assert isinstance(generator.semantic_config_version, InMemorySemanticConfigVersion)
    generator.item_validation.register_item(context.item_id)
    generator.semantic_config_version.register_version(context.semantic_config_version_id)
    return generator
