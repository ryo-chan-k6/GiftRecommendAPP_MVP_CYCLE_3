"""PostgreSQL ItemRepository for MOD-RECO-013 Post Hard Filter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.post_hard_filter_executor",
    "post-hard-filter-executor",
    "models",
)
from reco.application.post_hard_filter_executor.models import (  # noqa: E402
    ItemSemanticConcept,
    ItemSemanticRecord,
    ItemValidationRecord,
)

_FETCH_ITEMS_SQL_PREFIX = """
SELECT
  i.item_id::text AS item_id,
  i.item_name AS name,
  i.price,
  i.is_active,
  i.active_status,
  EXISTS (
    SELECT 1 FROM item_image img WHERE img.item_id = i.item_id
  ) AS has_image
FROM item AS i
WHERE i.item_id IN (
"""

_FETCH_SEMANTICS_SQL_PREFIX = """
SELECT
  item_id::text AS item_id,
  semantic_config_version_id::text AS semantic_config_version_id,
  semantic_json
FROM item_semantic
WHERE item_id IN (
"""


def _in_clause(ids: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
    placeholders = ", ".join(["%s"] * len(ids))
    return placeholders, ids


def _parse_concepts(semantic_json: Any) -> tuple[ItemSemanticConcept, ...]:
    if not isinstance(semantic_json, dict):
        return ()
    raw = semantic_json.get("concepts")
    if not isinstance(raw, list):
        return ()
    concepts: list[ItemSemanticConcept] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        code = entry.get("concept_code")
        confidence = entry.get("confidence")
        if not isinstance(code, str) or confidence is None:
            continue
        concepts.append(
            ItemSemanticConcept(concept_code=code, confidence=float(confidence)),
        )
    return tuple(concepts)


@dataclass
class PostgresPostFilterItemRepository:
    """IF-DB-RECO-004 Postgres implementation for Post Hard Filter."""

    session: DatabaseSession

    def fetch_items_for_validation(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemValidationRecord]:
        if not item_ids:
            return {}
        placeholders, params = _in_clause(item_ids)
        sql = _FETCH_ITEMS_SQL_PREFIX + placeholders + ")"
        rows = self.session.query(sql, params)
        result: dict[str, ItemValidationRecord] = {}
        for row in rows:
            item_id = str(row["item_id"])
            result[item_id] = ItemValidationRecord(
                item_id=item_id,
                name=row["name"],
                price=int(row["price"]) if row["price"] is not None else None,
                is_active=bool(row["is_active"]),
                active_status=str(row["active_status"]),
                has_image=bool(row["has_image"]),
            )
        return result

    def fetch_item_semantics(
        self,
        item_ids: tuple[str, ...],
    ) -> dict[str, ItemSemanticRecord]:
        if not item_ids:
            return {}
        placeholders, params = _in_clause(item_ids)
        sql = _FETCH_SEMANTICS_SQL_PREFIX + placeholders + ")"
        rows = self.session.query(sql, params)
        result: dict[str, ItemSemanticRecord] = {}
        for row in rows:
            item_id = str(row["item_id"])
            result[item_id] = ItemSemanticRecord(
                item_id=item_id,
                semantic_config_version_id=str(row["semantic_config_version_id"]),
                concepts=_parse_concepts(row["semantic_json"]),
            )
        return result
