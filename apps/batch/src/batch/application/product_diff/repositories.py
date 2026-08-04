"""Repositories for BATCH-006 product diff.

``list_eligible_staging`` / ``resolve_item`` use ``DbReader`` when injected (Wave B).
Without a reader, in-memory ``seed_*`` remains for scaffold / UT.

Production write path keeps:
- product_diff_result UNIQUE upsert on (batch_run_id, external_item_code)
- optional staging_item.diff_status sync (scaffold probe; full SQL later)
- NO writes to item / item_image / item.active_status
- NO normalized_hash recalculation
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.product_diff.models import DiffJudgment, ItemSeed, StagingItemSeed
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"
_STAGING_COLUMNS = (
    "staging_item_id",
    "source",
    "external_item_code",
    "normalized_hash",
    "item_name",
    "item_url",
    "price",
    "availability",
    "diff_status",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "normalized_hash",
    "item_name",
    "active_status",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class ProductDiffRepositories:
    """Facade: Staging selection / Item resolve / Diff upsert / Staging sync / logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_staging: list[StagingItemSeed] = field(default_factory=list)
    seed_items: list[ItemSeed] = field(default_factory=list)
    staging_items: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    product_diff_results: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    # boundary probes — must stay empty under correct job behavior
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_image_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    hash_recalculate_calls: list[str] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind shared pipeline ``batch_run_id`` for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def __post_init__(self) -> None:
        for seed in self.seed_staging:
            if seed.staging_item_id not in self.staging_items:
                self.staging_items[seed.staging_item_id] = {
                    "staging_item_id": seed.staging_item_id,
                    "source": seed.source,
                    "external_item_code": seed.external_item_code,
                    "normalized_hash": seed.normalized_hash,
                    "item_name": seed.item_name,
                    "item_url": seed.item_url,
                    "price": seed.price,
                    "availability": seed.availability,
                    "diff_status": seed.diff_status,
                    "validation_failed": seed.validation_failed,
                    "fetch_unavailable": seed.fetch_unavailable,
                }
        for seed in self.seed_items:
            key = (seed.source, seed.external_item_code)
            if key not in self.items:
                self.items[key] = {
                    "item_id": seed.item_id or f"it_{uuid.uuid4().hex[:12]}",
                    "source": seed.source,
                    "external_item_code": seed.external_item_code,
                    "normalized_hash": seed.normalized_hash,
                    "item_name": seed.item_name,
                    "active_status": seed.active_status,
                }

    def list_eligible_staging(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        staging_item_ids: tuple[str, ...] | None = None,
        external_item_codes: tuple[str, ...] | None = None,
        force: bool = False,
    ) -> list[StagingItemSeed]:
        """§18.1 No.8: normalized_hash NOT NULL, diff_status IS NULL (unless force)."""

        if self.db_reader is not None:
            return self._list_eligible_staging_from_db(
                max_items=max_items,
                source=source,
                staging_item_ids=staging_item_ids,
                external_item_codes=external_item_codes,
                force=force,
            )

        if staging_item_ids:
            selected: list[StagingItemSeed] = []
            for sid in staging_item_ids:
                row = self.staging_items.get(sid)
                if row is None:
                    continue
                seed = self._row_to_staging(row)
                if not self._staging_passes_filters(seed, force=force):
                    continue
                selected.append(seed)
                if len(selected) >= max_items:
                    break
            return selected

        if external_item_codes:
            code_set = set(external_item_codes)
            selected = []
            for row in self.staging_items.values():
                seed = self._row_to_staging(row)
                if seed.external_item_code not in code_set:
                    continue
                if seed.source != source:
                    continue
                if not self._staging_passes_filters(seed, force=force):
                    continue
                selected.append(seed)
                if len(selected) >= max_items:
                    break
            return selected

        eligible: list[StagingItemSeed] = []
        for row in self.staging_items.values():
            seed = self._row_to_staging(row)
            if seed.source != source:
                continue
            if not self._staging_passes_filters(seed, force=force):
                continue
            eligible.append(seed)

        eligible.sort(key=lambda s: s.staging_item_id)
        return eligible[: max(0, max_items)]

    def _list_eligible_staging_from_db(
        self,
        *,
        max_items: int,
        source: str,
        staging_item_ids: tuple[str, ...] | None,
        external_item_codes: tuple[str, ...] | None,
        force: bool,
    ) -> list[StagingItemSeed]:
        """SELECT via DbReader (equals-only; NULL filters applied in-process)."""

        reader = self.db_reader
        if reader is None:
            return []

        if staging_item_ids:
            selected: list[StagingItemSeed] = []
            for sid in staging_item_ids:
                result = reader.fetch_rows(
                    "staging_item",
                    columns=_STAGING_COLUMNS,
                    equals=(("staging_item_id", sid),),
                    limit=1,
                )
                if not result.rows:
                    continue
                seed = self._cache_staging_row(result.rows[0])
                if not self._staging_passes_filters(seed, force=force):
                    continue
                selected.append(seed)
                if len(selected) >= max_items:
                    break
            return selected

        if external_item_codes:
            selected = []
            for code in external_item_codes:
                if not code:
                    continue
                result = reader.fetch_rows(
                    "staging_item",
                    columns=_STAGING_COLUMNS,
                    equals=(("source", source), ("external_item_code", code)),
                    limit=1,
                )
                if not result.rows:
                    continue
                seed = self._cache_staging_row(result.rows[0])
                if not self._staging_passes_filters(seed, force=force):
                    continue
                selected.append(seed)
                if len(selected) >= max_items:
                    break
            return selected

        fetch_cap = max(0, max_items)
        if fetch_cap == 0:
            return []
        # Over-fetch then filter NULL semantics in-process (DbReader has no IS NULL).
        fetch_limit = min(max(fetch_cap * 5, fetch_cap), 5000)
        result = reader.fetch_rows(
            "staging_item",
            columns=_STAGING_COLUMNS,
            equals=(("source", source),),
            order_by=("staging_item_id",),
            limit=fetch_limit,
        )
        eligible: list[StagingItemSeed] = []
        for row in result.rows:
            seed = self._cache_staging_row(row)
            if not self._staging_passes_filters(seed, force=force):
                continue
            eligible.append(seed)
        eligible.sort(key=lambda s: s.staging_item_id)
        return eligible[:fetch_cap]

    @staticmethod
    def _staging_passes_filters(seed: StagingItemSeed, *, force: bool) -> bool:
        if seed.normalized_hash is None:
            return False
        if not force and seed.diff_status is not None:
            return False
        return True

    def _cache_staging_row(self, row: dict[str, object]) -> StagingItemSeed:
        seed = self._row_to_staging(row)
        self.staging_items[seed.staging_item_id] = {
            "staging_item_id": seed.staging_item_id,
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "normalized_hash": seed.normalized_hash,
            "item_name": seed.item_name,
            "item_url": seed.item_url,
            "price": seed.price,
            "availability": seed.availability,
            "diff_status": seed.diff_status,
            "validation_failed": seed.validation_failed,
            "fetch_unavailable": seed.fetch_unavailable,
        }
        return seed

    def load_staging(self, *, staging_item_id: str) -> StagingItemSeed:
        row = self.staging_items.get(staging_item_id)
        if row is None and self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "staging_item",
                columns=_STAGING_COLUMNS,
                equals=(("staging_item_id", staging_item_id),),
                limit=1,
            )
            if result.rows:
                return self._cache_staging_row(result.rows[0])
        if row is None:
            raise KeyError(f"staging_item not found: {staging_item_id}")
        return self._row_to_staging(row)

    def resolve_item(self, *, source: str, external_item_code: str) -> ItemSeed | None:
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

        row = self.items.get((source, external_item_code))
        if row is None:
            return None
        return ItemSeed(
            source=str(row["source"]),
            external_item_code=str(row["external_item_code"]),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_id=str(row["item_id"]) if row.get("item_id") else None,
            item_name=str(row["item_name"]) if row.get("item_name") else None,
            active_status=str(row["active_status"]) if row.get("active_status") else None,
        )

    def _cache_item_row(self, row: dict[str, object]) -> ItemSeed:
        seed = ItemSeed(
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row["external_item_code"]),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_id=str(row["item_id"]) if row.get("item_id") is not None else None,
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            active_status=str(row["active_status"]) if row.get("active_status") is not None else None,
        )
        self.items[(seed.source, seed.external_item_code)] = {
            "item_id": seed.item_id or f"it_{uuid.uuid4().hex[:12]}",
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "normalized_hash": seed.normalized_hash,
            "item_name": seed.item_name,
            "active_status": seed.active_status,
        }
        return seed

    def upsert_product_diff(
        self,
        *,
        batch_run_id: str,
        judgment: DiffJudgment,
    ) -> dict[str, object]:
        """UNIQUE (batch_run_id, external_item_code) ON CONFLICT DO UPDATE."""

        key = (batch_run_id, judgment.external_item_code)
        existing = self.product_diff_results.get(key)
        product_diff_result_id = (
            str(existing["product_diff_result_id"])
            if existing and existing.get("product_diff_result_id")
            else f"pdr_{uuid.uuid4().hex[:12]}"
        )
        now = datetime.now(UTC)
        record: dict[str, object] = {
            "product_diff_result_id": product_diff_result_id,
            "batch_run_id": batch_run_id,
            "staging_item_id": judgment.staging_item_id,
            "external_item_code": judgment.external_item_code,
            "old_hash": judgment.old_hash,
            "new_hash": judgment.new_hash,
            "diff_status": judgment.diff_status,
            "judged_at": judgment.judged_at,
            "updated_at": now,
        }
        # source / item_id は持たない（#526）
        self.product_diff_results[key] = record
        # PK は DB default（gen_random_uuid）に任せ、冪等キーで UPSERT する
        persist_row = {
            "batch_run_id": batch_run_id,
            "staging_item_id": judgment.staging_item_id,
            "external_item_code": judgment.external_item_code,
            "old_hash": judgment.old_hash,
            "new_hash": judgment.new_hash,
            "diff_status": judgment.diff_status,
            "judged_at": judgment.judged_at,
            "updated_at": now,
        }
        self.db_writer.upsert_rows(
            "product_diff_result",
            (persist_row,),
            conflict_columns=("batch_run_id", "external_item_code"),
            update_columns=(
                "staging_item_id",
                "old_hash",
                "new_hash",
                "diff_status",
                "judged_at",
                "updated_at",
            ),
        )
        return record

    def sync_staging_diff_status(
        self,
        *,
        staging_item_id: str,
        diff_status: str,
    ) -> None:
        """Persist optional staging_item.diff_status sync (spec §9.4 / §18.1 No.10).

        正本は product_diff_result。Staging は選定補助（diff_status IS NULL）のため、
        live postgres でも update_rows で同一値を書く（scaffold 限定だった実装を解消）。
        """

        row = self.staging_items.get(staging_item_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row["diff_status"] = diff_status
        row["updated_at"] = now
        self.db_writer.update_rows(
            "staging_item",
            set_values={"diff_status": diff_status, "updated_at": now},
            equals=(("staging_item_id", staging_item_id),),
        )

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        external_item_code: str | None = None,
        staging_item_id: str | None = None,
    ) -> None:
        detail: dict[str, object] = {}
        if external_item_code is not None:
            detail["external_item_code"] = external_item_code
        if staging_item_id is not None:
            detail["staging_item_id"] = staging_item_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"external_item_code": external_item_code, "staging_item_id": staging_item_id},
            detail=detail or None,
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        emit_phase(
            phase_logs=self.phase_logs,
            phase_log_writer=self.phase_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            phase=phase,
            status=status,
        )

    def _row_to_staging(self, row: dict[str, object]) -> StagingItemSeed:
        return StagingItemSeed(
            staging_item_id=str(row["staging_item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row["external_item_code"]),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            item_url=str(row["item_url"]) if row.get("item_url") is not None else None,
            price=int(row["price"]) if row.get("price") is not None else None,
            availability=int(row["availability"]) if row.get("availability") is not None else None,
            diff_status=str(row["diff_status"]) if row.get("diff_status") is not None else None,
            validation_failed=bool(row.get("validation_failed") or False),
            fetch_unavailable=bool(row.get("fetch_unavailable") or False),
        )
