"""Repositories for BATCH-009 item generation queue registration.

``list_eligible_diffs`` / ``load_diff`` / ``load_item`` / ``find_active_queue`` use
``DbReader`` when injected (Wave C). Without a reader, in-memory seed remains for
scaffold / UT.

previous_* / config_version_only etc. are not in DDL → defaults (None/False) when
mapping DB rows.

Write path (IF-DB-BATCH-010 / #1634 Wave 1):
- ``insert_queue`` → ``write_rows``（実 INSERT。PK は UUID）
- ``touch_queue_queued_at`` → ``update_rows``（``queued_at`` のみ）
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.item_generation_queue.models import (
    ELIGIBLE_DIFF_STATUSES,
    ItemRow,
    ProductDiffRow,
    QueueRow,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"
ACTIVE_QUEUE_STATUSES = frozenset({"queued", "processing"})

_DIFF_COLUMNS = (
    "product_diff_result_id",
    "batch_run_id",
    "staging_item_id",
    "external_item_code",
    "old_hash",
    "new_hash",
    "diff_status",
    "judged_at",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "active_status",
    "is_active",
    "normalized_hash",
    "item_name",
    "item_caption",
    "catchcopy",
    "external_genre_id",
    "price",
    "item_url",
)
_QUEUE_COLUMNS = (
    "item_generation_queue_id",
    "item_id",
    "generation_type",
    "queue_status",
    "retry_count",
    "queued_at",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class ItemGenerationQueueRepositories:
    """Facade: Diff read / Item read / Queue register / logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_diffs: list[ProductDiffRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    seed_queues: list[QueueRow] = field(default_factory=list)
    product_diff_results: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    queues: list[dict[str, object]] = field(default_factory=list)
    written_queue_rows: list[dict[str, object]] = field(default_factory=list)
    item_write_count: int = 0
    product_diff_write_count: int = 0
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind ``batch_run_id`` (= job_run_id UUID) for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def __post_init__(self) -> None:
        for seed in self.seed_diffs:
            if seed.product_diff_result_id not in self.product_diff_results:
                self.product_diff_results[seed.product_diff_result_id] = self._diff_to_dict(seed)
        for seed in self.seed_items:
            key = (seed.source, seed.external_item_code)
            if key not in self.items:
                self.items[key] = self._item_to_dict(seed)
        for seed in self.seed_queues:
            self.queues.append(
                {
                    "item_generation_queue_id": seed.item_generation_queue_id,
                    "item_id": seed.item_id,
                    "generation_type": seed.generation_type,
                    "queue_status": seed.queue_status,
                    "retry_count": seed.retry_count,
                    "queued_at": seed.queued_at,
                }
            )

    def list_eligible_diffs(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        diff_batch_run_id: str | None = None,
        external_item_codes: tuple[str, ...] | None = None,
    ) -> tuple[list[ProductDiffRow], int, int]:
        """§18.1 No.5: new/updated 主処理。unavailable / unchanged は skip 集計."""

        if self.db_reader is not None:
            return self._list_eligible_diffs_from_db(
                max_items=max_items,
                source=source,
                diff_batch_run_id=diff_batch_run_id,
                external_item_codes=external_item_codes,
            )

        code_set = set(external_item_codes) if external_item_codes else None
        eligible: list[ProductDiffRow] = []
        unavailable_count = 0
        unchanged_count = 0

        rows = sorted(
            self.product_diff_results.values(),
            key=lambda r: str(r["product_diff_result_id"]),
        )
        for row in rows:
            diff = self._row_to_diff(row)
            if diff_batch_run_id and diff.batch_run_id != diff_batch_run_id:
                continue
            if code_set is not None and diff.external_item_code not in code_set:
                continue
            # Item 欠落は plan から落とさず、load_item で GRS-DB-001 失敗にする（仕様 §8.2）
            item = self.items.get((source, diff.external_item_code))
            if item is not None and str(item.get("source") or DEFAULT_SOURCE) != source:
                continue

            if diff.diff_status == "unavailable":
                unavailable_count += 1
                continue
            if diff.diff_status == "unchanged":
                unchanged_count += 1
                continue
            if diff.diff_status not in ELIGIBLE_DIFF_STATUSES:
                continue
            eligible.append(diff)

        return eligible[: max(0, max_items)], unavailable_count, unchanged_count

    def _list_eligible_diffs_from_db(
        self,
        *,
        max_items: int,
        source: str,
        diff_batch_run_id: str | None,
        external_item_codes: tuple[str, ...] | None,
    ) -> tuple[list[ProductDiffRow], int, int]:
        reader = self.db_reader
        if reader is None:
            return [], 0, 0

        candidate_rows: list[dict[str, object]] = []
        if external_item_codes:
            for code in external_item_codes:
                if not code:
                    continue
                equals: list[tuple[str, object]] = [("external_item_code", code)]
                if diff_batch_run_id:
                    equals.append(("batch_run_id", diff_batch_run_id))
                result = reader.fetch_rows(
                    "product_diff_result",
                    columns=_DIFF_COLUMNS,
                    equals=tuple(equals),
                    order_by=("product_diff_result_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        else:
            fetch_cap = max(0, max_items)
            if fetch_cap == 0 and not diff_batch_run_id:
                return [], 0, 0
            scan_target = max(fetch_cap, 1)
            fetch_limit = min(max(scan_target * 5, scan_target), 5000)
            equals_scan: tuple[tuple[str, object], ...] = ()
            if diff_batch_run_id:
                equals_scan = (("batch_run_id", diff_batch_run_id),)
            result = reader.fetch_rows(
                "product_diff_result",
                columns=_DIFF_COLUMNS,
                equals=equals_scan,
                order_by=("product_diff_result_id",),
                limit=fetch_limit,
            )
            candidate_rows.extend(result.rows)

        eligible: list[ProductDiffRow] = []
        unavailable_count = 0
        unchanged_count = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["product_diff_result_id"])):
            diff = self._cache_diff_row(row)
            if diff.product_diff_result_id in seen_ids:
                continue
            seen_ids.add(diff.product_diff_result_id)

            # Item 欠落は plan から落とさない。source 不一致のみ除外。
            item_row = self.items.get((source, diff.external_item_code))
            if item_row is None and self.db_reader is not None:
                fetched = self.db_reader.fetch_rows(
                    "item",
                    columns=_ITEM_COLUMNS,
                    equals=(
                        ("source", source),
                        ("external_item_code", diff.external_item_code),
                    ),
                    limit=1,
                )
                if fetched.rows:
                    self._cache_item_row(fetched.rows[0])
                    item_row = self.items.get((source, diff.external_item_code))
            if item_row is not None and str(item_row.get("source") or DEFAULT_SOURCE) != source:
                continue

            if diff.diff_status == "unavailable":
                unavailable_count += 1
                continue
            if diff.diff_status == "unchanged":
                unchanged_count += 1
                continue
            if diff.diff_status not in ELIGIBLE_DIFF_STATUSES:
                continue
            eligible.append(diff)

        return eligible[: max(0, max_items)], unavailable_count, unchanged_count

    def load_item(self, *, source: str, external_item_code: str) -> ItemRow:
        row = self.items.get((source, external_item_code))
        if row is None and self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item",
                columns=_ITEM_COLUMNS,
                equals=(("source", source), ("external_item_code", external_item_code)),
                limit=1,
            )
            if result.rows:
                return self._cache_item_row(result.rows[0])
        if row is None:
            raise KeyError(f"item not found: {source}/{external_item_code}")
        return self._row_to_item(row)

    def load_diff(self, *, product_diff_result_id: str) -> ProductDiffRow:
        row = self.product_diff_results.get(product_diff_result_id)
        if row is None and self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "product_diff_result",
                columns=_DIFF_COLUMNS,
                equals=(("product_diff_result_id", product_diff_result_id),),
                limit=1,
            )
            if result.rows:
                return self._cache_diff_row(result.rows[0])
        if row is None:
            raise KeyError(f"product_diff_result not found: {product_diff_result_id}")
        return self._row_to_diff(row)

    def find_active_queue(
        self,
        *,
        item_id: str,
        generation_type: str,
    ) -> dict[str, object] | None:
        if self.db_reader is not None:
            return self._find_active_queue_from_db(
                item_id=item_id, generation_type=generation_type
            )

        for row in self.queues:
            if row["item_id"] != item_id:
                continue
            if row["generation_type"] != generation_type:
                continue
            if row["queue_status"] in ACTIVE_QUEUE_STATUSES:
                return row
        return None

    def _find_active_queue_from_db(
        self,
        *,
        item_id: str,
        generation_type: str,
    ) -> dict[str, object] | None:
        reader = self.db_reader
        if reader is None:
            return None

        for status in ("queued", "processing"):
            result = reader.fetch_rows(
                "item_generation_queue",
                columns=_QUEUE_COLUMNS,
                equals=(
                    ("item_id", item_id),
                    ("generation_type", generation_type),
                    ("queue_status", status),
                ),
                order_by=("queued_at",),
                limit=1,
            )
            if result.rows:
                row = dict(result.rows[0])
                self.queues.append(row)
                return row
        return None

    def insert_queue(
        self,
        *,
        item_id: str,
        generation_type: str,
        queued_at: datetime,
    ) -> dict[str, object]:
        now = queued_at if queued_at.tzinfo else queued_at.replace(tzinfo=UTC)
        # DDL: item_generation_queue_id uuid PK DEFAULT gen_random_uuid()
        record = {
            "item_generation_queue_id": str(uuid.uuid4()),
            "item_id": item_id,
            "generation_type": generation_type,
            "queue_status": "queued",
            "retry_count": 0,
            "queued_at": now,
        }
        self.queues.append(dict(record))
        self.written_queue_rows.append(dict(record))
        self.db_writer.write_rows("item_generation_queue", (dict(record),))
        return dict(record)

    def touch_queue_queued_at(
        self,
        *,
        item_generation_queue_id: str,
        queued_at: datetime,
    ) -> dict[str, object]:
        now = queued_at if queued_at.tzinfo else queued_at.replace(tzinfo=UTC)
        for row in self.queues:
            if row["item_generation_queue_id"] != item_generation_queue_id:
                continue
            if row["queue_status"] != "queued":
                raise ValueError("active queued row expected for queued_at touch")
            row["queued_at"] = now
            write_row = {
                "item_generation_queue_id": item_generation_queue_id,
                "queued_at": now,
            }
            self.written_queue_rows.append(dict(write_row))
            self.db_writer.update_rows(
                "item_generation_queue",
                set_values={"queued_at": now},
                equals=(("item_generation_queue_id", item_generation_queue_id),),
            )
            return dict(row)
        raise KeyError(f"queue row not found: {item_generation_queue_id}")

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        external_item_code: str | None = None,
        item_id: str | None = None,
    ) -> None:
        detail: dict[str, object] = {}
        if external_item_code is not None:
            detail["external_item_code"] = external_item_code
        if item_id is not None:
            detail["item_id"] = item_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"external_item_code": external_item_code, "item_id": item_id},
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

    def _cache_diff_row(self, row: dict[str, object]) -> ProductDiffRow:
        diff = self._row_to_diff(row)
        self.product_diff_results[diff.product_diff_result_id] = self._diff_to_dict(diff)
        return diff

    def _cache_item_row(self, row: dict[str, object]) -> ItemRow:
        item = self._row_to_item(row)
        self.items[(item.source, item.external_item_code)] = self._item_to_dict(item)
        return item

    def _diff_to_dict(self, seed: ProductDiffRow) -> dict[str, object]:
        return {
            "product_diff_result_id": seed.product_diff_result_id,
            "batch_run_id": seed.batch_run_id,
            "staging_item_id": seed.staging_item_id,
            "external_item_code": seed.external_item_code,
            "diff_status": seed.diff_status,
            "old_hash": seed.old_hash,
            "new_hash": seed.new_hash,
            "previous_meaning": seed.previous_meaning,
            "previous_price": seed.previous_price,
            "previous_item_url": seed.previous_item_url,
            "previous_review_average": seed.previous_review_average,
            "previous_review_count": seed.previous_review_count,
            "previous_availability": seed.previous_availability,
            "config_version_only": seed.config_version_only,
            "feature_input_hash_only": seed.feature_input_hash_only,
            "embedding_only": seed.embedding_only,
        }

    def _item_to_dict(self, seed: ItemRow) -> dict[str, object]:
        return {
            "item_id": seed.item_id,
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "active_status": seed.active_status,
            "is_active": seed.is_active,
            "normalized_hash": seed.normalized_hash,
            "item_name": seed.item_name,
            "item_caption": seed.item_caption,
            "catchcopy": seed.catchcopy,
            "external_genre_id": seed.external_genre_id,
            "attribute_ids": seed.attribute_ids,
            "tag_ids": seed.tag_ids,
            "price": seed.price,
            "item_url": seed.item_url,
            "review_average": seed.review_average,
            "review_count": seed.review_count,
            "availability": seed.availability,
        }

    def _row_to_diff(self, row: dict[str, object]) -> ProductDiffRow:
        from batch.application.item_generation_queue.models import MeaningSnapshot

        status = str(row["diff_status"])
        pm = row.get("previous_meaning")
        parsed_previous: MeaningSnapshot | None = pm if isinstance(pm, MeaningSnapshot) else None

        return ProductDiffRow(
            product_diff_result_id=str(row["product_diff_result_id"]),
            batch_run_id=str(row["batch_run_id"]),
            staging_item_id=str(row["staging_item_id"]),
            external_item_code=str(row["external_item_code"]),
            diff_status=status,  # type: ignore[arg-type]
            old_hash=str(row["old_hash"]) if row.get("old_hash") is not None else None,
            new_hash=str(row["new_hash"]) if row.get("new_hash") is not None else None,
            # DDL に previous_* / config_version_only 等はない → 既定値
            previous_meaning=parsed_previous,
            previous_price=int(row["previous_price"]) if row.get("previous_price") is not None else None,
            previous_item_url=str(row["previous_item_url"]) if row.get("previous_item_url") is not None else None,
            previous_review_average=(
                float(row["previous_review_average"])
                if row.get("previous_review_average") is not None
                else None
            ),
            previous_review_count=(
                int(row["previous_review_count"]) if row.get("previous_review_count") is not None else None
            ),
            previous_availability=(
                int(row["previous_availability"]) if row.get("previous_availability") is not None else None
            ),
            config_version_only=bool(row.get("config_version_only") or False),
            feature_input_hash_only=bool(row.get("feature_input_hash_only") or False),
            embedding_only=bool(row.get("embedding_only") or False),
        )

    def _row_to_item(self, row: dict[str, object]) -> ItemRow:
        attr = row.get("attribute_ids") or ()
        tags = row.get("tag_ids") or ()
        return ItemRow(
            item_id=str(row["item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row["external_item_code"]),
            active_status=str(row.get("active_status") or "active"),
            is_active=bool(row.get("is_active") if row.get("is_active") is not None else True),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            item_caption=str(row["item_caption"]) if row.get("item_caption") is not None else None,
            catchcopy=str(row["catchcopy"]) if row.get("catchcopy") is not None else None,
            external_genre_id=(
                str(row["external_genre_id"]) if row.get("external_genre_id") is not None else None
            ),
            attribute_ids=tuple(str(x) for x in attr) if isinstance(attr, (list, tuple)) else (),
            tag_ids=tuple(str(x) for x in tags) if isinstance(tags, (list, tuple)) else (),
            price=int(row["price"]) if row.get("price") is not None else None,
            item_url=str(row["item_url"]) if row.get("item_url") is not None else None,
            # item テーブルに review_average / availability はない → None
            review_average=float(row["review_average"]) if row.get("review_average") is not None else None,
            review_count=int(row["review_count"]) if row.get("review_count") is not None else None,
            availability=int(row["availability"]) if row.get("availability") is not None else None,
        )


__all__ = [
    "ACTIVE_QUEUE_STATUSES",
    "DEFAULT_SOURCE",
    "ItemGenerationQueueRepositories",
]
