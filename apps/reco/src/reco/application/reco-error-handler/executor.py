"""MOD-RECO-024 Reco Error Handler implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reco.application.recommendation_orchestrator.errors import RecoError
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import MODULE_ID, SURFACE_ERROR_CODE_UNKNOWN
from .error_log_builder import build_error_log_write_request, build_test_seam_event
from .message_masker import mask_sensitive_text
from .models import ErrorLogWriteRequest
from .ports import ErrorLogWriterPort
from .surface_code_resolver import resolve_surface_code

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class NoOpErrorLogWriter:
    """029 未実装時の no-op Error Log Writer."""

    module_id: str = "MOD-RECO-029"
    requests: list[ErrorLogWriteRequest] = field(default_factory=list)

    def write(self, request: ErrorLogWriteRequest) -> None:
        self.requests.append(request)


@dataclass
class RecoErrorHandler:
    """ErrorHandlerPort implementation for MOD-RECO-024."""

    error_log_writer: ErrorLogWriterPort = field(default_factory=NoOpErrorLogWriter)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    append_test_seam_events: bool = True

    def handle(
        self,
        context: ExecutionContext,
        *,
        module_id: str,
        error_code: str,
        message: str,
        phase_name: str | None = None,
        cause: BaseException | None = None,
    ) -> RecoError:
        try:
            return self._handle_internal(
                context,
                module_id=module_id,
                error_code=error_code,
                message=message,
                phase_name=phase_name,
                cause=cause,
            )
        except Exception as exc:  # noqa: BLE001 — secondary loop avoidance (§10.2)
            self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).error(
                "reco_error_handler_internal_failure",
                module_id=self.module_id,
                source_module_id=module_id,
                failure_type=type(exc).__name__,
            )
            return RecoError(
                error_code=SURFACE_ERROR_CODE_UNKNOWN,
                message="Reco Error Handler internal failure",
                module_id=module_id,
                phase_name=phase_name,
            )

    def _handle_internal(
        self,
        context: ExecutionContext,
        *,
        module_id: str,
        error_code: str,
        message: str,
        phase_name: str | None,
        cause: BaseException | None,
    ) -> RecoError:
        if not module_id.strip() or not message.strip():
            surface_code = SURFACE_ERROR_CODE_UNKNOWN
            detail_error_code = None
            safe_message = mask_sensitive_text(message or "invalid error handler input")
        else:
            surface_code, detail_error_code = resolve_surface_code(
                module_id=module_id,
                error_code=error_code,
                cause=cause,
            )
            safe_message = mask_sensitive_text(message)

        reco_error = RecoError(
            error_code=surface_code,
            message=safe_message,
            module_id=module_id,
            phase_name=phase_name,
        )

        write_request = build_error_log_write_request(
            context,
            surface_code=surface_code,
            detail_error_code=detail_error_code,
            module_id=module_id,
            message=safe_message,
            phase_name=phase_name,
        )
        self._delegate_error_log(context, write_request)

        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "reco_error_standardized",
            module_id=self.module_id,
            source_module_id=module_id,
            surface_error_code=surface_code,
            phase_name=phase_name,
        )

        return reco_error

    def _delegate_error_log(
        self,
        context: ExecutionContext,
        request: ErrorLogWriteRequest,
    ) -> None:
        try:
            self.error_log_writer.write(request)
        except Exception as exc:  # noqa: BLE001 — 029 failure must not block RecoError
            self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
                "error_log_writer_write_failed",
                module_id=self.module_id,
                writer_module_id=getattr(self.error_log_writer, "module_id", None),
                failure_type=type(exc).__name__,
            )
            return

        if self.append_test_seam_events:
            context.error_log_events.append(build_test_seam_event(request))


def build_default_reco_error_handler() -> RecoErrorHandler:
    return RecoErrorHandler()
