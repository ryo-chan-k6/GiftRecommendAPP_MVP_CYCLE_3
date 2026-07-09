"""MOD-RECO-027 §14 unit test coverage (module spec No.1–13, 16, 21–22 unit 観点).

| §14 No | 観点 | テスト関数 / 参照 |
| -----: | ---- | ----------------- |
| 1 | 正常系（Concept あり） | smoke: `test_generate_item_features_applies_concept_feature_rules` |
| 2 | 正常系（Concept 0 件） | smoke: `test_generate_item_features_with_empty_concepts_returns_neutral_base` |
| 3 | 統合式 | `test_applies_neutral_base_plus_delta_weight_confidence_formula` |
| 4 | source_weight | `test_applies_source_weight_difference_between_description_and_name` |
| 5 | polarity | `test_applies_concept_feature_rule_polarity_to_delta_sign` |
| 6 | raw clip | `test_clips_raw_values_outside_zero_to_one_range` |
| 7 | 境界値（NaN） | smoke: `test_generate_item_features_raises_for_nan_raw` |
| 8 | 8 軸完全性 | `test_generates_all_eight_mvp_feature_axes` |
| 9 | 冪等キー | `test_persists_feature_input_hash_and_normalization_version_id` |
| 10 | normalized 未設定 | `test_leaves_normalized_feature_value_null_after_upsert` |
| 11 | skip | smoke: `test_generate_item_features_skips_when_hash_unchanged` |
| 12 | 例外系（item_semantic 欠落） | `test_raises_grs_bat_008_when_item_semantic_is_missing` |
| 13 | 例外系（normalization_rule 欠落） | `test_raises_grs_bat_008_when_normalization_binding_missing` |
| 14 | DB 永続化 | out of scope（integration） |
| 15 | Batch 連携 | out of scope（integration） |
| 16 | ログ | `test_emits_structured_log_with_trace_id_without_secrets` |
| 17 | Orchestrator 非連携 | out of scope（architecture） |
| 18 | hash 再算出なし | `test_passes_through_feature_input_hash_without_recomputation` |
| 19 | 正規化非実施 | No.10 と smoke で間接確認 |
| 20 | Upsert 冪等 | out of scope（integration） |
| 21 | Metadata 直接 Delta 非適用 | `test_ignores_context_metadata_when_semantic_has_no_concepts` |
| 22 | shared-logic 利用 | `test_integrates_deltas_via_shared_logic_bridge` |
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from conftest import (
    DEFAULT_FEATURE_INPUT_HASH,
    DEFAULT_ITEM_ID,
    DEFAULT_TRACE_ID,
    _sample_context,
    build_generator_with_registered_item,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.item_feature_generator import (
    GenerationStatus,
    InMemoryConceptFeatureRuleRepository,
    InMemoryItemFeatureRepository,
    InMemoryNormalizationRuleRepository,
    ItemFeatureGeneratorError,
    NEUTRAL_BASE,
    SURFACE_ERROR_CODE,
)
from reco.application.item_feature_generator.constants import (
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
)
from reco.application.item_feature_generator.models import ConceptFeatureRuleRecord
from reco.domain.gift_meaning.features import FEATURE_VALUE_MAX, FEATURE_VALUE_MIN, MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _single_concept_context(
    *,
    concept_code: str = "formal_refined",
    confidence: float = 0.80,
    source_type: str = "item_description",
) -> object:
    return _sample_context(
        skip_if_unchanged=False,
        concepts=[
            {
                "concept_code": concept_code,
                "confidence": confidence,
                "source_type": source_type,
                "input_intent": "neutral",
                "extraction_method": "rule",
            },
        ],
    )


def _custom_rules_repo(
    rules: tuple[ConceptFeatureRuleRecord, ...],
) -> InMemoryConceptFeatureRuleRepository:
    return InMemoryConceptFeatureRuleRepository(rules=rules)


# §14 No.3 統合式 — neutral_base + delta × source_weight × confidence
def test_applies_neutral_base_plus_delta_weight_confidence_formula() -> None:
    context = _single_concept_context(confidence=0.80, source_type="item_description")
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    # formal_refined -> formality: delta=0.25, weight=1.0, confidence=0.8
    expected_formality = NEUTRAL_BASE + (0.25 * 1.0 * 0.80)
    assert result.features["formality"] == pytest.approx(expected_formality)


# §14 No.4 source_weight — item_description(1.0) と item_name(0.8) の差
def test_applies_source_weight_difference_between_description_and_name() -> None:
    description_context = _single_concept_context(
        confidence=1.0,
        source_type="item_description",
    )
    name_context = _single_concept_context(
        confidence=1.0,
        source_type="item_name",
    )
    description_generator = build_generator_with_registered_item(description_context)
    name_generator = build_generator_with_registered_item(name_context)

    description_result = description_generator.generate_item_features(description_context)
    name_result = name_generator.generate_item_features(name_context)

    description_formality = description_result.features["formality"]
    name_formality = name_result.features["formality"]
    assert description_formality > name_formality
    assert description_formality == pytest.approx(NEUTRAL_BASE + 0.25)
    assert name_formality == pytest.approx(NEUTRAL_BASE + (0.25 * 0.80))


# §14 No.5 polarity — negative polarity が減算方向へ反映される
def test_applies_concept_feature_rule_polarity_to_delta_sign() -> None:
    context = _single_concept_context(confidence=1.0, source_type="item_description")
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    # formal_refined -> novelty: delta=0.05, polarity=negative
    assert result.features["novelty"] == pytest.approx(NEUTRAL_BASE - 0.05)


# §14 No.6 raw clip — 0.0 / 1.0 外の raw が clip される
def test_clips_raw_values_outside_zero_to_one_range() -> None:
    rules = (
        ConceptFeatureRuleRecord(
            "clip_probe",
            "formality",
            2.0,
            POLARITY_POSITIVE,
        ),
        ConceptFeatureRuleRecord(
            "clip_probe",
            "safety",
            2.0,
            POLARITY_NEGATIVE,
        ),
    )
    context = _sample_context(
        skip_if_unchanged=False,
        concepts=[
            {
                "concept_code": "clip_probe",
                "confidence": 1.0,
                "source_type": "item_description",
                "input_intent": "neutral",
                "extraction_method": "rule",
            },
        ],
    )
    generator = build_generator_with_registered_item(
        context,
        concept_rules=_custom_rules_repo(rules),
    )

    result = generator.generate_item_features(context)

    assert result.features["formality"] == FEATURE_VALUE_MAX
    assert result.features["safety"] == FEATURE_VALUE_MIN


# §14 No.8 8 軸完全性
def test_generates_all_eight_mvp_feature_axes() -> None:
    context = _sample_context(skip_if_unchanged=False)
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    assert result.feature_codes == MVP_FEATURE_CODES
    assert len(result.features) == len(MVP_FEATURE_CODES)
    assert len(result.item_feature_ids) == len(MVP_FEATURE_CODES)
    for code in MVP_FEATURE_CODES:
        assert code in result.features


# §14 No.9 冪等キー — feature_input_hash / feature_normalization_version_id が行に記録される
def test_persists_feature_input_hash_and_normalization_version_id() -> None:
    context = _sample_context(skip_if_unchanged=False)
    repository = InMemoryItemFeatureRepository()
    generator = build_generator_with_registered_item(
        context,
        item_feature_repository=repository,
    )

    result = generator.generate_item_features(context)

    persisted = repository.find_by_idempotent_key(
        item_id=context.item_id,
        semantic_config_version_id=context.semantic_config_version_id,
        feature_input_hash=context.feature_input_hash,
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    )
    assert len(persisted) == len(MVP_FEATURE_CODES)
    assert result.feature_input_hash == DEFAULT_FEATURE_INPUT_HASH
    assert result.feature_normalization_version_id == DEFAULT_FEATURE_NORMALIZATION_VERSION_ID
    for row in persisted:
        assert row.feature_input_hash == DEFAULT_FEATURE_INPUT_HASH
        assert row.feature_normalization_version_id == DEFAULT_FEATURE_NORMALIZATION_VERSION_ID


# §14 No.10 normalized 未設定 — Upsert 後 normalized_feature_value IS NULL
def test_leaves_normalized_feature_value_null_after_upsert() -> None:
    context = _sample_context(skip_if_unchanged=False)
    repository = InMemoryItemFeatureRepository()
    generator = build_generator_with_registered_item(
        context,
        item_feature_repository=repository,
    )

    generator.generate_item_features(context)

    persisted = repository.find_by_idempotent_key(
        item_id=context.item_id,
        semantic_config_version_id=context.semantic_config_version_id,
        feature_input_hash=context.feature_input_hash,
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    )
    assert all(row.normalized_feature_value is None for row in persisted)
    assert all(row.raw_feature_value is not None for row in persisted)


# §14 No.12 例外系（item_semantic 欠落）
def test_raises_grs_bat_008_when_item_semantic_is_missing() -> None:
    context = _sample_context(skip_if_unchanged=False)
    object.__setattr__(context, "item_semantic", None)
    generator = build_generator_with_registered_item(context)

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "item_semantic is required" in exc_info.value.message


def test_raises_grs_bat_008_when_semantic_json_has_no_concepts() -> None:
    context = _sample_context(
        skip_if_unchanged=False,
        concepts=None,
    )
    object.__setattr__(
        context.item_semantic,
        "semantic_json",
        {},
    )
    generator = build_generator_with_registered_item(context)

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.13 例外系（normalization_rule 欠落）
def test_raises_grs_bat_008_when_normalization_binding_missing() -> None:
    context = _sample_context(skip_if_unchanged=False)
    normalization_rules = InMemoryNormalizationRuleRepository(binding=None)
    generator = build_generator_with_registered_item(
        context,
        normalization_rules=normalization_rules,
    )

    with pytest.raises(ItemFeatureGeneratorError) as exc_info:
        generator.generate_item_features(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.internal_error_code == "GRS-CFG-006"
    assert "normalization_rule binding not found" in exc_info.value.message


# §14 No.16 ログ — trace_id を含み secret を含まない
def test_emits_structured_log_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        skip_if_unchanged=False,
        item_id=DEFAULT_ITEM_ID,
    )
    logger = ScaffoldRecoLogger()
    generator = build_generator_with_registered_item(context, logger=logger)

    generator.generate_item_features(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "item_feature_generation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == DEFAULT_TRACE_ID
    serialized = json.dumps(log_record.attributes, ensure_ascii=False)
    assert "api_key" not in serialized.lower()
    assert log_record.attributes["status"] == GenerationStatus.GENERATED.value


# §14 No.18 hash 再算出なし — context の hash をそのまま結果・永続化へ渡す
def test_passes_through_feature_input_hash_without_recomputation() -> None:
    custom_hash = "b" * 64
    context = _sample_context(
        feature_input_hash=custom_hash,
        skip_if_unchanged=False,
    )
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    assert result.feature_input_hash == custom_hash
    assert result.status == GenerationStatus.GENERATED


# §14 No.21 Metadata 直接 Delta 非適用 — semantic concepts が空なら metadata だけでは raw を動かさない
def test_ignores_context_metadata_when_semantic_has_no_concepts() -> None:
    context = _sample_context(
        skip_if_unchanged=False,
        concepts=[],
    )
    object.__setattr__(context, "item_name", "定番ギフト")
    object.__setattr__(context, "genre_name", "スイーツ")
    object.__setattr__(context, "tags", ("ギフト",))
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_features(context)

    assert result.status == GenerationStatus.GENERATED
    assert all(result.features[code] == NEUTRAL_BASE for code in MVP_FEATURE_CODES)


# §14 No.22 shared-logic 利用 — bridge が shared-logic の integrate / clip を呼ぶ
def test_integrates_deltas_via_shared_logic_bridge() -> None:
    context = _single_concept_context(confidence=1.0, source_type="item_description")
    generator = build_generator_with_registered_item(context)

    with patch(
        "reco.application.item_feature_generator.generator.integrate_feature_deltas",
        wraps=__import__(
            "reco.application.item_feature_generator.shared_logic_bridge",
            fromlist=["integrate_feature_deltas"],
        ).integrate_feature_deltas,
    ) as integrate_mock, patch(
        "reco.application.item_feature_generator.generator.clip_feature_vector",
        wraps=__import__(
            "reco.application.item_feature_generator.shared_logic_bridge",
            fromlist=["clip_feature_vector"],
        ).clip_feature_vector,
    ) as clip_mock:
        result = generator.generate_item_features(context)

    assert integrate_mock.called
    assert clip_mock.called
    assert result.status == GenerationStatus.GENERATED
