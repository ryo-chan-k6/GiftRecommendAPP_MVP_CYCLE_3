"""MOD-RECO-012 Candidate Retriever module unit tests (module spec §14.3 unit)."""

from __future__ import annotations

import json

from conftest import (
    TrackingItemRepository,
    _sample_context,
    build_item_record,
    build_retriever_with_repository,
)
from reco.application.candidate_retriever import (
    CandidateRetriever,
    InMemoryItemRepository,
    PHASE_NAME,
    PRE_FILTER_PHASE_NAME,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


# §14 No.11 内部順序
def test_retrieve_runs_pre_hard_filter_before_retrieval() -> None:
    context = _sample_context(
        run_id="run-module-order",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    inner = InMemoryItemRepository(items=(build_item_record(item_id="item-1"),))
    tracking_repo = TrackingItemRepository(inner=inner)
    retriever = CandidateRetriever(
        item_repository=tracking_repo,
        logger=ScaffoldRecoLogger(),
    )

    retriever.retrieve(context)

    assert tracking_repo.calls == [
        "count_active_items",
        "count_filtered_items",
        "search_vector_candidates",
    ]


# §14 No.13 Metric
def test_execute_sets_pre_filter_candidate_count_metric() -> None:
    context = _sample_context(
        run_id="run-module-metric",
        ng_keywords=(),
        hard_filter_candidates=(),
        candidate_limit=10,
    )
    repo_items = tuple(
        build_item_record(
            item_id=f"item-{index}",
            embedding=(1.0, float(index) * 0.1, 0.0, 0.0),
        )
        for index in range(3)
    )
    retriever, _ = build_retriever_with_repository(
        context,
        item_repository=InMemoryItemRepository(items=repo_items),
    )

    result_context = retriever.execute(context)

    assert result_context.pre_filter_candidate_count == 3  # type: ignore[attr-defined]
    assert result_context.retrieval_candidate_count == 3  # type: ignore[attr-defined]


# §14 No.15 ログ
def test_execute_emits_structured_logs_with_trace_id_without_secrets() -> None:
    context = _sample_context(
        run_id="run-module-log",
        trace_id="trace-mod-reco-012-unit",
        ng_keywords=(),
        hard_filter_candidates=(),
    )
    logger = ScaffoldRecoLogger()
    retriever, _ = build_retriever_with_repository(
        context,
        item_repository=InMemoryItemRepository(items=(build_item_record(item_id="item-1"),)),
        logger=logger,
    )

    retriever.execute(context)

    pre_logs = [record for record in logger.records if record.event == PRE_FILTER_PHASE_NAME]
    retrieval_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(pre_logs) == 1
    assert len(retrieval_logs) == 1

    for record in pre_logs + retrieval_logs:
        assert record.context.trace_id == "trace-mod-reco-012-unit"
        serialized = json.dumps(record.attributes, ensure_ascii=False).lower()
        assert "api_key" not in serialized
        assert "password" not in serialized
        assert "token" not in serialized
        assert "secret" not in serialized
