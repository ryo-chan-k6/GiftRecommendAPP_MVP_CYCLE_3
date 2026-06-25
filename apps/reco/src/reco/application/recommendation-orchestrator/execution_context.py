"""Pipeline execution context for MOD-RECO-001."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult
from reco.domain.recommendation.run import RecommendationRun


@dataclass
class ExecutionContext:
    """Mutable state passed across MOD-RECO-002〜029 during a single run."""

    recommendation_request: RecommendationRequest
    trace_id: str
    execution_mode: ExecutionMode
    caller_context: dict[str, object] | None = None

    recommendation_run: RecommendationRun | None = None
    config_versions: dict[str, str] = field(default_factory=dict)
    ranked_items: list[dict[str, object]] = field(default_factory=list)
    recommendation_result: RecommendationResult | None = None

    completed_modules: list[str] = field(default_factory=list)
    phase_log_events: list[dict[str, object]] = field(default_factory=list)
    error_log_events: list[dict[str, object]] = field(default_factory=list)
    reason_fallback_count: int = 0

    _started_at: float = field(default_factory=perf_counter, repr=False)

    @property
    def run_id(self) -> str | None:
        if self.recommendation_run is None:
            return None
        return self.recommendation_run.run_id

    @property
    def recommendation_latency_ms(self) -> int:
        elapsed = perf_counter() - self._started_at
        return int(elapsed * 1_000)
