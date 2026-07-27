"""Repositories for BATCH-008 Item Active Status.

``list_detected_candidates`` / ``list_diff_suggestions`` / ``get_item`` use ``DbReader``
when injected (Wave C). Without a reader, in-memory seed remains for scaffold / UT.

Retention DELETE は本 Batch の対象外（T7）。書込本格化は out of scope。
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timezone

from batch.application.item_active_status.models import (
    ActiveStatusValue,
    CandidateRow,
    DiffSuggestion,
    ItemRow,
)
from batch.infrastructure.db import DbReader, DbWriter

_CANDIDATE_COLUMNS = (
    "item_active_status_candidate_id",
    "batch_run_id",
    "source",
    "external_item_code",
    "candidate_active_status",
    "candidate_status",
    "detected_at",
    "detection_basis",
    "reason_code",
    "item_id",
    "applied_at",
    "updated_at",
)
_DIFF_COLUMNS = (
    "product_diff_result_id",
    "batch_run_id",
    "staging_item_id",
    "external_item_code",
    "diff_status",
    "judged_at",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "active_status",
    "is_active",
)
_STAGING_SOURCE_COLUMNS = ("staging_item_id", "source", "external_item_code")


def _is_active_for(status: ActiveStatusValue) -> bool:
    """item テーブル定義書: is_active = (active_status = 'active')."""

    return status == "active"


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return None


@dataclass
class ItemActiveStatusRepositories:
    """Facade for Item / candidate / Diff / logs used by BATCH-008 Applier."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
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
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item",
                columns=_ITEM_COLUMNS,
                equals=(("source", source), ("external_item_code", external_item_code)),
                limit=1,
            )
            if not result.rows:
                return None
            return self._cache_item_row(result.rows[0])
        return self.items.get((source, external_item_code))

    def list_detected_candidates(
        self,
        *,
        source: str = "rakuten",
        batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
    ) -> list[CandidateRow]:
        if self.db_reader is not None:
            return self._list_detected_candidates_from_db(
                source=source,
                batch_run_id=batch_run_id,
                external_item_codes=external_item_codes,
            )

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

    def _list_detected_candidates_from_db(
        self,
        *,
        source: str,
        batch_run_id: str | None,
        external_item_codes: Sequence[str] | None,
    ) -> list[CandidateRow]:
        reader = self.db_reader
        if reader is None:
            return []

        equals: list[tuple[str, object]] = [
            ("source", source),
            ("candidate_status", "detected"),
        ]
        if batch_run_id is not None:
            equals.append(("batch_run_id", batch_run_id))

        result = reader.fetch_rows(
            "item_active_status_candidate",
            columns=_CANDIDATE_COLUMNS,
            equals=tuple(equals),
            order_by=("detected_at",),
            limit=5000,
        )
        codes = set(external_item_codes) if external_item_codes else None
        rows: list[CandidateRow] = []
        for row in result.rows:
            candidate = self._row_to_candidate(row)
            if codes is not None and candidate.external_item_code not in codes:
                continue
            self.candidates[candidate.candidate_id] = candidate
            rows.append(candidate)
        rows.sort(key=lambda r: r.detected_at)
        return rows

    def list_diff_suggestions(
        self,
        *,
        source: str = "rakuten",
        batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
    ) -> list[DiffSuggestion]:
        if self.db_reader is not None:
            return self._list_diff_suggestions_from_db(
                source=source,
                batch_run_id=batch_run_id,
                external_item_codes=external_item_codes,
            )

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

    def _list_diff_suggestions_from_db(
        self,
        *,
        source: str,
        batch_run_id: str | None,
        external_item_codes: Sequence[str] | None,
    ) -> list[DiffSuggestion]:
        reader = self.db_reader
        if reader is None:
            return []

        equals: tuple[tuple[str, object], ...] = ()
        if batch_run_id is not None:
            equals = (("batch_run_id", batch_run_id),)

        result = reader.fetch_rows(
            "product_diff_result",
            columns=_DIFF_COLUMNS,
            equals=equals,
            order_by=("judged_at",),
            limit=5000,
        )
        codes = set(external_item_codes) if external_item_codes else None
        rows: list[DiffSuggestion] = []
        for row in result.rows:
            resolved_source = self._resolve_diff_source(row)
            if resolved_source != source:
                continue
            external_item_code = str(row["external_item_code"])
            if codes is not None and external_item_code not in codes:
                continue
            diff_status = str(row["diff_status"])
            proposed: ActiveStatusValue | None = (
                "unavailable" if diff_status == "unavailable" else None
            )
            judged_at = _as_datetime(row.get("judged_at")) or datetime.now(UTC)
            suggestion = DiffSuggestion(
                product_diff_result_id=str(row["product_diff_result_id"]),
                batch_run_id=str(row["batch_run_id"]),
                source=resolved_source,
                external_item_code=external_item_code,
                diff_status=diff_status,
                proposed_active_status=proposed,
                judged_at=judged_at,
            )
            self.diffs[suggestion.product_diff_result_id] = suggestion
            rows.append(suggestion)
        rows.sort(key=lambda r: r.judged_at)
        return rows

    def _resolve_diff_source(self, row: dict[str, object]) -> str:
        """Resolve source via staging_item (by staging_item_id) or item (by code). No JOIN."""

        reader = self.db_reader
        staging_item_id = row.get("staging_item_id")
        external_item_code = str(row["external_item_code"])
        if reader is not None and staging_item_id is not None:
            staging = reader.fetch_rows(
                "staging_item",
                columns=_STAGING_SOURCE_COLUMNS,
                equals=(("staging_item_id", staging_item_id),),
                limit=1,
            )
            if staging.rows:
                return str(staging.rows[0].get("source") or "rakuten")

        if reader is not None:
            item = reader.fetch_rows(
                "item",
                columns=_ITEM_COLUMNS,
                equals=(("external_item_code", external_item_code),),
                limit=1,
            )
            if item.rows:
                return str(item.rows[0].get("source") or "rakuten")

        return "rakuten"

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
        if existing is None and self.db_reader is not None:
            existing = self.get_item(source=source, external_item_code=external_item_code)
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
            updated_at=at,
        )
        self.candidates[candidate_id] = updated
        self.db_writer.write_rows(
            "item_active_status_candidate",
            (
                {
                    "item_active_status_candidate_id": candidate_id,
                    "candidate_status": "applied",
                    "applied_at": at.isoformat(),
                    "updated_at": at.isoformat(),
                },
            ),
        )

    def mark_candidate_superseded(self, candidate_id: str, *, updated_at: datetime | None = None) -> None:
        self._mark_terminal(candidate_id, status="superseded", updated_at=updated_at)

    def mark_candidate_discarded(self, candidate_id: str, *, updated_at: datetime | None = None) -> None:
        self._mark_terminal(candidate_id, status="discarded", updated_at=updated_at)

    def _mark_terminal(
        self,
        candidate_id: str,
        *,
        status: str,
        updated_at: datetime | None = None,
    ) -> None:
        existing = self.candidates.get(candidate_id)
        if existing is None or existing.candidate_status != "detected":
            return
        at = updated_at or datetime.now(timezone.utc)
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
            updated_at=at,
        )
        self.candidates[candidate_id] = updated
        self.db_writer.write_rows(
            "item_active_status_candidate",
            (
                {
                    "item_active_status_candidate_id": candidate_id,
                    "candidate_status": status,
                    "updated_at": at.isoformat(),
                },
            ),
        )

    def delete_candidate(self, candidate_id: str) -> bool:
        """Physical DELETE for Retention cleanup. Never call for detected."""

        existing = self.candidates.get(candidate_id)
        if existing is None:
            return False
        if existing.candidate_status == "detected":
            return False
        del self.candidates[candidate_id]
        self.deleted_candidate_ids.append(candidate_id)
        self.db_writer.write_rows(
            "item_active_status_candidate",
            (
                {
                    "item_active_status_candidate_id": candidate_id,
                    "op": "delete",
                },
            ),
        )
        return True

    def list_candidates_for_retention(self) -> list[CandidateRow]:
        return list(self.candidates.values())

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})

    def record_error(self, *, code: str, summary: str, item_code: str | None = None) -> None:
        self.error_logs.append({"code": code, "summary": summary, "item_code": item_code})

    def _cache_item_row(self, row: dict[str, object]) -> ItemRow:
        status = str(row.get("active_status") or "active")
        if status not in {"active", "inactive", "unavailable", "excluded"}:
            status = "active"
        item = ItemRow(
            source=str(row.get("source") or "rakuten"),
            external_item_code=str(row["external_item_code"]),
            active_status=status,  # type: ignore[arg-type]
            item_id=str(row["item_id"]) if row.get("item_id") is not None else None,
            is_active=(
                bool(row["is_active"])
                if row.get("is_active") is not None
                else _is_active_for(status)  # type: ignore[arg-type]
            ),
        )
        self.items[item.idempotency_key] = item
        return item

    def _row_to_candidate(self, row: dict[str, object]) -> CandidateRow:
        status = str(row.get("candidate_status") or "detected")
        cand_status = str(row.get("candidate_active_status") or "unavailable")
        detected_at = _as_datetime(row.get("detected_at")) or datetime.now(UTC)
        return CandidateRow(
            candidate_id=str(row["item_active_status_candidate_id"]),
            batch_run_id=str(row["batch_run_id"]),
            source=str(row.get("source") or "rakuten"),
            external_item_code=str(row["external_item_code"]),
            candidate_active_status=cand_status,  # type: ignore[arg-type]
            candidate_status=status,  # type: ignore[arg-type]
            detected_at=detected_at,
            detection_basis=(
                str(row["detection_basis"]) if row.get("detection_basis") is not None else None
            ),
            reason_code=str(row["reason_code"]) if row.get("reason_code") is not None else None,
            item_id=str(row["item_id"]) if row.get("item_id") is not None else None,
            applied_at=_as_datetime(row.get("applied_at")),
            updated_at=_as_datetime(row.get("updated_at")),
        )
