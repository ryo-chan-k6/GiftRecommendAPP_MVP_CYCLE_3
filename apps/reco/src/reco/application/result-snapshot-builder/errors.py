"""MOD-RECO-022 Result Snapshot Builder errors."""

from __future__ import annotations

from .constants import (
    ITEM_INFO_ERROR_CODE,
    MODULE_ID,
    RESULT_ITEM_SAVE_ERROR_CODE,
    SNAPSHOT_BUILD_ERROR_CODE,
    SURFACE_ERROR_CODE,
)


class ResultSnapshotBuilderError(Exception):
    """Snapshot Builder failure propagated to Orchestrator (GRS-REC-012)."""

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

__all__ = [
    "ITEM_INFO_ERROR_CODE",
    "MODULE_ERROR_MODULE_ID",
    "RESULT_ITEM_SAVE_ERROR_CODE",
    "SNAPSHOT_BUILD_ERROR_CODE",
    "SURFACE_ERROR_CODE",
    "ResultSnapshotBuilderError",
]
