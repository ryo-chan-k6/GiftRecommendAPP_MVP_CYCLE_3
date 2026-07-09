"""MOD-RECO-027 Item Feature Generator errors."""

from __future__ import annotations

from .constants import MODULE_ID, SURFACE_ERROR_CODE


class ItemFeatureGeneratorError(Exception):
    """Item Feature generation failure propagated to Batch (GRS-BAT-008)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = SURFACE_ERROR_CODE,
        internal_error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.internal_error_code = internal_error_code
        self.message = message


MODULE_ERROR_MODULE_ID = MODULE_ID
