"""MOD-RECO-022 Result Snapshot Builder implementation."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from time import perf_counter
from typing import TYPE_CHECKING

from reco.domain.recommendation.result import RecommendationResultItem
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, PHASE_NAME
from .errors import ResultSnapshotBuilderError
from .in_memory_repository import (
    InMemoryItemSnapshotReadRepository,
    InMemoryRecommendationResultItemRepository,
    build_default_in_memory_item_snapshot_read_repository,
)
from .input_parser import parse_snapshot_builder_input
from .models import SnapshotBuilderInputItem, SnapshotBuilderRunMetrics
from .ports import ItemSnapshotReadPort, RecommendationResultItemRepositoryPort
from .snapshot_engine import build_result_snapshots

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class ResultSnapshotBuilder:
    """PipelineModulePort implementation for Result Snapshot Builder."""

    item_reader: ItemSnapshotReadPort = field(
        default_factory=build_default_in_memory_item_snapshot_read_repository,
    )
    item_repository: RecommendationResultItemRepositoryPort = field(
        default_factory=InMemoryRecommendationResultItemRepository,
    )
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        filled_items, metrics = self.build_snapshots(context)
        _attach_outputs(context, filled_items, metrics)
        context.completed_modules.append(self.module_id)
        return context

    def build_snapshots(
        self,
        context: ExecutionContext,
    ) -> tuple[tuple[SnapshotBuilderInputItem, ...], SnapshotBuilderRunMetrics]:
        started = perf_counter()
        snapshot_input = parse_snapshot_builder_input(context)

        try:
            filled_items, metrics = build_result_snapshots(
                snapshot_input,
                item_reader=self.item_reader,
                item_repository=self.item_repository,
            )
        except ResultSnapshotBuilderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ResultSnapshotBuilderError(
                f"result snapshot build failed for run: {context.run_id}",
            ) from exc

        latency_ms = int((perf_counter() - started) * 1_000)
        metrics = SnapshotBuilderRunMetrics(
            snapshot_builder_item_count=metrics.snapshot_builder_item_count,
            snapshot_builder_latency_ms=latency_ms,
            snapshot_builder_items_persisted=metrics.snapshot_builder_items_persisted,
            snapshot_build_success=metrics.snapshot_build_success,
            snapshot_null_image_count=metrics.snapshot_null_image_count,
            snapshot_null_review_count=metrics.snapshot_null_review_count,
        )
        self._log_build_completed(context, metrics)
        return filled_items, metrics

    def _log_build_completed(
        self,
        context: ExecutionContext,
        metrics: SnapshotBuilderRunMetrics,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            PHASE_NAME,
            snapshot_builder_item_count=metrics.snapshot_builder_item_count,
            snapshot_builder_latency_ms=metrics.snapshot_builder_latency_ms,
            snapshot_builder_items_persisted=metrics.snapshot_builder_items_persisted,
            snapshot_null_image_count=metrics.snapshot_null_image_count,
            snapshot_null_review_count=metrics.snapshot_null_review_count,
            module_id=self.module_id,
        )


def _attach_outputs(
    context: ExecutionContext,
    filled_items: tuple[SnapshotBuilderInputItem, ...],
    metrics: SnapshotBuilderRunMetrics,
) -> None:
    recommendation_result = context.recommendation_result
    if recommendation_result is None:
        raise ResultSnapshotBuilderError(
            "recommendation_result is required on execution_context",
        )

    domain_items = tuple(
        RecommendationResultItem(
            item_id=item.item_id,
            rank=item.rank,
            final_score=item.final_score,
            is_fallback=item.is_fallback,
        )
        for item in filled_items
    )
    version_info = dict(recommendation_result.version_info or {})
    version_info.update(
        {
            "snapshot_builder_item_count": str(metrics.snapshot_builder_item_count),
            "snapshot_builder_items_persisted": "true",
            "snapshot_builder_latency_ms": str(metrics.snapshot_builder_latency_ms),
            "snapshot_build_success": "true",
        },
    )
    for item in filled_items:
        if item.snapshot is not None:
            version_info[f"item:{item.item_id}:item_name_snapshot"] = (
                item.snapshot.item_name_snapshot
            )
            version_info[f"item:{item.item_id}:item_price_snapshot"] = str(
                item.snapshot.item_price_snapshot
            )
            version_info[f"item:{item.item_id}:item_url_snapshot"] = (
                item.snapshot.item_url_snapshot
            )

    context.recommendation_result = replace(
        recommendation_result,
        items=domain_items,
        version_info=version_info,
    )
    context.snapshot_builder_item_count = metrics.snapshot_builder_item_count
    context.snapshot_builder_latency_ms = metrics.snapshot_builder_latency_ms
    context.snapshot_builder_items_persisted = metrics.snapshot_builder_items_persisted
    context.snapshot_build_success = metrics.snapshot_build_success
    context.snapshot_null_image_count = metrics.snapshot_null_image_count
    context.snapshot_null_review_count = metrics.snapshot_null_review_count


def build_default_result_snapshot_builder() -> ResultSnapshotBuilder:
    return ResultSnapshotBuilder()
