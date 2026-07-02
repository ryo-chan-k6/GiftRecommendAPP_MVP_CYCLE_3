"""Test bootstrap and shared fixtures for MOD-RECO-014 unit tests."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from reco.application.config_version_resolver import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
)
from reco.application.recommendation_orchestrator.execution_context import (
    ExecutionContext,
)
from reco.domain import (
    BudgetCondition,
    ExecutionCondition,
    ExecutionMode,
    NgCondition,
    OccasionCondition,
    PreferredCondition,
    RecommendationRequest,
    RecommendationRun,
    RelationshipCondition,
    RunStatus,
)
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import ScaffoldRecoLogger


def _load_package(import_root: str, relative_path: str) -> None:
    init_path = Path(__file__).resolve().parents[4] / relative_path / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_package(
    "reco.application.internal_condition_feature_estimator",
    "src/reco/application/internal-condition-feature-estimator",
)
_load_package(
    "reco.application.post_hard_filter_executor",
    "src/reco/application/post-hard-filter-executor",
)
_load_package(
    "reco.application.user_feature_generator",
    "src/reco/application/user-feature-generator",
)
_load_package(
    "reco.application.feature_matcher",
    "src/reco/application/feature-matcher",
)

from reco.application.feature_matcher import (  # noqa: E402
    FeatureMatcher,
    InMemoryFeatureNormalizationRepository,
    InMemoryItemFeatureRecord,
    InMemoryItemFeatureRepository,
    build_uniform_item_features,
)
from reco.application.internal_condition_feature_estimator.models import (  # noqa: E402
    InternalFeatureEstimate,
)
from reco.application.post_hard_filter_executor.models import (  # noqa: E402
    ValidatedRetrievalCandidate,
    ValidatedRetrievalCandidateItem,
)
from reco.application.user_feature_generator.constants import (  # noqa: E402
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
)
from reco.application.user_feature_generator.models import UserFeature  # noqa: E402

DEFAULT_RUN_ID = "run-feature-matcher-1"


def _uniform_user_features(value: float = 0.8) -> dict[str, float]:
    return {axis: value for axis in MVP_FEATURE_CODES}


def _sample_user_feature(
    *,
    features: dict[str, float] | None = None,
) -> UserFeature:
    return UserFeature(
        recommendation_run_id=DEFAULT_RUN_ID,
        features=features or _uniform_user_features(),
        user_feature_raw=_uniform_user_features(),
        feature_normalization_version_id=DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        generated_at=datetime.now(UTC),
    )


def _sample_internal_estimate(
    *,
    avoid_delta: dict[str, float] | None = None,
) -> InternalFeatureEstimate:
    zero = {axis: 0.0 for axis in MVP_FEATURE_CODES}
    return InternalFeatureEstimate(
        preferred_delta=dict(zero),
        avoid_delta=avoid_delta or dict(zero),
        free_text_delta=dict(zero),
        internal_feature_delta=dict(zero),
        applied_concept_count=0,
        semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
        estimation_method="rule",
    )


def _sample_context(
    *,
    run_id: str = DEFAULT_RUN_ID,
    validated_candidate: ValidatedRetrievalCandidate | None = None,
    user_feature: UserFeature | None = None,
    internal_estimate: InternalFeatureEstimate | None = None,
    trace_id: str = "trace-feature-matcher",
) -> ExecutionContext:
    request = RecommendationRequest(
        request_id="req-feature-matcher-1",
        relationship=RelationshipCondition(
            relationship_code="lover",
            relationship_label="恋人",
        ),
        occasion=OccasionCondition(
            occasion_code="birthday",
            occasion_label="誕生日",
        ),
        preferred_condition=PreferredCondition(preferred_text="実用的なギフト"),
        budget=BudgetCondition(budget_min=3000, budget_max=10000),
        ng_condition=NgCondition(ng_keywords=("カジュアル",), ng_categories=()),
        execution=ExecutionCondition(mode=ExecutionMode.UI, candidate_limit=10),
    )
    context = ExecutionContext(
        recommendation_request=request,
        trace_id=trace_id,
        execution_mode=ExecutionMode.UI,
        config_versions={
            "semantic_config_version_id": DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            "model_versions.embedding": DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        },
        recommendation_run=RecommendationRun(
            run_id=run_id,
            request_id=request.request_id,
            status=RunStatus.RUNNING,
            semantic_config_version=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            model_version=DEFAULT_EMBEDDING_MODEL_VERSION_ID,
        ),
        user_feature=user_feature or _sample_user_feature(),
        internal_feature_estimate=internal_estimate or _sample_internal_estimate(),
    )
    context.validated_retrieval_candidate = validated_candidate or ValidatedRetrievalCandidate(  # type: ignore[attr-defined]
        candidates=(
            ValidatedRetrievalCandidateItem(item_id="item-001", similarity_score=0.95),
            ValidatedRetrievalCandidateItem(item_id="item-002", similarity_score=0.80),
        ),
        total_validated=2,
        total_excluded=0,
    )
    return context


def build_matcher_with_repository(
    context: ExecutionContext,
    *,
    item_repository: InMemoryItemFeatureRepository | None = None,
    normalization: InMemoryFeatureNormalizationRepository | None = None,
) -> tuple[FeatureMatcher, InMemoryItemFeatureRepository]:
    repo = item_repository or InMemoryItemFeatureRepository(
        records={
            "item-001": InMemoryItemFeatureRecord(
                item_id="item-001",
                semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                features={
                    "formality": 0.65,
                    "safety": 0.7,
                    "brand_appropriateness": 0.6,
                    "emotion": 0.55,
                    "novelty": 0.5,
                    "intimacy": 0.45,
                    "symbolic_identity": 0.5,
                    "story_richness": 0.4,
                },
            ),
            "item-002": InMemoryItemFeatureRecord(
                item_id="item-002",
                semantic_config_version_id=DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
                features=build_uniform_item_features(0.2),
            ),
        },
    )
    matcher = FeatureMatcher(
        item_feature_repository=repo,
        normalization=normalization or InMemoryFeatureNormalizationRepository(),
        logger=ScaffoldRecoLogger(),
    )
    return matcher, repo
