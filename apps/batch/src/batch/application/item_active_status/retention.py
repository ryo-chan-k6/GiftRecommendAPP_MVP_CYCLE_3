"""T7 item_active_status_candidate Retention cleanup.

正本: テーブル定義書 §13 / BATCH-004 §18.1.1 / BATCH-008 §11
- detected: 削除しない
- applied: applied_at + retention_days
- superseded / discarded: updated_at + retention_days
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from batch.application.item_active_status.models import CandidateRow, RetentionCleanupResult
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

RETENTION_BATCH_ID = "BATCH-008-RETENTION"
DEFAULT_RETENTION_DAYS = 14
TERMINAL_STATUSES = frozenset({"applied", "superseded", "discarded"})


def retention_cutoff(*, now: datetime, retention_days: int = DEFAULT_RETENTION_DAYS) -> datetime:
    return now - timedelta(days=retention_days)


def retention_anchor(row: CandidateRow) -> datetime | None:
    """Return the timestamp used for Retention age calculation."""

    if row.candidate_status == "detected":
        return None
    if row.candidate_status == "applied":
        return row.applied_at
    if row.candidate_status in {"superseded", "discarded"}:
        return row.updated_at
    return None


def is_retention_eligible(
    row: CandidateRow,
    *,
    now: datetime,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> bool:
    """True when the row may be physically deleted."""

    if row.candidate_status == "detected":
        return False
    if row.candidate_status not in TERMINAL_STATUSES:
        return False
    anchor = retention_anchor(row)
    if anchor is None:
        return False
    return anchor <= retention_cutoff(now=now, retention_days=retention_days)


class RetentionCleanupJob:
    """Deletes terminal candidate rows older than Retention window."""

    def __init__(
        self,
        *,
        repositories: ItemActiveStatusRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()
        self._retention_days = retention_days

    def run(
        self,
        *,
        job_run_id: str,
        now: datetime | None = None,
        dry_run: bool = False,
        trace_id: str | None = None,
    ) -> RetentionCleanupResult:
        bound = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=RETENTION_BATCH_ID, job_run_id=job_run_id)
        clock = now or datetime.now(timezone.utc)

        result = RetentionCleanupResult(
            batch_id=RETENTION_BATCH_ID,
            job_run_id=job_run_id,
            status="failed",
            retention_days=self._retention_days,
        )
        # dataclass is frozen — rebuild via object.__setattr__ avoided; use mutable locals then construct
        scanned = 0
        deleted = 0
        skipped_detected = 0
        skipped_young = 0
        deleted_ids: list[str] = []
        error_codes: list[str] = []

        try:
            rows = self._repos.list_candidates_for_retention()
            scanned = len(rows)
            self._repos.record_phase(phase="scan", status="succeeded")

            for row in rows:
                if row.candidate_status == "detected":
                    skipped_detected += 1
                    continue
                if not is_retention_eligible(
                    row, now=clock, retention_days=self._retention_days
                ):
                    skipped_young += 1
                    continue
                if dry_run:
                    deleted_ids.append(row.candidate_id)
                    deleted += 1
                    continue
                ok = self._repos.delete_candidate(row.candidate_id)
                if ok:
                    deleted += 1
                    deleted_ids.append(row.candidate_id)
                else:
                    # detected ガード等
                    # DDL ^GRS-[A-Z]{3}-[0-9]{3}$ 準拠（GRS-DB-* は2文字で error_log 不可）
                    error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary="retention delete rejected",
                        item_code=row.external_item_code,
                    )

            status = "succeeded"
            if error_codes and deleted:
                status = "partially_succeeded"
            elif error_codes and not deleted:
                status = "failed"

            result = RetentionCleanupResult(
                batch_id=RETENTION_BATCH_ID,
                job_run_id=job_run_id,
                status=status,  # type: ignore[arg-type]
                retention_days=self._retention_days,
                scanned_count=scanned,
                deleted_count=deleted,
                skipped_detected_count=skipped_detected,
                skipped_young_count=skipped_young,
                deleted_candidate_ids=deleted_ids,
                error_codes=error_codes,
            )
            bound.info(
                "retention.cleanup",
                deleted=deleted,
                skipped_detected=skipped_detected,
                skipped_young=skipped_young,
                dry_run=dry_run,
            )
            self._tracker.complete(
                batch_id=RETENTION_BATCH_ID,
                job_run_id=job_run_id,
                status=result.status,
            )
            self._repos.record_phase(phase="finalize", status=result.status)
            return result
        except Exception as exc:  # noqa: BLE001
            self._repos.record_error(code="GRS-BAT-001", summary=str(exc))
            self._tracker.complete(
                batch_id=RETENTION_BATCH_ID, job_run_id=job_run_id, status="failed"
            )
            self._repos.record_phase(phase="finalize", status="failed")
            return RetentionCleanupResult(
                batch_id=RETENTION_BATCH_ID,
                job_run_id=job_run_id,
                status="failed",
                retention_days=self._retention_days,
                scanned_count=scanned,
                deleted_count=deleted,
                skipped_detected_count=skipped_detected,
                skipped_young_count=skipped_young,
                deleted_candidate_ids=deleted_ids,
                error_codes=[*error_codes, "GRS-BAT-001"],
            )
