"""App-phase → DDL ``phase_name`` mapping for Batch observability (MVP).

共通 map: ``plan``→``batch_started``, ``finalize``→``batch_completed``.
DDL 同一名の app phase は identity。未マップは DB skip + warn。
"""

from __future__ import annotations

import logging

from batch.application.observability.phase_log import (
    ALLOWED_BATCH_PHASE_NAMES,
    ALLOWED_PHASE_STATUSES,
)

logger = logging.getLogger(__name__)

# 共通アプリ phase → DDL phase_name（genre_sync 専用 dict を統合）
DEFAULT_APP_PHASE_TO_DDL: dict[str, str] = {
    "plan": "batch_started",
    "finalize": "batch_completed",
    # DDL identity（app phase が DDL と同名のとき）
    "batch_started": "batch_started",
    "cursor_loaded": "cursor_loaded",
    "external_api_called": "external_api_called",
    "raw_saved": "raw_saved",
    "raw_metadata_saved": "raw_metadata_saved",
    "staging_transformed": "staging_transformed",
    "diff_judged": "diff_judged",
    "item_imported": "item_imported",
    "item_image_imported": "item_image_imported",
    "popularity_signal_imported": "popularity_signal_imported",
    "item_feature_generated": "item_feature_generated",
    "item_embedding_generated": "item_embedding_generated",
    "feature_distribution_metric_recorded": "feature_distribution_metric_recorded",
    "summary_created": "summary_created",
    "batch_completed": "batch_completed",
}

# 後方互換エイリアス（旧 genre_sync 専用名）
GENRE_SYNC_APP_PHASE_TO_DDL: dict[str, str] = DEFAULT_APP_PHASE_TO_DDL

# identity が ALLOWED と一致していることを起動時に軽く検証（開発時の drift 検知）
assert set(ALLOWED_BATCH_PHASE_NAMES).issubset(set(DEFAULT_APP_PHASE_TO_DDL.values()))


def map_app_phase_to_ddl(app_phase: str) -> str | None:
    """Return DDL phase_name for a known app phase, or None to skip DB write."""

    return DEFAULT_APP_PHASE_TO_DDL.get(app_phase)


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
