"""MOD-RECO-006 Internal Condition Feature Estimator errors."""

from __future__ import annotations

from .constants import MODULE_ID, SURFACE_ERROR_CODE


class InternalFeatureEstimateError(Exception):
    """Internal condition feature estimation failure propagated to Orchestrator."""

    def __init__(self, message: str, *, error_code: str = SURFACE_ERROR_CODE) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


MODULE_ERROR_MODULE_ID = MODULE_ID
