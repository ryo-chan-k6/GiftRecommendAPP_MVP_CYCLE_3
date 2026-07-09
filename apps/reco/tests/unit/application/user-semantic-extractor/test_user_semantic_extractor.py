"""MOD-RECO-004 User Semantic Extractor unit tests (module spec §14)."""

from __future__ import annotations

import json

import pytest

from conftest import (
    DEFAULT_RUN_ID,
    _sample_context,
    build_below_threshold_only_catalog,
    build_dedupe_catalog,
    build_extractor_with_registered_run,
    build_threshold_boundary_catalog,
)
from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
from reco.application.user_semantic_extractor import (
    SemanticExtractError,
    SURFACE_ERROR_CODE,
)
from reco.domain import (
    NgCondition,
    NonPreferredCondition,
    PreferredCondition,
    RecommendationRequest,
)
from reco.infrastructure.external_ai.client import (
    ExternalAiResponse,
    ScaffoldExternalAiClient,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _request_with_preferred_text(text: str, *, request_id: str = "req-semantic-1") -> RecommendationRequest:
    base = _sample_context().recommendation_request
    return RecommendationRequest(
        request_id=request_id,
        relationship=base.relationship,
        occasion=base.occasion,
        preferred_condition=PreferredCondition(preferred_text=text),
    )


# §14 No.1 正常系（preferred）
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


# §14 No.2 正常系（non_preferred）
def test_non_preferred_condition_extracts_avoid_intent() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-avoid",
        relationship=base.relationship,
        occasion=base.occasion,
        non_preferred_condition=NonPreferredCondition(
            non_preferred_keywords=("カジュアル",),
        ),
    )
    context = _sample_context(request=request, run_id="run-avoid")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert len(result.concepts) == 1
    assert result.concepts[0].concept_code == "too_casual"
    assert result.concepts[0].input_intent == "avoid"


# §14 No.3 正常系（free_text）— LLM モック
def test_execute_invokes_llm_once_for_free_text_without_rule_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-free",
        relationship=base.relationship,
        occasion=base.occasion,
        free_text="特別な日にふさわしい贈り物",
    )
    context = _sample_context(request=request, run_id="run-free")
    llm_client = ScaffoldExternalAiClient()
    extractor = build_extractor_with_registered_run(context, llm_client=llm_client)

    def _fake_generate(prompt: str, *, purpose: str) -> ExternalAiResponse:
        llm_client.generate_calls.append({"prompt": prompt, "purpose": purpose})
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
    assert result is not None
    assert len(llm_client.generate_calls) == 1
    assert result.concepts[0].concept_code == "warm_heartfelt"
    assert result.concepts[0].extraction_method == "llm"


# §14 No.4 境界値（入力全空）
def test_execute_with_empty_text_returns_empty_concepts() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-empty",
        relationship=base.relationship,
        occasion=base.occasion,
    )
    context = _sample_context(request=request, run_id="run-empty")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.concepts == ()
    assert extractor.user_semantic_repository.exists_for_run("run-empty")


# §14 No.5 境界値（0 件 Concept）— 閾値未満のみ
def test_execute_returns_empty_concepts_when_only_below_threshold_hits() -> None:
    request = _request_with_preferred_text("微妙な贈り物", request_id="req-weak")
    context = _sample_context(request=request, run_id="run-weak")
    extractor = build_extractor_with_registered_run(
        context,
        catalog=build_below_threshold_only_catalog(),
    )

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.concepts == ()
    assert extractor.user_semantic_repository.exists_for_run("run-weak")


# §14 No.6 境界値（confidence 閾値）— 0.59 除外 / 0.60 採用
def test_execute_applies_confidence_adoption_threshold() -> None:
    request = _request_with_preferred_text("低信頼と高信頼", request_id="req-threshold")
    context = _sample_context(request=request, run_id="run-threshold")
    extractor = build_extractor_with_registered_run(
        context,
        catalog=build_threshold_boundary_catalog(),
    )

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    concept_codes = {concept.concept_code for concept in result.concepts}
    assert concept_codes == {"at_threshold"}
    assert all(concept.confidence >= 0.60 for concept in result.concepts)


# §14 No.7 重複統合 — 同一 concept_code は confidence 最大で 1 件
def test_execute_dedupes_concepts_by_max_confidence() -> None:
    request = _request_with_preferred_text("上品で落ち着いたもの", request_id="req-dedupe")
    context = _sample_context(request=request, run_id="run-dedupe")
    extractor = build_extractor_with_registered_run(
        context,
        catalog=build_dedupe_catalog(),
    )

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert len(result.concepts) == 1
    assert result.concepts[0].concept_code == "formal_refined"
    assert result.concepts[0].confidence == 0.92


# §14 No.8 ng 分離
def test_execute_separates_ng_condition_into_hard_filter_candidates() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-ng",
        relationship=base.relationship,
        occasion=base.occasion,
        ng_condition=NgCondition(
            ng_keywords=("アルコール",),
            ng_categories=("tobacco",),
        ),
    )
    context = _sample_context(request=request, run_id="run-ng")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.concepts == ()
    assert len(result.hard_filter_candidates) == 2
    assert {candidate.filter_type for candidate in result.hard_filter_candidates} == {
        "attribute",
        "category",
    }
    extracted_json = extractor.user_semantic_repository.rows["run-ng"].extracted_semantic_json
    assert extracted_json == {"concepts": []}


# §14 No.9 preferred / non_preferred 区別
def test_preferred_keywords_do_not_match_non_preferred_rules() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-prefer-only",
        relationship=base.relationship,
        occasion=base.occasion,
        preferred_condition=PreferredCondition(
            preferred_keywords=("カジュアル",),
        ),
    )
    context = _sample_context(request=request, run_id="run-prefer-only")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.concepts == ()
    assert all(concept.input_intent != "avoid" for concept in result.concepts)


# §14 No.10 version 整合
def test_execute_sets_semantic_config_version_id_from_execution_context() -> None:
    context = _sample_context(run_id="run-version")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert result.semantic_config_version_id == context.config_versions["semantic_config_version_id"]
    persisted = extractor.user_semantic_repository.rows["run-version"]
    assert persisted.semantic_config_version_id == DEFAULT_SEMANTIC_CONFIG_VERSION_ID


# §14 No.11 例外系（Run 不整合）— version 不一致
def test_execute_raises_when_run_version_mismatch() -> None:
    context = _sample_context(run_id="run-mismatch")
    extractor = build_extractor_with_registered_run(context)
    extractor.run_validation.register_run("run-mismatch", "other-version")

    with pytest.raises(SemanticExtractError) as exc_info:
        extractor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE


# §14 No.11 例外系（Run 不整合）— Run 未存在
def test_execute_raises_when_recommendation_run_not_found() -> None:
    context = _sample_context(run_id="run-missing")
    extractor = build_extractor_with_registered_run(context, register_run=False)

    with pytest.raises(SemanticExtractError) as exc_info:
        extractor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "not found" in exc_info.value.message


# §14 No.12 例外系（重複 INSERT）
def test_execute_raises_on_duplicate_insert_for_same_run() -> None:
    context = _sample_context(run_id="run-dup")
    extractor = build_extractor_with_registered_run(context)

    extractor.execute(context)

    with pytest.raises(SemanticExtractError) as exc_info:
        extractor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert "already exists" in exc_info.value.message


# §14 No.13 例外系（LLM 失敗）
def test_execute_raises_grs_rec_004_when_llm_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-llm-fail",
        relationship=base.relationship,
        occasion=base.occasion,
        free_text="LLM が必要な自由文",
    )
    context = _sample_context(request=request, run_id="run-llm-fail")
    llm_client = ScaffoldExternalAiClient()
    extractor = build_extractor_with_registered_run(context, llm_client=llm_client)

    def _raise_generate(prompt: str, *, purpose: str) -> ExternalAiResponse:
        raise RuntimeError("external AI unavailable")

    monkeypatch.setattr(llm_client, "generate", _raise_generate)

    with pytest.raises(SemanticExtractError) as exc_info:
        extractor.execute(context)

    assert exc_info.value.error_code == SURFACE_ERROR_CODE
    assert not extractor.user_semantic_repository.exists_for_run("run-llm-fail")


# §14 No.16 ログ — trace_id を含み入力全文を含まない
def test_execute_emits_structured_log_with_trace_id_without_input_text() -> None:
    preferred_text = "上品で落ち着いたもの"
    request = _request_with_preferred_text(preferred_text, request_id="req-log")
    context = _sample_context(request=request, run_id="run-log")
    logger = ScaffoldRecoLogger()
    extractor = build_extractor_with_registered_run(context, logger=logger)

    extractor.execute(context)

    completion_logs = [
        record for record in logger.records if record.event == "semantic_extraction_completed"
    ]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == context.trace_id
    assert log_record.context.run_id == "run-log"
    serialized = json.dumps(log_record.attributes, ensure_ascii=False)
    assert preferred_text not in serialized
    assert "api_key" not in serialized.lower()


# §14 No.18 LLM on-demand（スキップ）— Rule で十分な場合 LLM 未呼び出し
def test_execute_skips_llm_when_rule_concepts_are_sufficient() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-skip-llm",
        relationship=base.relationship,
        occasion=base.occasion,
        preferred_condition=PreferredCondition(preferred_text="上品で落ち着いたもの"),
        free_text="補足の自由文",
    )
    context = _sample_context(request=request, run_id="run-skip-llm")
    llm_client = ScaffoldExternalAiClient()
    extractor = build_extractor_with_registered_run(context, llm_client=llm_client)

    extractor.execute(context)

    assert llm_client.generate_calls == []


# §14 No.19 LLM on-demand（呼び出し）は No.3 で確認


# §14 No.20 hard_filter 受け渡し — semantic_extraction_result 内に格納
def test_hard_filter_candidates_remain_nested_in_semantic_extraction_result() -> None:
    base = _sample_context().recommendation_request
    request = RecommendationRequest(
        request_id="req-hard-filter",
        relationship=base.relationship,
        occasion=base.occasion,
        ng_condition=NgCondition(ng_keywords=("アルコール",)),
    )
    context = _sample_context(request=request, run_id="run-hard-filter")
    extractor = build_extractor_with_registered_run(context)

    updated = extractor.execute(context)

    result = updated.semantic_extraction_result
    assert result is not None
    assert len(result.hard_filter_candidates) == 1
    assert not hasattr(updated, "hard_filter_candidates")
