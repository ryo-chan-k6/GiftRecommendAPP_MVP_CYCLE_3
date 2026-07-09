"""MOD-RECO-026 Item Semantic Generator smoke tests."""

from __future__ import annotations

import pytest

from conftest import (
    DEFAULT_ITEM_ID,
    _sample_context,
    build_generator_with_registered_item,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.item_semantic_generator import (
    GenerationStatus,
    ItemSemanticGenerationContext,
    ItemSemanticGeneratorError,
    SURFACE_ERROR_CODE,
)


def test_generate_item_semantic_extracts_from_description_and_upserts() -> None:
    context = _sample_context()
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    assert result.status == GenerationStatus.GENERATED
    assert result.item_semantic_id
    assert result.semantic_json is not None
    concepts = result.semantic_json["concepts"]
    assert len(concepts) == 1
    assert concepts[0]["concept_code"] == "formal_refined"
    assert concepts[0]["input_intent"] == "neutral"
    assert concepts[0]["confidence"] >= 0.60


def test_generate_item_semantic_allows_empty_concepts() -> None:
    context = _sample_context(item_description=None, item_name=None)
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    assert result.status == GenerationStatus.GENERATED
    assert result.semantic_json == {"concepts": []}


def test_generate_item_semantic_skips_when_input_unchanged() -> None:
    context = _sample_context(skip_if_unchanged=True)
    generator = build_generator_with_registered_item(context)

    first = generator.generate_item_semantic(context)
    second = generator.generate_item_semantic(context)

    assert first.status == GenerationStatus.GENERATED
    assert second.status == GenerationStatus.SKIPPED
    assert second.skip_reason == "semantic_input_unchanged"
    assert second.item_semantic_id == first.item_semantic_id


def test_generate_item_semantic_raises_for_missing_item() -> None:
    context = _sample_context(item_id="missing-item")
    generator = build_generator_with_registered_item(
        _sample_context(item_id=DEFAULT_ITEM_ID),
    )

    with pytest.raises(ItemSemanticGeneratorError) as exc_info:
        generator.generate_item_semantic(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_generate_item_semantic_applies_item_name_confidence_adjustment() -> None:
    context = _sample_context(
        item_description=None,
        item_name="定番ギフト",
    )
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    concepts = result.semantic_json["concepts"]
    assert len(concepts) == 1
    assert concepts[0]["concept_code"] == "safe_classic"
    assert concepts[0]["confidence"] == pytest.approx(0.67, abs=0.01)


def test_generate_item_semantic_ignores_negated_review() -> None:
    context = ItemSemanticGenerationContext(
        trace_id="trace-review",
        batch_run_id="batch-run-review",
        item_generation_queue_id="queue-review",
        item_id=DEFAULT_ITEM_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        review_texts=("思ったより安っぽい",),
    )
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    assert result.semantic_json == {"concepts": []}
