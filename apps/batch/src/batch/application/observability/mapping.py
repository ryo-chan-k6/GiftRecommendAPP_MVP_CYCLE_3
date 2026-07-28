"""App-phase → DDL ``phase_name`` mapping for Batch observability (MVP).

事実（実装）: genre_sync は ``plan`` / ``finalize`` のみ DB へマッピングする。
DDL ``phase_log``（owner_type=batch_run）の ``phase_name`` は固定 CHECK のため、
アプリの plan/finalize 等をそのまま INSERT できない。
"""

from __future__ import annotations

import logging

from batch.application.observability.phase_log import ALLOWED_PHASE_STATUSES

logger = logging.getLogger(__name__)

# MVP 代表マッピング（Human Review 対象）
GENRE_SYNC_APP_PHASE_TO_DDL: dict[str, str] = {
    "plan": "batch_started",
    "finalize": "batch_completed",
}


def map_app_phase_to_ddl(app_phase: str) -> str | None:
    """Return DDL phase_name for a known app phase, or None to skip DB write."""

    return GENRE_SYNC_APP_PHASE_TO_DDL.get(app_phase)


def map_app_phase_status(app_status: str) -> str:
    """Map app phase status to DDL ``phase_status``.

    ``succeeded`` / ``failed`` / ``started`` / ``skipped`` → 同名。
    それ以外（例: ``partially_succeeded``）→ ``failed``（失敗扱い）。
    """

    if app_status in ALLOWED_PHASE_STATUSES:
        return app_status
    return "failed"


def warn_unmapped_app_phase(app_phase: str) -> None:
    """Log when an app phase has no DDL mapping (in-memory only)."""

    logger.warning(
        "phase_log DB write skipped: app_phase %r has no DDL mapping "
        "(in-memory record kept)",
        app_phase,
    )
