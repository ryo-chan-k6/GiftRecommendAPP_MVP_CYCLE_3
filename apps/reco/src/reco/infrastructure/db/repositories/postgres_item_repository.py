"""PostgreSQL ItemRepository for MOD-RECO-012 Candidate Retriever."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from reco.infrastructure.db.application_bootstrap import _load_application_module
from reco.infrastructure.db.session import DatabaseSession

_load_application_module(
    "reco.application.candidate_retriever",
    "candidate-retriever",
    "models",
)
from reco.application.candidate_retriever.models import (  # noqa: E402
    FilterPredicate,
    RetrievalCandidateItem,
)

_COUNT_ACTIVE_SQL = """
SELECT COUNT(*)::int AS cnt
FROM item
WHERE is_active = true
"""


def _vector_literal(values: tuple[float, ...]) -> str:
    return "[" + ",".join(str(float(v)) for v in values) + "]"


def _item_filter_sql(predicate: FilterPredicate) -> tuple[str, list[Any]]:
    clauses: list[str] = ["TRUE"]
    params: list[Any] = []
    if predicate.active_only:
        clauses.append("i.is_active = true")
        clauses.append("i.active_status = 'active'")

    merged = predicate.merged_filter_conditions
    if merged.budget_min is not None:
        clauses.append("i.price >= %s")
        params.append(merged.budget_min)
    if merged.budget_max is not None:
        clauses.append("i.price <= %s")
        params.append(merged.budget_max)

    for keyword in merged.ng_keywords:
        clauses.append(
            "NOT ("
            "COALESCE(i.item_name, '') ILIKE %s"
            " OR COALESCE(i.catchcopy, '') ILIKE %s"
            " OR COALESCE(i.item_caption, '') ILIKE %s"
            ")"
        )
        pattern = f"%{keyword}%"
        params.extend((pattern, pattern, pattern))

    rules = predicate.data_quality_rules
    if rules.get("require_image"):
        clauses.append(
            "EXISTS (SELECT 1 FROM item_image img WHERE img.item_id = i.item_id)"
        )
    if rules.get("require_url"):
        clauses.append("i.item_url IS NOT NULL AND i.item_url <> ''")

    return " AND ".join(clauses), params


@dataclass
class PostgresItemRepository:
    """IF-DB-RECO-004 Postgres implementation for Candidate Retriever."""

    session: DatabaseSession

    def count_active_items(self) -> int:
        row = self.session.query_one(_COUNT_ACTIVE_SQL)
        return int(row["cnt"]) if row else 0

    def count_filtered_items(self, predicate: FilterPredicate) -> int:
        where_sql, params = _item_filter_sql(predicate)
        sql = f"""
SELECT COUNT(*)::int AS cnt
FROM item AS i
WHERE {where_sql}
"""
        row = self.session.query_one(sql, tuple(params))
        return int(row["cnt"]) if row else 0

    def search_vector_candidates(
        self,
        predicate: FilterPredicate,
        *,
        query_vector: tuple[float, ...],
        model_version_id: str,
        limit: int,
    ) -> tuple[RetrievalCandidateItem, ...]:
        if limit <= 0:
            return ()
        where_sql, params = _item_filter_sql(predicate)
        vector_lit = _vector_literal(query_vector)
        sql = f"""
SELECT
  i.item_id::text AS item_id,
  (1.0 - (e.embedding_vector <=> %s::vector))::float8 AS similarity_score
FROM item AS i
JOIN item_embedding AS e
  ON e.item_id = i.item_id
WHERE {where_sql}
  AND e.model_version_id = %s
ORDER BY e.embedding_vector <=> %s::vector
LIMIT %s
"""
        bound = (vector_lit, *params, model_version_id, vector_lit, limit)
        rows = self.session.query(sql, bound)
        return tuple(
            RetrievalCandidateItem(
                item_id=str(row["item_id"]),
                similarity_score=float(row["similarity_score"]),
            )
            for row in rows
        )
