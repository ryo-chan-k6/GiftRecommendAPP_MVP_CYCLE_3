"""MOD-RECO-002 Recommendation Run Recorder errors."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-002"


class RunRecorderError(Exception):
    """Run recording failure propagated to Orchestrator."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class RunStateConflictError(RunRecorderError):
    """Terminal guard or invalid transition (GRS-REC-201)."""

    def __init__(self, message: str) -> None:
        super().__init__("GRS-REC-201", message)
