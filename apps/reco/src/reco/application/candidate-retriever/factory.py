"""Scaffold wiring helpers for MOD-RECO-012."""

from __future__ import annotations

from reco.infrastructure.logger.logger import ScaffoldRecoLogger

from .in_memory_repository import build_default_in_memory_item_repository
from .retriever import CandidateRetriever, build_default_candidate_retriever


def build_scaffold_candidate_retriever() -> CandidateRetriever:
    """Build Candidate Retriever backed by in-memory repository (MVP scaffold)."""
    return CandidateRetriever(
        item_repository=build_default_in_memory_item_repository(),
        logger=ScaffoldRecoLogger(),
    )


__all__ = [
    "CandidateRetriever",
    "build_default_candidate_retriever",
    "build_scaffold_candidate_retriever",
]
