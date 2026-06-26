"""Scaffold wiring helpers for MOD-RECO-002."""

from __future__ import annotations

from reco.infrastructure.db.repositories.pair_master_reader import (
    InMemoryPairMasterReader,
)
from reco.infrastructure.db.repositories.recommendation_run_repository import (
    InMemoryRecommendationRunRepository,
)
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .recorder import RecommendationRunRecorder

# Orchestrator unit tests and build_default_stub_ports use this pair.
SCAFFOLD_PAIR_KEY: tuple[str, str] = ("friend", "birthday")
SCAFFOLD_PAIR_ID: str = "pair-scaffold-friend-birthday"


def build_scaffold_run_recorder(
    *,
    should_fail: bool = False,
) -> RecommendationRunRecorder:
    """Build Run Recorder backed by in-memory Repository (MVP scaffold)."""
    return RecommendationRunRecorder(
        run_repository=InMemoryRecommendationRunRepository(
            should_fail_on_write=should_fail,
        ),
        pair_reader=InMemoryPairMasterReader(
            pairs={SCAFFOLD_PAIR_KEY: SCAFFOLD_PAIR_ID},
        ),
        logger=ScaffoldRecoLogger(),
    )
