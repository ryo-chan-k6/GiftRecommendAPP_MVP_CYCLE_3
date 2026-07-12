"""Pair master lookup for relationship × occasion resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from reco.infrastructure.db.session import DatabaseSession

_RESOLVE_PAIR_ID_SQL = """
SELECT pair_id
FROM pair_master
WHERE relationship_code = %s
  AND occasion_code = %s
  AND is_active = true
LIMIT 1
"""


class PairMasterReader(Protocol):
    """Read-only access to pair_master."""

    def resolve_pair_id(
        self,
        *,
        relationship_code: str,
        occasion_code: str,
    ) -> str | None: ...


@dataclass
class InMemoryPairMasterReader:
    """Phase4a in-memory pair_master for tests and scaffold."""

    pairs: dict[tuple[str, str], str] = field(default_factory=dict)

    def resolve_pair_id(
        self,
        *,
        relationship_code: str,
        occasion_code: str,
    ) -> str | None:
        return self.pairs.get((relationship_code, occasion_code))


@dataclass
class PostgresPairMasterReader:
    """PostgreSQL pair_master lookup（is_active=true のみ）。"""

    session: DatabaseSession

    def resolve_pair_id(
        self,
        *,
        relationship_code: str,
        occasion_code: str,
    ) -> str | None:
        row = self.session.query_one(
            _RESOLVE_PAIR_ID_SQL,
            (relationship_code, occasion_code),
        )
        if row is None:
            return None
        return str(row["pair_id"])
