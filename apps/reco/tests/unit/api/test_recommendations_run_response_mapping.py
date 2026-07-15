"""Response mapping unit tests for API-INT-002 (契約仕様書 §12 No.1, 2, 8, 9)."""

from __future__ import annotations

from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.result import ResultStatus

from conftest import (
    api_headers,
    build_domain_request,
    build_execution_context,
    build_result_item,
    build_success_outcome,
    sample_request_body,
    score_breakdown_version_info,
    stub_api_client,
)


def test_run_recommendation_success_maps_result_items_and_scores() -> None:
    item = build_result_item(
        item_id="item_001",
        rank=1,
        final_score=0.82,
        reason_summary="上司へのお礼として候補にしています。",
    )
    version_info = {
        "recommendation_result_id": "result_001",
        "item:item_001:recommendation_result_item_id": "result_item_001",
        "item:item_001:item_name_snapshot": "上品な焼き菓子ギフトセット",
        "item:item_001:item_price_snapshot": "4320",
        "item:item_001:item_url_snapshot": "https://example.com/items/item_001",
    }
    context = build_execution_context(
        request=build_domain_request(include_reason=True),
        retrieval_candidate_count=12,
        feature_matcher_candidate_count=8,
        final_ranker_selected_count=1,
    )
    outcome = build_success_outcome(
        items=(item,),
        context=context,
        version_info=version_info,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(include_reason=True),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resultItemCount"] == 1
    assert data["resultStatus"] == "completed"
    assert data["candidateCounts"] == {
        "retrievalCount": 12,
        "matchingCount": 8,
        "rankingCount": 1,
    }

    result_item = data["resultItems"][0]
    assert result_item["recommendationResultItemId"] == "result_item_001"
    assert result_item["itemId"] == "item_001"
    assert result_item["itemName"] == "上品な焼き菓子ギフトセット"
    assert result_item["itemPrice"] == 4320
    assert result_item["itemUrl"] == "https://example.com/items/item_001"
    assert result_item["contextScore"] == 0.82
    assert result_item["finalScore"] == 0.82
    assert result_item["reasonSummary"] == "上司へのお礼として候補にしています。"
    assert result_item["reasonStatus"] == "completed"
    assert result_item["isFallback"] is False


def test_run_recommendation_zero_items_includes_no_candidates_warning() -> None:
    context = build_execution_context(
        retrieval_candidate_count=0,
        feature_matcher_candidate_count=0,
        final_ranker_selected_count=0,
        retrieval_latency_ms=95,
    )
    outcome = build_success_outcome(
        items=(),
        result_status=ResultStatus.EMPTY,
        context=context,
        version_info={"recommendation_result_id": "result_002"},
        run_id="run_002",
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(request_id="request_002"),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resultItemCount"] == 0
    assert data["displayMessage"] == "条件に合う商品が見つかりませんでした。"
    assert data["warnings"] == [
        {"code": "NO_CANDIDATES_AFTER_RETRIEVAL", "severity": "warn"},
    ]
    assert response.json()["meta"]["resultCode"] == "GRS-REC-001"


def test_run_recommendation_low_candidates_warning() -> None:
    context = build_execution_context(
        retrieval_candidate_count=5,
        feature_matcher_candidate_count=2,
        final_ranker_selected_count=2,
    )
    outcome = build_success_outcome(
        items=(
            build_result_item(item_id="item_001", rank=1),
            build_result_item(item_id="item_002", rank=2),
        ),
        context=context,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(top_k=10),
            headers=api_headers(),
        )
    assert response.status_code == 200
    warnings = response.json()["data"]["warnings"]
    assert warnings == [{"code": "LOW_CANDIDATES_AFTER_MATCHING", "severity": "warn"}]


def test_run_recommendation_metric_summary_maps_phase_duration() -> None:
    context = build_execution_context(
        retrieval_candidate_count=3,
        feature_matcher_candidate_count=3,
        final_ranker_selected_count=1,
        retrieval_latency_ms=120,
        feature_matcher_latency_ms=210,
        final_ranker_latency_ms=95,
        reason_generation_latency_ms=380,
    )
    outcome = build_success_outcome(
        items=(build_result_item(),),
        context=context,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    metric_summary = response.json()["data"]["metricSummary"]
    assert metric_summary is not None
    assert metric_summary["phaseDurationMs"] == {
        "retrieval": 120,
        "matching": 210,
        "ranking": 95,
        "reason": 380,
    }
    assert isinstance(metric_summary["recommendationLatencyMs"], int)


def test_run_recommendation_debug_return_evaluation_mode() -> None:
    request = build_domain_request(
        mode=ExecutionMode.EVALUATION,
        include_reason=True,
        eval_case_id="eval_case_001",
        config_name="semantic_v1",
        version_label="2026-06-01",
        model_version_id="model_v3",
    )
    context = build_execution_context(
        request=request,
        config_versions={"semantic": "v1"},
    )
    breakdown = {"contextScore": 0.82, "popularityScore": 0.64}
    version_info = {
        "recommendation_result_id": "result_debug",
        **score_breakdown_version_info("item_001", breakdown),
    }
    outcome = build_success_outcome(
        items=(build_result_item(),),
        context=context,
        version_info=version_info,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(mode="evaluation", include_reason=True),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["metadata"]["mode"] == "evaluation"
    assert data["metadata"]["debugPayload"] == {
        "evalCaseId": "eval_case_001",
        "configName": "semantic_v1",
        "versionLabel": "2026-06-01",
        "modelVersionId": "model_v3",
        "configVersions": {"semantic": "v1"},
    }
    assert data["resultItems"][0]["scoreBreakdown"] == breakdown
    assert data["reasonData"] is not None
    assert len(data["reasonData"]["items"]) == 1


def test_run_recommendation_debug_return_include_debug_info() -> None:
    request = build_domain_request(include_debug_info=True, include_reason=True)
    context = build_execution_context(request=request)
    breakdown = {"finalScore": 0.78}
    version_info = score_breakdown_version_info("item_001", breakdown)
    outcome = build_success_outcome(
        items=(build_result_item(),),
        context=context,
        version_info=version_info,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(include_debug_info=True, include_reason=True),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resultItems"][0]["scoreBreakdown"] == breakdown
    assert data["metadata"].get("debugPayload") is None


def test_run_recommendation_without_debug_omits_score_breakdown() -> None:
    context = build_execution_context(
        retrieval_candidate_count=8,
        feature_matcher_candidate_count=8,
        final_ranker_selected_count=1,
    )
    version_info = score_breakdown_version_info("item_001", {"finalScore": 0.78})
    outcome = build_success_outcome(
        items=(build_result_item(),),
        context=context,
        version_info=version_info,
    )
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resultItems"][0].get("scoreBreakdown") is None
    assert data.get("warnings") in (None, [])


def test_run_recommendation_reason_fallback_maps_completed_reason() -> None:
    item = build_result_item(
        reason_summary=None,
        reason_status=None,
        is_fallback=True,
    )
    context = build_execution_context(
        request=build_domain_request(include_reason=True),
        reason_fallback_count=1,
        retrieval_candidate_count=3,
        feature_matcher_candidate_count=3,
        final_ranker_selected_count=1,
    )
    outcome = build_success_outcome(items=(item,), context=context)
    with stub_api_client(outcome) as client:
        response = client.post(
            "/internal/reco/v1/recommendations/run",
            json=sample_request_body(include_reason=True),
            headers=api_headers(),
        )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["fallbackUsed"] is True
    result_item = data["resultItems"][0]
    assert result_item["isFallback"] is True
    assert result_item["reasonSummary"] == "推薦候補として選定しました。"
    assert result_item["reasonStatus"] == "completed"
