"""In-memory repositories for BATCH-008 unit tests / scaffold wiring.

Production will replace these with real DB adapters (IF-DB-BATCH-006 / 009 / 021).
Retention DELETE は本 Batch の対象外（T7）。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone

from batch.application.item_active_status.models import (
    ActiveStatusValue,
    CandidateRow,
    DiffSuggestion,
    ItemRow,
)
from batch.infrastructure.db import DbWriter


def _is_active_for(status: ActiveStatusValue) -> bool:
    """item テーブル定義書: is_active = (active_status = 'active')."""

    return status == "active"


@dataclass
class ItemActiveStatusRepositories:
    """Facade for Item / candidate / Diff / logs used by BATCH-008 Applier."""

    db_writer: DbWriter
    items: dict[tuple[str, str], ItemRow] = field(default_factory=dict)
    candidates: dict[str, CandidateRow] = field(default_factory=dict)
    diffs: dict[str, DiffSuggestion] = field(default_factory=dict)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    deleted_candidate_ids: list[str] = field(default_factory=list)

    def seed_item(self, row: ItemRow) -> None:
        self.items[row.idempotency_key] = ItemRow(
            source=row.source,
            external_item_code=row.external_item_code,
            active_status=row.active_status,
            item_id=row.item_id,
            is_active=_is_active_for(row.active_status),
        )

    def seed_candidate(self, row: CandidateRow) -> None:
        self.candidates[row.candidate_id] = row

    def seed_diff(self, row: DiffSuggestion) -> None:
        self.diffs[row.product_diff_result_id] = row

    def get_item(self, *, source: str, external_item_code: str) -> ItemRow | None:
        return self.items.get((source, external_item_code))

    def list_detected_candidates(
        self,
        *,
        source: str = "rakuten",
        batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
    ) -> list[CandidateRow]:
        codes = set(external_item_codes) if external_item_codes else None
        rows: list[CandidateRow] = []
        for row in self.candidates.values():
            if row.candidate_status != "detected":
                continue
            if row.source != source:
                continue
            if batch_run_id is not None and row.batch_run_id != batch_run_id:
                continue
            if codes is not None and row.external_item_code not in codes:
                continue
            rows.append(row)
        rows.sort(key=lambda r: r.detected_at)
        return rows

    def list_diff_suggestions(
        self,
        *,
        source: str = "rakuten",
        batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
    ) -> list[DiffSuggestion]:
        codes = set(external_item_codes) if external_item_codes else None
        rows: list[DiffSuggestion] = []
        for row in self.diffs.values():
            if row.source != source:
                continue
            if batch_run_id is not None and row.batch_run_id != batch_run_id:
                continue
            if codes is not None and row.external_item_code not in codes:
                continue
            # §9.2: unavailable のみ制限提案。他は提案なし（行は読んでも proposed=None）
            rows.append(row)
        rows.sort(key=lambda r: r.judged_at)
        return rows

    def update_item_active_status(
        self,
        *,
        source: str,
        external_item_code: str,
        active_status: ActiveStatusValue,
        fail: bool = False,
    ) -> bool:
        if fail:
            return False
        key = (source, external_item_code)
        existing = self.items.get(key)
        if existing is None:
            return False
        updated = ItemRow(
            source=existing.source,
            external_item_code=existing.external_item_code,
            active_status=active_status,
            item_id=existing.item_id,
            is_active=_is_active_for(active_status),
        )
        self.items[key] = updated
        self.db_writer.write_rows(
            "item",
            (
                {
                    "source": source,
                    "external_item_code": external_item_code,
                    "active_status": active_status,
                    "is_active": updated.is_active,
                },
            ),
        )
        return True

    def mark_candidate_applied(self, candidate_id: str, *, applied_at: datetime | None = None) -> None:
        existing = self.candidates.get(candidate_id)
        if existing is None or existing.candidate_status != "detected":
            return
        at = applied_at or datetime.now(timezone.utc)
        updated = CandidateRow(
            candidate_id=existing.candidate_id,
            batch_run_id=existing.batch_run_id,
            source=existing.source,
            external_item_code=existing.external_item_code,
            candidate_active_status=existing.candidate_active_status,
            candidate_status="applied",
            detected_at=existing.detected_at,
            detection_basis=existing.detection_basis,
            reason_code=existing.reason_code,
            item_id=existing.item_id,
            applied_at=at,
        )
        self.candidates[candidate_id] = updated
        self.db_writer.write_rows(
            "item_active_status_candidate",
            (
                {
                    "item_active_status_candidate_id": candidate_id,
                    "candidate_status": "applied",
                    "applied_at": at.isoformat(),
                },
            ),
        )

    def mark_candidate_superseded(self, candidate_id: str) -> None:
        self._mark_terminal(candidate_id, status="superseded")

    def mark_candidate_discarded(self, candidate_id: str) -> None:
        self._mark_terminal(candidate_id, status="discarded")

    def _mark_terminal(self, candidate_id: str, *, status: str) -> None:
        existing = self.candidates.get(candidate_id)
        if existing is None or existing.candidate_status != "detected":
            return
        updated = CandidateRow(
            candidate_id=existing.candidate_id,
            batch_run_id=existing.batch_run_id,
            source=existing.source,
            external_item_code=existing.external_item_code,
            candidate_active_status=existing.candidate_active_status,
            candidate_status=status,  # type: ignore[arg-type]
            detected_at=existing.detected_at,
            detection_basis=existing.detection_basis,
            reason_code=existing.reason_code,
            item_id=existing.item_id,
            applied_at=None,
        )
        self.candidates[candidate_id] = updated
        self.db_writer.write_rows(
            "item_active_status_candidate",
            (
                {
                    "item_active_status_candidate_id": candidate_id,
                    "candidate_status": status,
                },
            ),
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})

    def record_error(self, *, code: str, summary: str, item_code: str | None = None) -> None:
        self.error_logs.append({"code": code, "summary": summary, "item_code": item_code})
