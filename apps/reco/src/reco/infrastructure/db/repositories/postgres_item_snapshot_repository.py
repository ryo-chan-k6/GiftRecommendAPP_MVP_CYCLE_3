"""PostgreSQL ItemSnapshotReadPort for MOD-RECO-022."""

from __future__ import annotations

from dataclasses import dataclass

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.result_snapshot_builder",
    "result-snapshot-builder",
    "models",
)
from reco.application.result_snapshot_builder.models import (  # noqa: E402
    ItemPrimaryImageRecord,
    ItemReviewSnapshotRecord,
    ItemSourceRecord,
)


def _in_clause(ids: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    return ", ".join(["%s"] * len(ids)), ids


@dataclass
class PostgresItemSnapshotReadRepository:
    """Item / image / review snapshot source from Postgres."""

    session: DatabaseSession

    def fetch_items(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSourceRecord]:
        if not item_ids:
            return {}
        placeholders, params = _in_clause(item_ids)
        sql = f"""
SELECT
  item_id::text AS item_id,
  item_name,
  price,
  item_url,
  catchcopy,
  shop_code
FROM item
WHERE item_id IN ({placeholders})
"""
        rows = self.session.query(sql, params)
        return {
            str(row["item_id"]): ItemSourceRecord(
                item_id=str(row["item_id"]),
                item_name=row["item_name"],
                price=int(row["price"]) if row["price"] is not None else None,
                item_url=row["item_url"],
                catchcopy=row["catchcopy"],
                shop_code=row["shop_code"],
            )
            for row in rows
        }

    def fetch_primary_images(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemPrimaryImageRecord]:
        if not item_ids:
            return {}
        placeholders, params = _in_clause(item_ids)
        sql = f"""
SELECT DISTINCT ON (item_id)
  item_id::text AS item_id,
  image_url
FROM item_image
WHERE item_id IN ({placeholders})
  AND is_primary = true
ORDER BY item_id, display_order ASC
"""
        rows = self.session.query(sql, params)
        return {
            str(row["item_id"]): ItemPrimaryImageRecord(
                item_id=str(row["item_id"]),
                image_url=str(row["image_url"]),
            )
            for row in rows
        }

    def fetch_review_snapshots(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemReviewSnapshotRecord]:
        if not item_ids:
            return {}
        placeholders, params = _in_clause(item_ids)
        sql = f"""
SELECT
  item_id::text AS item_id,
  review_average,
  review_count
FROM item_review_summary
WHERE item_id IN ({placeholders})
"""
        rows = self.session.query(sql, params)
        return {
            str(row["item_id"]): ItemReviewSnapshotRecord(
                item_id=str(row["item_id"]),
                review_average=(
                    float(row["review_average"])
                    if row["review_average"] is not None
                    else None
                ),
                review_count=(
                    int(row["review_count"])
                    if row["review_count"] is not None
                    else None
                ),
            )
            for row in rows
        }
