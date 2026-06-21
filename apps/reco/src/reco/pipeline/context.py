"""Pipeline execution context passed between recommendation phases."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineContext:
    """Mutable state container for a single recommendation run."""

    recommendation_request_id: str | None = None
    recommendation_run_id: str | None = None
    completed_phases: list[str] = field(default_factory=list)
    parsed_input: dict[str, object] | None = None
    user_feature: dict[str, float] | None = None
    retrieval_candidates: list[str] | None = None
    matching_results: list[dict[str, object]] | None = None
    ranking_results: list[dict[str, object]] | None = None
    reasons: list[str] | None = None
