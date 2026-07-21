"""MOD-RECO-012 Candidate Retriever implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME, PRE_FILTER_PHASE_NAME
from .errors import PreHardFilterError, RetrievalError
from .models import CandidateRetrieverResult
from .ports import ItemRepositoryPort
from reco.application.candidate_retriever.pre_hard_filter.filter import run_pre_hard_filter
from reco.application.candidate_retriever.retrieval.retrieval_engine import run_retrieval

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class CandidateRetriever:
    """PipelineModulePort implementation for Candidate Retriever (pre_hard_filter → retrieval)."""

    item_repository: ItemRepositoryPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result = self.retrieve(context)
        _attach_outputs(context, result)
        context.completed_modules.append(self.module_id)
        return context

    def retrieve(self, context: ExecutionContext) -> CandidateRetrieverResult:
        self._validate_context(context)

        pre_started = perf_counter()
        try:
            pool = run_pre_hard_filter(context, item_repository=self.item_repository)
        except PreHardFilterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PreHardFilterError(
                f"pre hard filter failed for run: {context.run_id}",
            ) from exc
        pre_latency_ms = int((perf_counter() - pre_started) * 1_000)

        self._log_pre_filter_completed(context, pool.total_after_filter, pre_latency_ms)

        retrieval_started = perf_counter()
        try:
            retrieval_candidate = run_retrieval(
                context,
                pool,
                item_repository=self.item_repository,
            )
        except RetrievalError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RetrievalError(
                f"retrieval failed for run: {context.run_id}",
            ) from exc
        retrieval_latency_ms = int((perf_counter() - retrieval_started) * 1_000)

        self._log_retrieval_completed(
            context,
            retrieval_candidate.total_retrieved,
            retrieval_latency_ms,
        )

        return CandidateRetrieverResult(
            pre_filtered_item_pool=pool,
            retrieval_candidate=retrieval_candidate,
            pre_filter_candidate_count=pool.total_after_filter,
            pre_hard_filter_latency_ms=pre_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            retrieval_candidate_count=retrieval_candidate.total_retrieved,
        )

    def _validate_context(self, context: ExecutionContext) -> None:
        if context.run_id is None:
            raise PreHardFilterError("run_id is required on execution_context")
        if context.semantic_extraction_result is None:
            raise PreHardFilterError(
                "semantic_extraction_result is required on execution_context",
            )
        query_embedding = context.query_embedding
        if query_embedding is None:
            raise PreHardFilterError("query_embedding is required on execution_context")

    def _log_pre_filter_completed(
        self,
        context: ExecutionContext,
        pre_filter_candidate_count: int,
        duration_ms: int,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PRE_FILTER_PHASE_NAME,
            pre_filter_candidate_count=pre_filter_candidate_count,
            pre_hard_filter_latency_ms=duration_ms,
            module_id=self.module_id,
        )

    def _log_retrieval_completed(
        self,
        context: ExecutionContext,
        retrieval_candidate_count: int,
        duration_ms: int,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            retrieval_candidate_count=retrieval_candidate_count,
            retrieval_latency_ms=duration_ms,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    result: CandidateRetrieverResult,
) -> None:
    context.pre_filtered_item_pool = result.pre_filtered_item_pool
    context.retrieval_candidate = result.retrieval_candidate
    context.pre_filter_candidate_count = result.pre_filter_candidate_count
    context.pre_hard_filter_latency_ms = result.pre_hard_filter_latency_ms
    context.retrieval_latency_ms = result.retrieval_latency_ms
    context.retrieval_candidate_count = result.retrieval_candidate_count


def build_default_candidate_retriever() -> CandidateRetriever:
    from .in_memory_repository import build_default_in_memory_item_repository

    return CandidateRetriever(
        item_repository=build_default_in_memory_item_repository(),
    )
