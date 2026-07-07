"""MOD-RECO-001 Recommendation Orchestrator implementation."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import (
    ReasonStatus,
    RecommendationResult,
    RecommendationResultItem,
    ResultStatus,
)
from reco.domain.recommendation.run import RunStatus

from .constants import GENERIC_REASON_SUMMARY, MODULE_ERROR_CODES, ORCHESTRATOR_MODULE_ORDER
from .phase_name import normalize_orchestrator_phase_name, resolve_aggregated_phase_name

# MOD-RECO-014 §16.1 No.8: Matching 対象 0 件時に Orchestrator がスキップするモジュール
_MATCHING_RANKING_MODULE_IDS: frozenset[str] = frozenset(
    {
        "MOD-RECO-015",
        "MOD-RECO-016",
        "MOD-RECO-017",
        "MOD-RECO-018",
        "MOD-RECO-019",
        "MOD-RECO-020",
    }
)
from .errors import ModuleExecutionError, RecoError
from .execution_context import ExecutionContext
from .ports import (
    OrchestratorPorts,
    PhaseStatus,
    ReasonGenerationOutcome,
)
from .reason_fallback import inject_generic_reason_fallback
from .stubs import build_default_stub_ports, resolve_execution_mode


@dataclass(frozen=True)
class OrchestratorOutcome:
    """Result of a single orchestrator invocation."""

    success: bool
    recommendation_result: RecommendationResult | None = None
    reco_error: RecoError | None = None
    execution_context: ExecutionContext | None = None


class RecommendationOrchestrator:
    """Controls reco online pipeline order and delegates to downstream modules."""

    def __init__(self, ports: OrchestratorPorts | None = None) -> None:
        if ports is None:
            ports, _ = build_default_stub_ports()
        self._ports = ports

    @property
    def ports(self) -> OrchestratorPorts:
        return self._ports

    def run(
        self,
        recommendation_request: RecommendationRequest,
        *,
        trace_id: str,
        execution_mode: ExecutionMode | None = None,
        caller_context: dict[str, object] | None = None,
    ) -> OrchestratorOutcome:
        mode = resolve_execution_mode(recommendation_request, execution_mode)
        context = ExecutionContext(
            recommendation_request=recommendation_request,
            trace_id=trace_id,
            execution_mode=mode,
            caller_context=caller_context,
        )

        self._ports.phase_log_writer.record_phase(
            context,
            phase_name="request_received",
            phase_status=PhaseStatus.STARTED,
        )

        try:
            context = self._execute_pipeline(context)
        except ModuleExecutionError as exc:
            failed_phase_name = normalize_orchestrator_phase_name(
                exc.module_id,
                exc.phase_name,
            )
            reco_error = self._ports.error_handler.handle(
                context,
                module_id=exc.module_id,
                error_code=exc.error_code,
                message=str(exc),
                phase_name=failed_phase_name,
                cause=exc.__cause__,
            )
            self._ports.phase_log_writer.record_phase(
                context,
                phase_name=failed_phase_name,
                phase_status=PhaseStatus.FAILED,
                module_id=exc.module_id,
                error_code=exc.error_code,
            )
            return OrchestratorOutcome(
                success=False,
                reco_error=reco_error,
                execution_context=context,
            )

        if context.recommendation_result is None:
            fatal_error = self._ports.error_handler.handle(
                context,
                module_id="MOD-RECO-021",
                error_code="GRS-REC-012",
                message="recommendation result is missing after pipeline",
                phase_name="response_built",
            )
            return OrchestratorOutcome(
                success=False,
                reco_error=fatal_error,
                execution_context=context,
            )

        if context.recommendation_run is not None:
            context.recommendation_run = context.recommendation_run.with_status(
                RunStatus.SUCCEEDED
            )

        if self._ports.metric_logger is not None:
            self._ports.metric_logger.record_metrics(context)

        self._ports.phase_log_writer.record_phase(
            context,
            phase_name="response_built",
            phase_status=PhaseStatus.SUCCEEDED,
            duration_ms=context.recommendation_latency_ms,
        )

        return OrchestratorOutcome(
            success=True,
            recommendation_result=context.recommendation_result,
            execution_context=context,
        )

    def _execute_pipeline(self, context: ExecutionContext) -> ExecutionContext:
        context = self._invoke_config_resolver(context)
        context = self._invoke_run_recorder(context)
        matching_zero_short_circuit = False

        for module in self._ports.ordered_pipeline_modules():
            if (
                matching_zero_short_circuit
                and module.module_id in _MATCHING_RANKING_MODULE_IDS
            ):
                continue

            if module.module_id in {"MOD-RECO-021", "MOD-RECO-022"}:
                context = self._invoke_pipeline_module(context, module)
                continue

            if module.module_id == "MOD-RECO-019":
                context = self._invoke_pipeline_module(context, module)
                # Ranking 責務分離: 019 (score) → 020 (rank)
                context = self._invoke_pipeline_module(
                    context, self._ports.final_ranker
                )
                continue

            if module.module_id == "MOD-RECO-020":
                # Already invoked immediately after MOD-RECO-019.
                continue

            context = self._invoke_pipeline_module(context, module)

            if (
                module.module_id == "MOD-RECO-014"
                and self._should_short_circuit_after_feature_matcher(context)
            ):
                context = self._record_matching_completed_after_short_circuit(context)
                context = self._prepare_empty_result_after_matching_zero(context)
                matching_zero_short_circuit = True

        context = self._invoke_reason_generator(context)
        self._assert_module_order(context)
        return context

    def _invoke_run_recorder(self, context: ExecutionContext) -> ExecutionContext:
        # MOD-RECO-002: enum 外 run_recorded は記録せず Run 永続化のみ（028 §16.1 No.8/9）
        module = self._ports.run_recorder
        try:
            return module.record_run(context)
        except Exception as exc:  # noqa: BLE001 - delegated to MOD-RECO-024
            error_code = MODULE_ERROR_CODES[module.module_id]
            failed_phase_name = normalize_orchestrator_phase_name(
                module.module_id,
                "run_recorded",
            )
            self._ports.phase_log_writer.record_phase(
                context,
                phase_name=failed_phase_name,
                phase_status=PhaseStatus.FAILED,
                module_id=module.module_id,
                error_code=error_code,
            )
            raise ModuleExecutionError(
                module.module_id,
                str(exc),
                error_code=error_code,
                phase_name=failed_phase_name,
            ) from exc

    def _invoke_config_resolver(self, context: ExecutionContext) -> ExecutionContext:
        module = self._ports.config_resolver
        return self._invoke_step(
            context,
            module_id=module.module_id,
            raw_phase_name="config_resolved",
            action=lambda ctx: module.resolve(ctx),
        )

    def _invoke_pipeline_module(self, context: ExecutionContext, module) -> ExecutionContext:
        return self._invoke_step(
            context,
            module_id=module.module_id,
            raw_phase_name=module.phase_name,
            action=lambda ctx: module.execute(ctx),
        )

    def _invoke_reason_generator(self, context: ExecutionContext) -> ExecutionContext:
        module = self._ports.reason_generator
        phase_name = resolve_aggregated_phase_name(
            module.module_id,
            module.phase_name,
        )
        if phase_name is None:
            msg = f"phase_name is not configured for {module.module_id}"
            raise ModuleExecutionError(
                module.module_id,
                msg,
                error_code=MODULE_ERROR_CODES[module.module_id],
                phase_name=module.phase_name,
            )

        started = perf_counter()

        self._ports.phase_log_writer.record_phase(
            context,
            phase_name=phase_name,
            phase_status=PhaseStatus.STARTED,
            module_id=module.module_id,
        )

        result = module.generate(context)
        duration_ms = int((perf_counter() - started) * 1_000)

        if result.outcome == ReasonGenerationOutcome.UNRECOVERABLE:
            context = inject_generic_reason_fallback(context)
            self._ports.phase_log_writer.record_phase(
                context,
                phase_name=phase_name,
                phase_status=PhaseStatus.SUCCEEDED,
                module_id=module.module_id,
                duration_ms=duration_ms,
            )
            return context

        if context.recommendation_result is None:
            raise ModuleExecutionError(
                module.module_id,
                "recommendation result missing before reason merge",
                error_code=MODULE_ERROR_CODES[module.module_id],
                phase_name=phase_name,
            )

        context.recommendation_result = _merge_reason_into_result(
            context.recommendation_result,
            reason_summary=result.reason_summary or GENERIC_REASON_SUMMARY,
            is_fallback=result.is_fallback,
        )

        self._ports.phase_log_writer.record_phase(
            context,
            phase_name=phase_name,
            phase_status=PhaseStatus.SUCCEEDED,
            module_id=module.module_id,
            duration_ms=duration_ms,
        )
        return context

    def _invoke_step(
        self,
        context: ExecutionContext,
        *,
        module_id: str,
        raw_phase_name: str,
        action,
    ) -> ExecutionContext:
        phase_name = resolve_aggregated_phase_name(module_id, raw_phase_name)
        started = perf_counter()

        if phase_name is not None:
            self._ports.phase_log_writer.record_phase(
                context,
                phase_name=phase_name,
                phase_status=PhaseStatus.STARTED,
                module_id=module_id,
            )

        try:
            updated = action(context)
        except Exception as exc:  # noqa: BLE001 - delegated to MOD-RECO-024
            error_code = MODULE_ERROR_CODES.get(module_id, "GRS-REC-999")
            failed_phase_name = normalize_orchestrator_phase_name(
                module_id,
                raw_phase_name,
            )
            self._ports.phase_log_writer.record_phase(
                context,
                phase_name=failed_phase_name,
                phase_status=PhaseStatus.FAILED,
                module_id=module_id,
                error_code=error_code,
            )
            raise ModuleExecutionError(
                module_id,
                str(exc),
                error_code=error_code,
                phase_name=failed_phase_name,
            ) from exc

        duration_ms = int((perf_counter() - started) * 1_000)
        if phase_name is not None:
            self._ports.phase_log_writer.record_phase(
                updated,
                phase_name=phase_name,
                phase_status=PhaseStatus.SUCCEEDED,
                module_id=module_id,
                duration_ms=duration_ms,
            )
        return updated

    def _record_matching_completed_after_short_circuit(
        self,
        context: ExecutionContext,
    ) -> ExecutionContext:
        """MOD-RECO-014 §16.1 No.8: 015 以降スキップ時も matching_completed を記録する。"""
        self._ports.phase_log_writer.record_phase(
            context,
            phase_name="matching_completed",
            phase_status=PhaseStatus.STARTED,
            module_id="MOD-RECO-014",
        )
        self._ports.phase_log_writer.record_phase(
            context,
            phase_name="matching_completed",
            phase_status=PhaseStatus.SUCCEEDED,
            module_id="MOD-RECO-014",
        )
        return context

    def _should_short_circuit_after_feature_matcher(
        self,
        context: ExecutionContext,
    ) -> bool:
        """MOD-RECO-014 成功後、Matching 対象 0 件なら 015 以降を呼ばない（§16.1 No.8）。"""
        candidate_count = getattr(context, "feature_matcher_candidate_count", None)
        if candidate_count == 0:
            return True

        feature_match_result = getattr(context, "feature_match_result", None)
        if feature_match_result is None:
            return False

        if feature_match_result.total_matched == 0:
            return True
        return not feature_match_result.entries

    def _prepare_empty_result_after_matching_zero(
        self,
        context: ExecutionContext,
    ) -> ExecutionContext:
        run_id = context.run_id or "run-empty"
        context.recommendation_result = RecommendationResult(
            run_id=run_id,
            request_id=context.recommendation_request.request_id,
            items=(),
            result_status=ResultStatus.EMPTY,
            version_info=dict(context.config_versions),
        )
        return context

    def _expected_completed_modules(self, context: ExecutionContext) -> list[str]:
        if (
            "MOD-RECO-014" in context.completed_modules
            and self._should_short_circuit_after_feature_matcher(context)
        ):
            return [
                module_id
                for module_id in ORCHESTRATOR_MODULE_ORDER
                if module_id not in _MATCHING_RANKING_MODULE_IDS
            ]
        return list(ORCHESTRATOR_MODULE_ORDER)

    def _assert_module_order(self, context: ExecutionContext) -> None:
        expected = self._expected_completed_modules(context)
        actual = [
            module_id
            for module_id in context.completed_modules
            if module_id in expected
        ]
        if actual != expected:
            raise ModuleExecutionError(
                "MOD-RECO-001",
                f"module order mismatch: expected {expected}, got {actual}",
                error_code="GRS-REC-002",
                phase_name=normalize_orchestrator_phase_name(
                    "MOD-RECO-001",
                    "pipeline_control",
                ),
            )


def _merge_reason_into_result(
    result: RecommendationResult,
    *,
    reason_summary: str,
    is_fallback: bool,
) -> RecommendationResult:
    items = tuple(
        RecommendationResultItem(
            item_id=item.item_id,
            rank=item.rank,
            final_score=item.final_score,
            reason_summary=reason_summary,
            reason_status=ReasonStatus.COMPLETED,
            is_fallback=is_fallback,
        )
        for item in result.items
    )
    return RecommendationResult(
        run_id=result.run_id,
        request_id=result.request_id,
        items=items,
        result_status=result.result_status,
        version_info=result.version_info,
    )
