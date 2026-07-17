"""In-memory repositories for BATCH-009 unit tests / scaffold wiring.

Production will replace these with real DB adapters while keeping:
- product_diff_result READ ONLY
- item READ ONLY (no active_status / business column updates)
- item_generation_queue INSERT / active queued queued_at UPDATE only
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
from batch.infrastructure.db import DbWriter

DEFAULT_SOURCE = "rakuten"
ACTIVE_QUEUE_STATUSES = frozenset({"queued", "processing"})


@dataclass
class ItemGenerationQueueRepositories:
    """Facade: Diff read / Item read / Queue register / logs."""

    db_writer: DbWriter
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
            item = self.items.get((source, diff.external_item_code))
            if item is None:
                continue
            if str(item.get("source") or DEFAULT_SOURCE) != source:
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
        if row is None:
            raise KeyError(f"item not found: {source}/{external_item_code}")
        return self._row_to_item(row)

    def load_diff(self, *, product_diff_result_id: str) -> ProductDiffRow:
        row = self.product_diff_results.get(product_diff_result_id)
        if row is None:
            raise KeyError(f"product_diff_result not found: {product_diff_result_id}")
        return self._row_to_diff(row)

    def find_active_queue(
        self,
        *,
        item_id: str,
        generation_type: str,
    ) -> dict[str, object] | None:
        for row in self.queues:
            if row["item_id"] != item_id:
                continue
            if row["generation_type"] != generation_type:
                continue
            if row["queue_status"] in ACTIVE_QUEUE_STATUSES:
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
        record = {
            "item_generation_queue_id": f"igq_{uuid.uuid4().hex[:12]}",
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
                "op": "touch_queued_at",
            }
            self.written_queue_rows.append(dict(write_row))
            self.db_writer.write_rows("item_generation_queue", (dict(write_row),))
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
        self.error_logs.append(
            {
                "code": code,
                "summary": summary,
                "external_item_code": external_item_code,
                "item_id": item_id,
            }
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})

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
            review_average=float(row["review_average"]) if row.get("review_average") is not None else None,
            review_count=int(row["review_count"]) if row.get("review_count") is not None else None,
            availability=int(row["availability"]) if row.get("availability") is not None else None,
        )


__all__ = [
    "ACTIVE_QUEUE_STATUSES",
    "DEFAULT_SOURCE",
    "ItemGenerationQueueRepositories",
]
