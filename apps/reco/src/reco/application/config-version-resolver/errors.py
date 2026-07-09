"""MOD-RECO-003 config resolution errors."""

from __future__ import annotations


class ConfigResolveError(Exception):
    """Raised when Config / Version resolution fails.

    Orchestrator maps this to GRS-REC-003 (surface). ``detail_code`` holds GRS-CFG-*.
    """

    def __init__(self, detail_code: str, message: str) -> None:
        super().__init__(message)
        self.detail_code = detail_code
        self.message = message
