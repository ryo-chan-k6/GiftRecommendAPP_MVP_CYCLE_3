"""Pair master lookup for relationship × occasion resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


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
