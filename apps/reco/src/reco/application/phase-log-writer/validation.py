"""Phase name and input validation (MOD-RECO-028 §8.5 / §10.2)."""

from __future__ import annotations

from .constants import ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES


def is_valid_phase_name(phase_name: str) -> bool:
    normalized = phase_name.strip()
    if not normalized:
        return False
    return normalized in ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES


def normalize_phase_name(phase_name: str) -> str | None:
    normalized = phase_name.strip()
    if not normalized:
        return None
    if normalized not in ALLOWED_RECOMMENDATION_RUN_PHASE_NAMES:
        return None
    return normalized
