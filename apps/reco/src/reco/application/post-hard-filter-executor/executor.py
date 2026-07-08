"""MOD-RECO-013 Post Hard Filter Executor implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import PostHardFilterError
from .filter_engine import run_post_hard_filter
from .models import PostHardFilterResult
from .ports import ItemRepositoryPort

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class PostHardFilterExecutor:
    """PipelineModulePort implementation for Post Hard Filter."""

    item_repository: ItemRepositoryPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result = self.apply_post_hard_filter(context)
        _attach_outputs(context, result)
        context.completed_modules.append(self.module_id)
        return context

    def apply_post_hard_filter(self, context: ExecutionContext) -> PostHardFilterResult:
        self._validate_context(context)

        started = perf_counter()
        try:
            result = run_post_hard_filter(
                context,
                item_repository=self.item_repository,
            )
        except PostHardFilterError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PostHardFilterError(
                f"post hard filter failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        result = PostHardFilterResult(
            validated_retrieval_candidate=result.validated_retrieval_candidate,
            excluded_candidate_log=result.excluded_candidate_log,
            post_filter_candidate_count=result.post_filter_candidate_count,
            post_hard_filter_latency_ms=latency_ms,
        )

        self._log_filter_completed(context, result)
        return result

    def _validate_context(self, context: ExecutionContext) -> None:
        if context.run_id is None:
            raise PostHardFilterError("run_id is required on execution_context")

    def _log_filter_completed(
        self,
        context: ExecutionContext,
        result: PostHardFilterResult,
    ) -> None:
        summary_by_reason = result.excluded_candidate_log.summary_by_reason or {}
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            post_filter_candidate_count=result.post_filter_candidate_count,
            post_hard_filter_latency_ms=result.post_hard_filter_latency_ms,
            post_hard_filter_exclusion_count=result.validated_retrieval_candidate.total_excluded,
            summary_by_reason=summary_by_reason,
            module_id=self.module_id,
        )


def _attach_outputs(context: ExecutionContext, result: PostHardFilterResult) -> None:
    context.validated_retrieval_candidate = result.validated_retrieval_candidate
    context.excluded_candidate_log = result.excluded_candidate_log
    context.post_filter_candidate_count = result.post_filter_candidate_count
    context.post_hard_filter_latency_ms = result.post_hard_filter_latency_ms


def build_default_post_hard_filter_executor() -> PostHardFilterExecutor:
    from .in_memory_repository import build_default_in_memory_item_repository

    return PostHardFilterExecutor(
        item_repository=build_default_in_memory_item_repository(),
    )
