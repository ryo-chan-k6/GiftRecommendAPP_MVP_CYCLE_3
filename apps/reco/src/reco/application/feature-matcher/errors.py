"""MOD-RECO-014 Feature Matcher errors."""

from __future__ import annotations

from .constants import MODULE_ID, SURFACE_ERROR_CODE


class FeatureMatcherError(Exception):
    """Feature Matcher failure propagated to Orchestrator (GRS-REC-011)."""

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
