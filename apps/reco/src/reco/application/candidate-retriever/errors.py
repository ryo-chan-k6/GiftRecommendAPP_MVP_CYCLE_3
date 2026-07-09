"""MOD-RECO-012 Candidate Retriever errors."""

from __future__ import annotations

from .constants import (
    MODULE_ID,
    SURFACE_ERROR_CODE_PRE_FILTER,
    SURFACE_ERROR_CODE_RETRIEVAL,
)


class PreHardFilterError(Exception):
    """Pre Hard Filter phase failure (GRS-REC-008)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = SURFACE_ERROR_CODE_PRE_FILTER,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class RetrievalError(Exception):
    """Vector Retrieval phase failure (GRS-REC-009)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = SURFACE_ERROR_CODE_RETRIEVAL,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


MODULE_ERROR_MODULE_ID = MODULE_ID
