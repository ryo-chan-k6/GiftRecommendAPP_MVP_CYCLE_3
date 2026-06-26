"""MOD-RECO-004 User Semantic Extractor smoke tests."""

from __future__ import annotations

import json

import pytest

from conftest import (
    DEFAULT_RUN_ID,
    _sample_context,
    build_extractor_with_registered_run,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.user_semantic_extractor import (
    SemanticExtractError,
    SURFACE_ERROR_CODE,
)
from reco.domain import (
    NgCondition,
    NonPreferredCondition,
    RecommendationRequest,
)
from reco.infrastructure.external_ai.client import ScaffoldExternalAiClient


def test_execute_extracts_preferred_concept_and_persists_user_semantic() -> None:
    context = _sample_context()
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.user_semantic_id
    assert result.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    assert len(result.concepts) == 1
    assert result.concepts[0].concept_code == "formal_refined"
    assert result.concepts[0].input_intent == "prefer"
    assert result.concepts[0].confidence >= 0.60
    assert "MOD-RECO-004" in updated.completed_modules

    persisted = extractor.user_semantic_repository.rows[DEFAULT_RUN_ID]
    assert persisted.extracted_semantic_json["concepts"][0]["concept_code"] == "formal_refined"


def test_execute_with_empty_text_returns_empty_concepts() -> None:
    request = RecommendationRequest(
        request_id="req-empty",
        relationship=_sample_context().recommendation_request.relationship,
        occasion=_sample_context().recommendation_request.occasion,
    )
    context = _sample_context(request=request, run_id="run-empty")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result.concepts == ()
    assert extractor.user_semantic_repository.exists_for_run("run-empty")


def test_execute_separates_ng_condition_into_hard_filter_candidates() -> None:
    request = RecommendationRequest(
        request_id="req-ng",
        relationship=_sample_context().recommendation_request.relationship,
        occasion=_sample_context().recommendation_request.occasion,
        ng_condition=NgCondition(
            ng_keywords=("アルコール",),
            ng_categories=("tobacco",),
        ),
    )
    context = _sample_context(request=request, run_id="run-ng")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result.concepts == ()
    assert len(result.hard_filter_candidates) == 2
    assert {candidate.filter_type for candidate in result.hard_filter_candidates} == {
        "attribute",
        "category",
    }


def test_execute_raises_when_run_version_mismatch() -> None:
    context = _sample_context(run_id="run-mismatch")
    extractor = build_extractor_with_registered_run(context)
    extractor.run_validation.register_run("run-mismatch", "other-version")

    with pytest.raises(SemanticExtractError) as exc_info:
        extractor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


def test_execute_invokes_llm_once_for_free_text_without_rule_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = RecommendationRequest(
        request_id="req-free",
        relationship=_sample_context().recommendation_request.relationship,
        occasion=_sample_context().recommendation_request.occasion,
        free_text="特別な日にふさわしい贈り物",
    )
    context = _sample_context(request=request, run_id="run-free")
    extractor = build_extractor_with_registered_run(context)

    llm_client = ScaffoldExternalAiClient()
    extractor.llm_client = llm_client

    def _fake_generate(prompt: str, *, purpose: str):
        llm_client.generate_calls.append({"prompt": prompt, "purpose": purpose})
        from reco.infrastructure.external_ai.client import ExternalAiResponse

        return ExternalAiResponse(
            text=json.dumps(
                {
                    "concepts": [
                        {
                            "concept_code": "warm_heartfelt",
                            "confidence": 0.72,
                            "input_intent": "prefer",
                            "evidence_texts": ["特別な日にふさわしい贈り物"],
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            model="test",
        )

    monkeypatch.setattr(llm_client, "generate", _fake_generate)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert len(llm_client.generate_calls) == 1
    assert result.concepts[0].concept_code == "warm_heartfelt"
    assert result.concepts[0].extraction_method == "llm"


def test_non_preferred_condition_extracts_avoid_intent() -> None:
    request = RecommendationRequest(
        request_id="req-avoid",
        relationship=_sample_context().recommendation_request.relationship,
        occasion=_sample_context().recommendation_request.occasion,
        non_preferred_condition=NonPreferredCondition(
            non_preferred_keywords=("カジュアル",),
        ),
    )
    context = _sample_context(request=request, run_id="run-avoid")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert len(result.concepts) == 1
    assert result.concepts[0].concept_code == "too_casual"
    assert result.concepts[0].input_intent == "avoid"
