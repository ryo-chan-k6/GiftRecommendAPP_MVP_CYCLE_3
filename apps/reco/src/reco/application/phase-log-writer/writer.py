"""MOD-RECO-028 Phase Log Writer implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.application.recommendation_orchestrator.ports import PhaseStatus
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, TERMINAL_PHASE_STATUSES
from .mapper import (
    build_in_memory_event,
    build_started_record,
    build_terminal_detail_json,
    buffered_event_to_kwargs,
)
from .models import BufferedPhaseEvent
from .ports import PhaseLogRepository
from .repository import InMemoryPhaseLogRepository
from .validation import normalize_phase_name


@dataclass
class _RunPhaseState:
    """Run-scoped state for started rows and pre-run buffering."""

    open_phase_ids: dict[str, str] = field(default_factory=dict)
    buffered_events: list[BufferedPhaseEvent] = field(default_factory=list)


@dataclass
class PhaseLogWriter:
    """PhaseLogWriterPort implementation for MOD-RECO-028."""

    repository: PhaseLogRepository = field(default_factory=InMemoryPhaseLogRepository)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    _run_states: dict[str, _RunPhaseState] = field(default_factory=dict)

    def record_phase(
        self,
        context: ExecutionContext,
        *,
        phase_name: str,
        phase_status: PhaseStatus,
        module_id: str | None = None,
        error_code: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        status_value = phase_status.value
        self._append_in_memory_event(
            context,
            phase_name=phase_name,
            phase_status=status_value,
            module_id=module_id,
            error_code=error_code,
            duration_ms=duration_ms,
        )

        normalized_name = normalize_phase_name(phase_name)
        if normalized_name is None:
            self._log_warn(
                context,
                event="phase_log_invalid_phase_name",
                phase_name=phase_name,
                phase_status=status_value,
            )
            return

        run_id = context.run_id
        if run_id is None:
            state = self._state_for_pending(context)
            state.buffered_events.append(
                BufferedPhaseEvent(
                    phase_name=normalized_name,
                    phase_status=status_value,
                    module_id=module_id,
                    error_code=error_code,
                    duration_ms=duration_ms,
                )
            )
            return

        self._flush_buffered_events(context, run_id=run_id)
        self._persist_event(
            context,
            run_id=run_id,
            phase_name=normalized_name,
            phase_status=status_value,
            module_id=module_id,
            error_code=error_code,
            duration_ms=duration_ms,
        )

    def _append_in_memory_event(
        self,
        context: ExecutionContext,
        *,
        phase_name: str,
        phase_status: str,
        module_id: str | None,
        error_code: str | None,
        duration_ms: int | None,
    ) -> None:
        context.phase_log_events.append(
            build_in_memory_event(
                context,
                phase_name=phase_name,
                phase_status=phase_status,
                module_id=module_id,
                error_code=error_code,
                duration_ms=duration_ms,
            )
        )

    def _state_key_for_run(self, run_id: str) -> str:
        return f"run:{run_id}"

    def _state_key_for_pending(self, context: ExecutionContext) -> str:
        request_id = context.recommendation_request.request_id
        return f"pending:{context.trace_id}:{request_id}"

    def _state_for_run(self, run_id: str) -> _RunPhaseState:
        key = self._state_key_for_run(run_id)
        state = self._run_states.get(key)
        if state is None:
            state = _RunPhaseState()
            self._run_states[key] = state
        return state

    def _state_for_pending(self, context: ExecutionContext) -> _RunPhaseState:
        key = self._state_key_for_pending(context)
        state = self._run_states.get(key)
        if state is None:
            state = _RunPhaseState()
            self._run_states[key] = state
        return state

    def _transfer_pending_state(self, context: ExecutionContext, *, run_id: str) -> _RunPhaseState:
        pending_key = self._state_key_for_pending(context)
        run_key = self._state_key_for_run(run_id)
        pending_state = self._run_states.pop(pending_key, _RunPhaseState())
        run_state = self._run_states.setdefault(run_key, _RunPhaseState())
        run_state.buffered_events.extend(pending_state.buffered_events)
        run_state.open_phase_ids.update(pending_state.open_phase_ids)
        return run_state

    def _flush_buffered_events(self, context: ExecutionContext, *, run_id: str) -> None:
        state = self._transfer_pending_state(context, run_id=run_id)
        if not state.buffered_events:
            return

        buffered = list(state.buffered_events)
        state.buffered_events.clear()
        for event in buffered:
            kwargs = buffered_event_to_kwargs(event)
            self._persist_event(
                context,
                run_id=run_id,
                phase_name=str(kwargs["phase_name"]),
                phase_status=str(kwargs["phase_status"]),
                module_id=kwargs["module_id"] if kwargs["module_id"] is None else str(kwargs["module_id"]),
                error_code=kwargs["error_code"] if kwargs["error_code"] is None else str(kwargs["error_code"]),
                duration_ms=(
                    int(kwargs["duration_ms"])
                    if kwargs["duration_ms"] is not None
                    else None
                ),
            )

    def _persist_event(
        self,
        context: ExecutionContext,
        *,
        run_id: str,
        phase_name: str,
        phase_status: str,
        module_id: str | None,
        error_code: str | None,
        duration_ms: int | None,
    ) -> None:
        if phase_status == PhaseStatus.STARTED.value:
            self._insert_started(
                context,
                run_id=run_id,
                phase_name=phase_name,
            )
            return

        if phase_status in TERMINAL_PHASE_STATUSES:
            self._update_terminal(
                context,
                run_id=run_id,
                phase_name=phase_name,
                phase_status=phase_status,
                module_id=module_id,
                error_code=error_code,
                duration_ms=duration_ms,
            )
            return

        self._log_warn(
            context,
            event="phase_log_unsupported_phase_status",
            phase_name=phase_name,
            phase_status=phase_status,
            run_id=run_id,
        )

    def _insert_started(
        self,
        context: ExecutionContext,
        *,
        run_id: str,
        phase_name: str,
    ) -> None:
        try:
            record = build_started_record(context, phase_name=phase_name, owner_id=run_id)
            phase_log_id = self.repository.insert_started(record)
            state = self._state_for_run(run_id)
            state.open_phase_ids[phase_name] = phase_log_id
            self.logger.bind(trace_id=context.trace_id, run_id=run_id).info(
                "phase_log_inserted",
                module_id=self.module_id,
                phase_log_id=phase_log_id,
                phase_name=phase_name,
                phase_status=PhaseStatus.STARTED.value,
            )
        except Exception as exc:  # noqa: BLE001 — 永続化失敗は推薦返却をブロックしない
            self._log_warn(
                context,
                event="phase_log_insert_failed",
                phase_name=phase_name,
                run_id=run_id,
                error_type=type(exc).__name__,
            )

    def _update_terminal(
        self,
        context: ExecutionContext,
        *,
        run_id: str,
        phase_name: str,
        phase_status: str,
        module_id: str | None,
        error_code: str | None,
        duration_ms: int | None,
    ) -> None:
        state = self._state_for_run(run_id)
        phase_log_id = state.open_phase_ids.get(phase_name)
        if phase_log_id is None:
            self._log_warn(
                context,
                event="phase_log_terminal_without_started",
                phase_name=phase_name,
                phase_status=phase_status,
                run_id=run_id,
            )
            return

        try:
            completed_at = datetime.now(UTC)
            detail_json = build_terminal_detail_json(context, module_id=module_id)
            self.repository.update_terminal(
                phase_log_id,
                phase_status=phase_status,
                completed_at=completed_at,
                duration_ms=duration_ms,
                error_code=error_code,
                detail_json=detail_json,
            )
            state.open_phase_ids.pop(phase_name, None)
            self.logger.bind(trace_id=context.trace_id, run_id=run_id).info(
                "phase_log_updated",
                module_id=self.module_id,
                phase_log_id=phase_log_id,
                phase_name=phase_name,
                phase_status=phase_status,
            )
        except Exception as exc:  # noqa: BLE001 — 永続化失敗は推薦返却をブロックしない
            self._log_warn(
                context,
                event="phase_log_update_failed",
                phase_name=phase_name,
                phase_status=phase_status,
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


def build_default_phase_log_writer() -> PhaseLogWriter:
    return PhaseLogWriter()
