"""MOD-RECO-023 Reason Generator unit tests (module spec §14 unit)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from conftest import (
    DEFAULT_ITEM_ID,
    DEFAULT_RESULT_ITEM_ID,
    _feature_match_entry,
    _risk_penalty_entry,
    _sample_context,
    _sample_feature_match_result,
    _sample_item_semantic_record,
    _sample_risk_penalty_result,
    build_item_semantic_reader,
    build_reason_generator,
    build_template_repository,
)
from reco.application.feature_matcher.models import FeatureAxisMatch
from reco.application.recommendation_orchestrator.ports import ReasonGenerationOutcome
from reco.application.reason_generator import (
    GENERATION_METHOD_INTERNAL_FALLBACK,
    GENERATION_METHOD_TEMPLATE,
    GENERIC_REASON_SUMMARY,
    LLM_REFINEMENT_ENV,
    ReasonTemplateRecord,
)
from reco.application.reason_generator.in_memory_repository import (
    InMemoryRecommendationReasonRepository,
)
from reco.infrastructure.external_ai.client import ExternalAiResponse, ScaffoldExternalAiClient


REASON_BASIS_REQUIRED_KEYS = frozenset(
    {
        "template_name",
        "template_version",
        "template_type",
        "used_features",
        "used_scores",
        "used_semantic_evidence",
        "generation_method",
        "generated_text",
    },
)


# §14 No.1 正常系
def test_generate_produces_summary_badges_and_points_with_strong_match() -> None:
    context = _sample_context()
    reason_repository = InMemoryRecommendationReasonRepository()
    generator = build_reason_generator(reason_repository=reason_repository)

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.SUCCESS
    item = context.recommendation_result.items[0]
    assert item.reason_summary
    assert item.reason_summary != GENERIC_REASON_SUMMARY
    row = reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_badges_json
    assert row.reason_points_json
    assert "きちんと感" in row.reason_badges_json[0]


# §14 No.2 テンプレート解決
def test_generate_selects_template_by_relationship_occasion_and_feature() -> None:
    generic_template = ReasonTemplateRecord(
        reason_template_id="template-generic",
        template_name="reason_summary_default",
        template_version=1,
        template_type="summary",
        template_body="{relationship_label}への{occasion_label}として、{primary_reason}がある候補です。",
    )
    specific_template = ReasonTemplateRecord(
        reason_template_id="template-friend-birthday-formality",
        template_name="reason_summary_friend_birthday_formality",
        template_version=2,
        template_type="summary",
        template_body=(
            "{relationship_label}への{occasion_label}向けに、"
            "{primary_reason}が特徴的な候補です。"
        ),
        relationship_code="friend",
        occasion_code="birthday",
        feature_code="formality",
    )
    context = _sample_context()
    generator = build_reason_generator(
        template_reader=build_template_repository(generic_template, specific_template),
    )

    generator.generate(context)

    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_basis_json["template_name"] == "reason_summary_friend_birthday_formality"
    assert "向けに" in row.reason_summary


# §14 No.3 reason_basis_json
def test_generate_reason_basis_json_contains_required_keys() -> None:
    context = _sample_context()
    semantic_reader = build_item_semantic_reader(_sample_item_semantic_record())
    generator = build_reason_generator(item_semantic_reader=semantic_reader)

    generator.generate(context)

    basis = generator.reason_repository.rows_by_result_item_id[
        DEFAULT_RESULT_ITEM_ID
    ].reason_basis_json
    assert set(basis) == REASON_BASIS_REQUIRED_KEYS
    assert basis["generation_method"] == GENERATION_METHOD_TEMPLATE
    assert isinstance(basis["used_features"], list)
    assert isinstance(basis["used_scores"], dict)


# §14 No.4 閾値
def test_generate_does_not_use_feature_match_below_threshold_as_primary_reason() -> None:
    below_threshold = _feature_match_entry(
        features={
            "formality": FeatureAxisMatch(distance=0.3, match=0.79),
            "emotion": FeatureAxisMatch(distance=0.2, match=0.75),
        },
    )
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(entries=(below_threshold,)),
    )
    generator = build_reason_generator()

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK
    basis = generator.reason_repository.rows_by_result_item_id[
        DEFAULT_RESULT_ITEM_ID
    ].reason_basis_json
    strong_features = [
        feature
        for feature in basis["used_features"]
        if feature["strength"] == "strong"
    ]
    assert strong_features == []
    assert context.recommendation_result.items[0].reason_summary == GENERIC_REASON_SUMMARY


def test_generate_uses_only_features_at_or_above_strong_match_threshold() -> None:
    mixed_features = _feature_match_entry(
        features={
            "formality": FeatureAxisMatch(distance=0.1, match=0.88),
            "emotion": FeatureAxisMatch(distance=0.4, match=0.65),
        },
    )
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(entries=(mixed_features,)),
    )
    generator = build_reason_generator()

    generator.generate(context)

    strong_features = [
        feature
        for feature in generator.reason_repository.rows_by_result_item_id[
            DEFAULT_RESULT_ITEM_ID
        ].reason_basis_json["used_features"]
        if feature["strength"] == "strong"
    ]
    assert [feature["feature_code"] for feature in strong_features] == ["formality"]


# §14 No.5 caution_note
def test_generate_sets_caution_note_when_risk_penalty_is_high() -> None:
    context = _sample_context(
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(_risk_penalty_entry(risk_penalty=0.45),),
        ),
    )
    generator = build_reason_generator()

    generator.generate(context)

    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.caution_note is not None
    assert "リスク要因" in row.caution_note


def test_generate_leaves_caution_note_null_when_risk_is_low() -> None:
    only_strong_features = _feature_match_entry(
        features={
            "formality": FeatureAxisMatch(distance=0.1, match=0.88),
            "safety": FeatureAxisMatch(distance=0.15, match=0.85),
        },
    )
    context = _sample_context(
        feature_match_result=_sample_feature_match_result(entries=(only_strong_features,)),
        risk_penalty_result=_sample_risk_penalty_result(
            entries=(_risk_penalty_entry(risk_penalty=0.08),),
        ),
    )
    generator = build_reason_generator()

    generator.generate(context)

    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.caution_note is None


# §14 No.6 入力欠損
def test_generate_uses_generic_labels_when_relationship_and_occasion_missing() -> None:
    context = _sample_context(relationship=None, occasion=None)
    generator = build_reason_generator()

    generator.generate(context)

    summary = context.recommendation_result.items[0].reason_summary
    assert "贈り物として" in summary
    assert "今回のギフトとして" in summary


# §14 No.7 根拠不足
def test_generate_uses_internal_fallback_without_strong_match() -> None:
    context = _sample_context(include_feature_match=False)
    generator = build_reason_generator()

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK
    item = context.recommendation_result.items[0]
    assert item.reason_summary == GENERIC_REASON_SUMMARY
    assert item.is_fallback is True
    basis = generator.reason_repository.rows_by_result_item_id[
        DEFAULT_RESULT_ITEM_ID
    ].reason_basis_json
    assert basis["generation_method"] == GENERATION_METHOD_INTERNAL_FALLBACK


@dataclass
class _FailingExternalAiClient:
    generate_calls: list[dict[str, str]] = field(default_factory=list)

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse:
        self.generate_calls.append({"prompt": prompt, "purpose": purpose})
        raise TimeoutError("simulated llm timeout")


# §14 No.8 LLM 失敗
def test_generate_keeps_template_summary_when_llm_refinement_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_REFINEMENT_ENV, "true")
    context = _sample_context()
    llm_client = _FailingExternalAiClient()
    generator = build_reason_generator(llm_client=llm_client)

    generator.generate(context)

    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_basis_json["generation_method"] == GENERATION_METHOD_TEMPLATE
    assert row.reason_summary != GENERIC_REASON_SUMMARY
    assert "友人" in row.reason_summary


# §14 No.9 禁止表現
def test_generate_falls_back_when_template_contains_forbidden_expression() -> None:
    forbidden_template = ReasonTemplateRecord(
        reason_template_id="template-forbidden",
        template_name="reason_summary_forbidden",
        template_version=1,
        template_type="summary",
        template_body="絶対に喜ばれます",
    )
    context = _sample_context()
    generator = build_reason_generator(
        template_reader=build_template_repository(forbidden_template),
    )

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK
    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_summary == GENERIC_REASON_SUMMARY
    assert row.reason_basis_json["generation_method"] == GENERATION_METHOD_INTERNAL_FALLBACK


# §14 No.10 DB INSERT（unit 範囲）
def test_generate_persists_one_non_empty_reason_row_per_item() -> None:
    context = _sample_context()
    reason_repository = InMemoryRecommendationReasonRepository()
    generator = build_reason_generator(reason_repository=reason_repository)

    generator.generate(context)

    assert len(reason_repository.rows_by_result_item_id) == 1
    row = reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_summary
    assert row.recommendation_result_item_id == DEFAULT_RESULT_ITEM_ID


def test_generate_retries_insert_with_generic_reason_when_first_insert_fails() -> None:
    context = _sample_context()
    reason_repository = InMemoryRecommendationReasonRepository(
        fail_once_for_item_ids={DEFAULT_RESULT_ITEM_ID},
    )
    generator = build_reason_generator(reason_repository=reason_repository)

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.INTERNAL_FALLBACK
    row = reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_summary == GENERIC_REASON_SUMMARY


# §14 No.13 スコア不変
def test_generate_does_not_mutate_rank_or_final_score() -> None:
    context = _sample_context()
    before = context.recommendation_result.items[0]
    generator = build_reason_generator()

    generator.generate(context)

    after = context.recommendation_result.items[0]
    assert after.rank == before.rank
    assert after.final_score == before.final_score


# §14 No.16 責務境界
def test_generate_does_not_modify_snapshot_builder_version_info() -> None:
    context = _sample_context()
    version_info_before = dict(context.recommendation_result.version_info)
    generator = build_reason_generator()

    generator.generate(context)

    version_info_after = context.recommendation_result.version_info
    assert version_info_after["snapshot_builder_items_persisted"] == version_info_before[
        "snapshot_builder_items_persisted"
    ]
    assert version_info_after["_builder_items"] == version_info_before["_builder_items"]
    assert "item_name_snapshot" not in version_info_after


# §14 No.21 item_semantic 読取
def test_generate_reflects_item_semantic_evidence_in_reason_basis_json() -> None:
    evidence_text = "上品な包装で贈答シーンに適している"
    semantic_reader = build_item_semantic_reader(
        _sample_item_semantic_record(evidence_text=evidence_text),
    )
    context = _sample_context()
    generator = build_reason_generator(item_semantic_reader=semantic_reader)

    generator.generate(context)

    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    evidence = row.reason_basis_json["used_semantic_evidence"]
    assert evidence[0]["evidence_text"] == evidence_text
    assert any(evidence_text in point for point in row.reason_points_json or [])


# §14 No.22 item_semantic 欠損
def test_generate_succeeds_with_feature_based_reason_when_item_semantic_missing() -> None:
    context = _sample_context()
    generator = build_reason_generator(item_semantic_reader=build_item_semantic_reader())

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.SUCCESS
    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_summary != GENERIC_REASON_SUMMARY
    assert row.reason_basis_json["used_semantic_evidence"] == []


# §14 No.23 LLM default OFF
def test_generate_does_not_call_llm_client_when_env_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(LLM_REFINEMENT_ENV, raising=False)
    context = _sample_context()
    llm_client = ScaffoldExternalAiClient()
    generator = build_reason_generator(llm_client=llm_client)

    generator.generate(context)

    assert llm_client.generate_calls == []


def test_generate_does_not_call_llm_client_when_env_is_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_REFINEMENT_ENV, "false")
    context = _sample_context()
    llm_client = ScaffoldExternalAiClient()
    generator = build_reason_generator(llm_client=llm_client)

    generator.generate(context)

    assert llm_client.generate_calls == []


# §14 No.25 LLM timeout
def test_generate_continues_with_template_when_llm_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LLM_REFINEMENT_ENV, "true")
    context = _sample_context()
    llm_client = _FailingExternalAiClient()
    generator = build_reason_generator(llm_client=llm_client)

    result = generator.generate(context)

    assert result.outcome == ReasonGenerationOutcome.SUCCESS
    assert len(llm_client.generate_calls) == 1
    row = generator.reason_repository.rows_by_result_item_id[DEFAULT_RESULT_ITEM_ID]
    assert row.reason_basis_json["generation_method"] == GENERATION_METHOD_TEMPLATE
