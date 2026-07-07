"""MOD-RECO-025 Metric Logger implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID
from .mapper import build_metric_record, metric_record_to_observation_dict
from .ports import MetricLoggerRepository
from .repository import InMemoryMetricLoggerRepository


@dataclass
class MetricLogger:
    """MetricLoggerPort implementation for MOD-RECO-025."""

    repository: MetricLoggerRepository = field(
        default_factory=InMemoryMetricLoggerRepository,
    )
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    recorded: list[dict[str, object]] = field(default_factory=list)

    def record_metrics(self, context: ExecutionContext) -> None:
        run_id = context.run_id
        if run_id is None:
            self._log_warn(
                context,
                event="metric_log_skipped_missing_run_id",
            )
            return

        try:
            record = build_metric_record(context)
            observation = metric_record_to_observation_dict(record)
            self.repository.save(record)
            self.recorded.append(observation)
            self.logger.bind(trace_id=context.trace_id, run_id=run_id).info(
                "metric_recorded",
                module_id=self.module_id,
                recommendation_latency_ms=record.recommendation_latency_ms,
                final_result_count=record.final_result_count,
                recommendation_empty=record.recommendation_empty,
            )
        except Exception as exc:  # noqa: BLE001 — 永続化失敗は推薦返却をブロックしない
            self._log_warn(
                context,
                event="metric_log_save_failed",
                run_id=run_id,
                error_type=type(exc).__name__,
            )

    def _log_warn(
        self,
        context: ExecutionContext,
        *,
        event: str,
        **attributes: object,
    ) -> None:
        # ScaffoldRecoLogger は warn 未実装のため info で構造化出力する（§10.2 warn 相当）
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id or "").info(
            event,
            module_id=self.module_id,
            severity="warn",
            **attributes,
        )


def build_default_metric_logger() -> MetricLogger:
    return MetricLogger()
