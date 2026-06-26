"""MOD-RECO-002 Recommendation Run Recorder implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from reco.domain.recommendation.run import RecommendationRun, RunStatus
from reco.infrastructure.db.repositories.pair_master_reader import PairMasterReader
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    RecommendationRunRecord,
    RecommendationRunRepository,
)
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .errors import MODULE_ID, RunRecorderError
from .state_machine import is_terminal, validate_transition

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )

_VERSION_KEY_CANDIDATES: tuple[tuple[str, str], ...] = (
    ("semantic_config_version_id", "semantic_config_version"),
    ("model_version_id", "model_version"),
    ("ranking_config_id", "ranking_config"),
)


def _resolve_config_version_ids(
    config_versions: dict[str, str],
) -> tuple[str, str, str] | None:
    resolved: list[str] = []
    for primary, fallback in _VERSION_KEY_CANDIDATES:
        value = config_versions.get(primary) or config_versions.get(fallback)
        if not value:
            return None
        resolved.append(value)
    return resolved[0], resolved[1], resolved[2]


def _to_domain_run(record: RecommendationRunRecord) -> RecommendationRun:
    return RecommendationRun(
        run_id=record.run_id,
        request_id=record.request_id,
        status=record.run_status,
        semantic_config_version=record.semantic_config_version_id,
        model_version=record.model_version_id,
    )


@dataclass
class RecommendationRunRecorder:
    """RunRecorderPort implementation for MOD-RECO-002."""

    run_repository: RecommendationRunRepository
    pair_reader: PairMasterReader
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID

    def record_run(self, context: ExecutionContext) -> ExecutionContext:
        """Create accepted run and transition to running (Orchestrator entry point)."""
        if context.recommendation_run is not None:
            if context.recommendation_run.status is RunStatus.RUNNING:
                return context
            raise RunRecorderError(
                "GRS-REC-002",
                "recommendation_run already exists on execution_context",
            )

        request = context.recommendation_request
        if not self.run_repository.request_exists(request.request_id):
            raise RunRecorderError(
                "GRS-REC-002",
                f"recommendation_request not found: {request.request_id}",
            )

        pair_id = self._resolve_pair_id(request)
        if pair_id is None:
            raise RunRecorderError(
                "GRS-REC-002",
                "pair_id could not be resolved from relationship and occasion",
            )

        version_ids = _resolve_config_version_ids(context.config_versions)
        if version_ids is None:
            raise RunRecorderError(
                "GRS-REC-002",
                "config version 3 columns are not set on execution_context",
            )

        semantic_id, model_id, ranking_id = version_ids
        if not self.run_repository.version_exists(
            semantic_config_version_id=semantic_id,
            model_version_id=model_id,
            ranking_config_id=ranking_id,
        ):
            raise RunRecorderError(
                "GRS-REC-002",
                "one or more config version ids do not exist",
            )

        try:
            accepted = self.run_repository.insert_accepted(
                request_id=request.request_id,
                pair_id=pair_id,
                semantic_config_version_id=semantic_id,
                model_version_id=model_id,
                ranking_config_id=ranking_id,
            )
        except Exception as exc:
            raise RunRecorderError(
                "GRS-REC-002",
                f"recommendation_run insert failed: {exc}",
            ) from exc

        context.recommendation_run = _to_domain_run(accepted)
        self._log_created(context, accepted)

        running = self._persist_transition(
            accepted.run_id,
            from_status=RunStatus.ACCEPTED,
            to_status=RunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        context.recommendation_run = _to_domain_run(running)
        self._log_status_changed(
            context,
            from_status=RunStatus.ACCEPTED,
            to_status=RunStatus.RUNNING,
        )
        context.completed_modules.append(self.module_id)
        return context

    def apply_transition(
        self,
        context: ExecutionContext,
        target: RunStatus,
    ) -> ExecutionContext:
        """Apply a single run_status transition (for terminal states and re-entry)."""
        if context.recommendation_run is None:
            raise RunRecorderError(
                "GRS-REC-002",
                "recommendation_run is not initialized on execution_context",
            )

        run_id = context.recommendation_run.run_id
        current_record = self.run_repository.get_by_id(run_id)
        if current_record is None:
            raise RunRecorderError(
                "GRS-REC-002",
                f"recommendation_run not found: {run_id}",
            )

        from_status = current_record.run_status
        validate_transition(from_status, target)

        started_at = current_record.started_at
        completed_at = current_record.completed_at
        now = datetime.now(UTC)

        if target is RunStatus.RUNNING and started_at is None:
            started_at = now
        if is_terminal(target):
            completed_at = now

        try:
            updated = self._persist_transition(
                run_id,
                from_status=from_status,
                to_status=target,
                started_at=started_at,
                completed_at=completed_at,
            )
        except RunRecorderError:
            raise
        except Exception as exc:
            raise RunRecorderError(
                "GRS-REC-002",
                f"recommendation_run update failed: {exc}",
            ) from exc

        context.recommendation_run = _to_domain_run(updated)
        self._log_status_changed(context, from_status=from_status, to_status=target)
        return context

    def _persist_transition(
        self,
        run_id: str,
        *,
        from_status: RunStatus,
        to_status: RunStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> RecommendationRunRecord:
        validate_transition(from_status, to_status)
        return self.run_repository.update_status(
            run_id,
            run_status=to_status,
            started_at=started_at,
            completed_at=completed_at,
        )

    def _resolve_pair_id(self, request) -> str | None:
        relationship = request.relationship
        occasion = request.occasion
        if relationship is None or occasion is None:
            return None
        return self.pair_reader.resolve_pair_id(
            relationship_code=relationship.relationship_code,
            occasion_code=occasion.occasion_code,
        )

    def _log_created(
        self,
        context: ExecutionContext,
        record: RecommendationRunRecord,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=record.run_id).info(
            "recommendation_run_created",
            recommendation_run_id=record.run_id,
            recommendation_request_id=record.request_id,
            run_status=record.run_status.value,
            module_id=self.module_id,
        )

    def _log_status_changed(
        self,
        context: ExecutionContext,
        *,
        from_status: RunStatus,
        to_status: RunStatus,
    ) -> None:
        run_id = context.run_id
        if run_id is None:
            return
        self.logger.bind(trace_id=context.trace_id, run_id=run_id).info(
            "recommendation_run_status_changed",
            recommendation_run_id=run_id,
            from_status=from_status.value,
            to_status=to_status.value,
            module_id=self.module_id,
        )
