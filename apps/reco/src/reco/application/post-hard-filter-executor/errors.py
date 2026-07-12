"""MOD-RECO-013 Post Hard Filter Executor errors."""

from __future__ import annotations

from .constants import MODULE_ID, SURFACE_ERROR_CODE


class PostHardFilterError(Exception):
    """Post Hard Filter failure propagated to Orchestrator (GRS-REC-010)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = SURFACE_ERROR_CODE,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


MODULE_ERROR_MODULE_ID = MODULE_ID
