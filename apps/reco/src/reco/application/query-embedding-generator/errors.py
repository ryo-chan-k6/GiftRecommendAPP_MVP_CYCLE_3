"""MOD-RECO-010 Query Embedding Generator errors."""

from __future__ import annotations

from .constants import MODULE_ID, SURFACE_ERROR_CODE


class QueryEmbeddingGenerationError(Exception):
    """Query Embedding generation failure propagated to Orchestrator."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = SURFACE_ERROR_CODE,
        detail_error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.detail_error_code = detail_error_code
        self.message = message


MODULE_ERROR_MODULE_ID = MODULE_ID
