"""MOD-RECO-027 Item Feature Generator smoke tests."""

from __future__ import annotations

import math

import pytest

from conftest import (
    DEFAULT_FEATURE_INPUT_HASH,
    DEFAULT_ITEM_ID,
    _sample_context,
    build_generator_with_registered_item,
)
from reco.application.item_feature_generator import (
    GenerationStatus,
    ItemFeatureGeneratorError,
    NEUTRAL_BASE,
    SURFACE_ERROR_CODE,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES


def test_generate_item_features_with_empty_concepts_returns_neutral_base() -> None:
    context = _sample_context()
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    assert result.status == GenerationStatus.GENERATED
    assert result.feature_codes == MVP_FEATURE_CODES
    assert len(result.item_feature_ids) == len(MVP_FEATURE_CODES)
    assert all(result.features[code] == NEUTRAL_BASE for code in MVP_FEATURE_CODES)


def test_generate_item_features_applies_concept_feature_rules() -> None:
    context = _sample_context(
        concepts=[
            {
                "concept_code": "formal_refined",
                "confidence": 0.80,
                "source_type": "item_description",
                "input_intent": "neutral",
                "extraction_method": "rule",
            },
        ],
    )
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    assert result.status == GenerationStatus.GENERATED
    assert result.features["formality"] > NEUTRAL_BASE
    assert result.features["novelty"] < NEUTRAL_BASE


def test_generate_item_features_skips_when_hash_unchanged() -> None:
    context = _sample_context(skip_if_unchanged=True)
    generator = build_generator_with_registered_item(context)

    first = generator.generate_item_features(context)
    second = generator.generate_item_features(context)

    assert first.status == GenerationStatus.GENERATED
    assert second.status == GenerationStatus.SKIPPED
    assert second.skip_reason == "feature_input_hash_unchanged"
    assert second.item_feature_ids == first.item_feature_ids


def test_generate_item_features_raises_for_missing_item() -> None:
    context = _sample_context(item_id="missing-item")
    generator = build_generator_with_registered_item(
        _sample_context(item_id=DEFAULT_ITEM_ID),
    )

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_generate_item_features_raises_for_invalid_hash() -> None:
    context = _sample_context(feature_input_hash="not-a-valid-hash")
    generator = build_generator_with_registered_item(context)

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert "feature_input_hash" in exc_info.value.message


def test_generate_item_features_raises_for_nan_raw() -> None:
    context = _sample_context(
        concepts=[
            {
                "concept_code": "formal_refined",
                "confidence": math.inf,
                "source_type": "item_description",
                "input_intent": "neutral",
                "extraction_method": "rule",
            },
        ],
    )
    generator = build_generator_with_registered_item(context)

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert "non-finite" in exc_info.value.message
