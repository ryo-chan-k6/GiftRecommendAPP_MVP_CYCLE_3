"""Pipeline execution context for MOD-RECO-001."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.domain.recommendation.inputs import ExecutionMode
from reco.domain.recommendation.request import RecommendationRequest
from reco.domain.recommendation.result import RecommendationResult
from reco.domain.recommendation.run import RecommendationRun
from reco.domain.semantic_extraction import SemanticExtractionResult

if TYPE_CHECKING:
    from reco.application.candidate_retriever.models import (
        PreFilteredItemPool,
        RetrievalCandidate,
    )
    from reco.application.external_condition_feature_estimator.models import (
        ExternalFeatureEstimate,
    )
    from reco.application.internal_condition_feature_estimator.models import (
        InternalFeatureEstimate,
    )
    from reco.application.post_hard_filter_executor.models import (
        ExcludedCandidateLog,
        ValidatedRetrievalCandidate,
    )
    from reco.application.query_embedding_generator.models import QueryEmbedding
    from reco.application.user_context_builder.models import (
        CompletedUserMeaning,
        UserContext,
    )
    from reco.application.user_feature_generator.models import UserFeature
    from reco.application.user_meaning_projector.models import UserMeaningProjection


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
    semantic_extraction_result: SemanticExtractionResult | None = None
    external_feature_estimate: ExternalFeatureEstimate | None = None

    internal_feature_estimate: InternalFeatureEstimate | None = None
    user_feature: UserFeature | None = None
    user_meaning: UserMeaningProjection | CompletedUserMeaning | None = None
    user_context: UserContext | None = None
    query_embedding: QueryEmbedding | None = None

    pre_filtered_item_pool: PreFilteredItemPool | None = None
    retrieval_candidate: RetrievalCandidate | None = None
    pre_filter_candidate_count: int | None = None
    pre_hard_filter_latency_ms: int | None = None
    retrieval_latency_ms: int | None = None
    retrieval_candidate_count: int | None = None

    validated_retrieval_candidate: ValidatedRetrievalCandidate | None = None
    excluded_candidate_log: ExcludedCandidateLog | None = None
    post_filter_candidate_count: int | None = None
    post_hard_filter_latency_ms: int | None = None

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
