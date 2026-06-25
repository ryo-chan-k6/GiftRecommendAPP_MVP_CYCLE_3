"""Reco orchestrator error types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RecoError:
    """Standardized reco error propagated to callers (MOD-RECO-024 経由)."""

    error_code: str
    message: str
    module_id: str | None = None
    phase_name: str | None = None


class ModuleExecutionError(Exception):
    """Raised when a downstream module fails fatally."""

    def __init__(
        self,
        module_id: str,
        message: str,
        *,
        error_code: str,
        phase_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.module_id = module_id
        self.error_code = error_code
        self.phase_name = phase_name
