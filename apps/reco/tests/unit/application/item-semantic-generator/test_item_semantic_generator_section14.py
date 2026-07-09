"""MOD-RECO-026 §14 unit test coverage (module spec No.1–19 unit 観点).

| §14 No | 観点 | テスト関数 / 参照 |
| -----: | ---- | ----------------- |
| 1 | 正常系（item_description） | smoke: `test_generate_item_semantic_extracts_from_description_and_upserts` |
| 2 | 正常系（item_name） | `test_extracts_keyword_concept_from_item_name` |
| 3 | 正常系（genre / tag） | `test_extracts_auxiliary_concepts_from_genre_and_tags` |
| 4 | 境界値（入力全空） | smoke: `test_generate_item_semantic_allows_empty_concepts` |
| 5 | 境界値（0 件 Concept） | `test_returns_empty_concepts_when_only_below_threshold_hits` |
| 6 | 境界値（confidence 閾値） | `test_applies_confidence_adoption_threshold` |
| 7 | 重複統合 | `test_dedupes_concepts_by_max_confidence` |
| 8 | 否定レビュー | smoke: `test_generate_item_semantic_ignores_negated_review` |
| 9 | source_type 補正 | smoke: `test_generate_item_semantic_applies_item_name_confidence_adjustment` |
| 10 | input_intent | `test_item_concepts_use_neutral_input_intent` |
| 11 | version 整合 | `test_persisted_row_matches_semantic_config_version_id` |
| 12 | skip | smoke: `test_generate_item_semantic_skips_when_input_unchanged` |
| 13 | 例外系（Item 不整合） | smoke: `test_generate_item_semantic_raises_for_missing_item` |
| 14 | 例外系（LLM 失敗） | `test_raises_grs_bat_008_when_llm_fails_without_upsert` |
| 15 | DB 永続化 | out of scope（integration） |
| 16 | Batch 連携 | out of scope（integration） |
| 17 | ログ | `test_emits_structured_log_with_trace_id_without_input_text` |
| 18 | LLM on-demand（スキップ） | `test_skips_llm_when_rule_concepts_are_sufficient` |
| 19 | LLM on-demand（呼び出し） | `test_invokes_llm_once_when_description_has_no_rule_hits` |
| 20 | Orchestrator 非連携 | out of scope（architecture） |
| 21 | Upsert 冪等 | out of scope（integration） |
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest

from conftest import (
    DEFAULT_ITEM_ID,
    DEFAULT_TRACE_ID,
    _sample_context,
    build_below_threshold_only_catalog,
    build_dedupe_catalog,
    build_genre_tag_catalog,
    build_generator_with_registered_item,
    build_threshold_boundary_catalog,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.item_semantic_generator import (
    GenerationStatus,
    ItemSemanticGenerationContext,
    ItemSemanticGeneratorError,
    SURFACE_ERROR_CODE,
)
from reco.infrastructure.external_ai.client import ExternalAiResponse, ScaffoldExternalAiClient
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_LLM_DESCRIPTION = (
    "記念日に贈りたい特別な体験を届けるギフトセット全体の説明文です"
)


# §14 No.2 正常系（item_name）
def test_extracts_keyword_concept_from_item_name() -> None:
    context = _sample_context(item_description=None, item_name="定番ギフト")
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    concepts = result.semantic_json["concepts"]
    assert len(concepts) == 1
    assert concepts[0]["concept_code"] == "safe_classic"
    assert concepts[0]["source_type"] == "item_name"


# §14 No.3 正常系（genre / tag）
def test_extracts_auxiliary_concepts_from_genre_and_tags() -> None:
    context = ItemSemanticGenerationContext(
        trace_id=DEFAULT_TRACE_ID,
        batch_run_id="batch-run-genre-tag",
        item_generation_queue_id="queue-genre-tag",
        item_id=DEFAULT_ITEM_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        genre_name="スイーツ",
        tags=("ギフト",),
    )
    generator = build_generator_with_registered_item(
        context,
        catalog=build_genre_tag_catalog(),
    )

    result = generator.generate_item_semantic(context)

    concept_codes = {concept["concept_code"] for concept in result.semantic_json["concepts"]}
    assert concept_codes == {"formal_refined", "safe_classic"}


# §14 No.5 境界値（0 件 Concept）— 閾値未満のみ
def test_returns_empty_concepts_when_only_below_threshold_hits() -> None:
    context = _sample_context(item_description="微妙な贈り物")
    generator = build_generator_with_registered_item(
        context,
        catalog=build_below_threshold_only_catalog(),
    )

    result = generator.generate_item_semantic(context)

    assert result.status == GenerationStatus.GENERATED
    assert result.semantic_json == {"concepts": []}


# §14 No.6 境界値（confidence 閾値）— 0.59 除外 / 0.60 採用
def test_applies_confidence_adoption_threshold() -> None:
    context = _sample_context(item_description="低信頼と高信頼の説明文")
    generator = build_generator_with_registered_item(
        context,
        catalog=build_threshold_boundary_catalog(),
    )

    result = generator.generate_item_semantic(context)

    concept_codes = {concept["concept_code"] for concept in result.semantic_json["concepts"]}
    assert concept_codes == {"at_threshold"}
    assert all(concept["confidence"] >= 0.60 for concept in result.semantic_json["concepts"])


# §14 No.7 重複統合 — 同一 concept_code は confidence 最大で 1 件
def test_dedupes_concepts_by_max_confidence() -> None:
    context = _sample_context(item_description="上品で落ち着いたギフト")
    generator = build_generator_with_registered_item(
        context,
        catalog=build_dedupe_catalog(),
    )

    result = generator.generate_item_semantic(context)

    concepts = result.semantic_json["concepts"]
    assert len(concepts) == 1
    assert concepts[0]["concept_code"] == "formal_refined"
    assert concepts[0]["confidence"] == 0.92


# §14 No.10 input_intent — Item 側 Concept は原則 neutral
def test_item_concepts_use_neutral_input_intent() -> None:
    context = _sample_context()
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    for concept in result.semantic_json["concepts"]:
        assert concept["input_intent"] == "neutral"


# §14 No.11 version 整合
def test_persisted_row_matches_semantic_config_version_id() -> None:
    context = _sample_context(skip_if_unchanged=False)
    generator = build_generator_with_registered_item(context)

    result = generator.generate_item_semantic(context)

    persisted = generator.item_semantic_repository.find_by_item_and_version(
        item_id=context.item_id,
        semantic_config_version_id=context.semantic_config_version_id,
    )
    assert persisted is not None
    assert persisted.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert result.item_semantic_id == persisted.item_semantic_id


@dataclass
class _FailingExternalAiClient:
    generate_calls: list[dict[str, str]] = field(default_factory=list)

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse:
        self.generate_calls.append({"prompt": prompt, "purpose": purpose})
        raise RuntimeError("external AI unavailable")


# §14 No.14 例外系（LLM 失敗）— unit 観点
def test_raises_grs_bat_008_when_llm_fails_without_upsert() -> None:
    context = ItemSemanticGenerationContext(
        trace_id=DEFAULT_TRACE_ID,
        batch_run_id="batch-run-llm-fail",
        item_generation_queue_id="queue-llm-fail",
        item_id=DEFAULT_ITEM_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        item_description=_LLM_DESCRIPTION,
        skip_if_unchanged=False,
    )
    llm_client = _FailingExternalAiClient()
    generator = build_generator_with_registered_item(context, llm_client=llm_client)

    with pytest.raises(ItemSemanticGeneratorError) as exc_info:
        generator.generate_item_semantic(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert exc_info.value.internal_error_code == "GRS-LLM-100"
    persisted = generator.item_semantic_repository.find_by_item_and_version(
        item_id=context.item_id,
        semantic_config_version_id=context.semantic_config_version_id,
    )
    assert persisted is None


# §14 No.17 ログ — trace_id を含み入力全文・secret を含まない
def test_emits_structured_log_with_trace_id_without_input_text() -> None:
    item_description = "上質な包装の贈答用ギフトセット"
    context = _sample_context(item_description=item_description, skip_if_unchanged=False)
    logger = ScaffoldRecoLogger()
    generator = build_generator_with_registered_item(context, logger=logger)

    generator.generate_item_semantic(context)

    completion_logs = [
        record
        for record in logger.records
        if record.event == "item_semantic_generation_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == DEFAULT_TRACE_ID
    serialized = json.dumps(log_record.attributes, ensure_ascii=False)
    assert item_description not in serialized
    assert "api_key" not in serialized.lower()


# §14 No.18 LLM on-demand（スキップ）— Rule で十分な場合 LLM 未呼び出し
def test_skips_llm_when_rule_concepts_are_sufficient() -> None:
    context = _sample_context(
        item_description="上質な包装の贈答用ギフトセット",
        skip_if_unchanged=False,
    )
    llm_client = ScaffoldExternalAiClient()
    generator = build_generator_with_registered_item(context, llm_client=llm_client)

    generator.generate_item_semantic(context)

    assert llm_client.generate_calls == []


# §14 No.19 LLM on-demand（呼び出し）— 説明文ありかつ Rule 0 件時に LLM を 1 回呼ぶ
def test_invokes_llm_once_when_description_has_no_rule_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = ItemSemanticGenerationContext(
        trace_id=DEFAULT_TRACE_ID,
        batch_run_id="batch-run-llm-call",
        item_generation_queue_id="queue-llm-call",
        item_id=DEFAULT_ITEM_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        item_description=_LLM_DESCRIPTION,
        skip_if_unchanged=False,
    )
    llm_client = ScaffoldExternalAiClient()
    generator = build_generator_with_registered_item(context, llm_client=llm_client)

    def _fake_generate(prompt: str, *, purpose: str) -> ExternalAiResponse:
        llm_client.generate_calls.append({"prompt": prompt, "purpose": purpose})
        return ExternalAiResponse(
            text=json.dumps(
                {
                    "concepts": [
                        {
                            "concept_code": "prestigious_quality",
                            "confidence": 0.78,
                            "input_intent": "neutral",
                            "evidence_texts": [_LLM_DESCRIPTION],
                            "source_type": "item_description",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            model="test",
        )

    monkeypatch.setattr(llm_client, "generate", _fake_generate)

    result = generator.generate_item_semantic(context)

    assert len(llm_client.generate_calls) == 1
    assert llm_client.generate_calls[0]["purpose"] == "item_semantic_extraction"
    concepts = result.semantic_json["concepts"]
    assert len(concepts) == 1
    assert concepts[0]["concept_code"] == "prestigious_quality"
    assert concepts[0]["extraction_method"] == "llm"
