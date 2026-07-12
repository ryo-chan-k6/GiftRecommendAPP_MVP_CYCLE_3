"""MOD-RECO-023 Reason Generator errors."""

from __future__ import annotations

MODULE_ERROR_MODULE_ID = "MOD-RECO-023"


class ReasonGeneratorError(Exception):
    """Reason Generator モジュール例外。"""

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.error_code = error_code
