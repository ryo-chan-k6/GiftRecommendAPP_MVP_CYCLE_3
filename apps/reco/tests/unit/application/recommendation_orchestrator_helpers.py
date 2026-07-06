"""Orchestrator 単体テスト向け Port 差し替え・配線ヘルパー。

User Meaning / Retrieval / Matching / Ranking / Output 配線後の
``build_default_stub_ports()`` は 004〜010、012 / 013、014 / 015 / 016、
017 / 018 / 019 / 020、021 / 022 / 023 を本実装とする。
デフォルト composition 経路では User Meaning 向けに in-memory Repository を
共有接続する ``build_wired_default_composition_ports()`` を用いる。
Retrieval / Matching / Ranking / Output 本実装は ``build_default_stub_ports()``
同梱の in-memory Repository を利用する。

Orchestrator 本体の挙動のみを切り出すテストでは、当該フェーズを Stub に戻す
``ports_with_user_meaning_stubs()`` / ``ports_with_retrieval_stubs()`` /
``ports_with_matching_stubs()`` / ``ports_with_ranking_stubs()`` /
``ports_with_output_stubs()`` を利用する。
User Meaning を Stub に戻す場合は Retrieval 本実装が 010 出力を要求するため、
同時に ``ports_with_retrieval_stubs()`` も適用する。
Matching 本実装は Retrieval 出力を要求するため、Matching を Stub に戻す前段で
Retrieval も Stub 化するか、Matching 単体検証用に ``ports_with_matching_stubs()``
を併用する。
Ranking 本実装は Matching 出力を要求するため、Ranking を Stub に戻す場合は
``ports_with_ranking_stubs()`` を併用する。
Output 本実装は Ranking 出力を要求するため、上流を Stub 化したパイプライン検証では
``ports_with_output_stubs()`` を併用する。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from reco.application.recommendation_orchestrator import OrchestratorPorts, build_default_stub_ports
from reco.application.recommendation_orchestrator.stubs import (
    StubPipelineModule,
    StubReasonGenerator,
)

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_feature_generator.in_memory_repository import (
        InMemoryUserFeatureRepository,
    )

_USER_MEANING_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("user_semantic_extractor", "MOD-RECO-004", "semantic_extracted"),
    ("external_feature_estimator", "MOD-RECO-005", "external_feature_estimated"),
    ("internal_feature_estimator", "MOD-RECO-006", "internal_feature_estimated"),
    ("user_feature_generator", "MOD-RECO-007", "user_feature_generated"),
    ("user_meaning_projector", "MOD-RECO-008", "user_meaning_projected"),
    ("user_context_builder", "MOD-RECO-009", "user_context_built"),
    ("query_embedding_generator", "MOD-RECO-010", "query_embedding_generated"),
)

_USER_MEANING_MODULE_IDS: tuple[str, ...] = tuple(
    module_id for _, module_id, _ in _USER_MEANING_STUB_PORTS
)

_RETRIEVAL_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("candidate_retriever", "MOD-RECO-012", "retrieval_completed"),
    ("post_hard_filter", "MOD-RECO-013", "post_hard_filtered"),
)

_RETRIEVAL_MODULE_IDS: tuple[str, ...] = tuple(
    module_id for _, module_id, _ in _RETRIEVAL_STUB_PORTS
)

_MATCHING_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("feature_matcher", "MOD-RECO-014", "feature_matched"),
    ("meaning_match_aggregator", "MOD-RECO-015", "meaning_match_aggregated"),
    ("context_scorer", "MOD-RECO-016", "context_scored"),
)

_MATCHING_MODULE_IDS: tuple[str, ...] = tuple(
    module_id for _, module_id, _ in _MATCHING_STUB_PORTS
)

_RANKING_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("popularity_scorer", "MOD-RECO-017", "popularity_scored"),
    ("risk_scorer", "MOD-RECO-018", "risk_scored"),
    ("final_score_calculator", "MOD-RECO-019", "final_score_calculated"),
    ("final_ranker", "MOD-RECO-020", "final_ranked"),
)

_RANKING_MODULE_IDS: tuple[str, ...] = tuple(
    module_id for _, module_id, _ in _RANKING_STUB_PORTS
)

_OUTPUT_STUB_PORTS: tuple[tuple[str, str, str], ...] = (
    ("result_builder", "MOD-RECO-021", "result_built"),
    ("snapshot_builder", "MOD-RECO-022", "snapshot_built"),
)

_OUTPUT_MODULE_IDS: tuple[str, ...] = (
    "MOD-RECO-021",
    "MOD-RECO-022",
    "MOD-RECO-023",
)


def ports_with_user_meaning_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """User Meaning フェーズ Port を StubPipelineModule に差し替える。"""
    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _USER_MEANING_STUB_PORTS
        },
    )


def ports_with_retrieval_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """Retrieval フェーズ Port を StubPipelineModule に差し替える。"""
    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _RETRIEVAL_STUB_PORTS
        },
    )


def ports_with_matching_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """Matching フェーズ Port を StubPipelineModule に差し替える。"""
    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _MATCHING_STUB_PORTS
        },
    )


def ports_with_ranking_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """Ranking フェーズ Port を StubPipelineModule に差し替える。"""
    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _RANKING_STUB_PORTS
        },
    )


def ports_with_output_stubs(ports: OrchestratorPorts) -> OrchestratorPorts:
    """Output フェーズ Port を scaffold Stub に差し替える。"""
    from reco.domain import RecommendationResult, RecommendationResultItem, ResultStatus

    result_builder = StubPipelineModule(
        module_id="MOD-RECO-021",
        phase_name="result_built",
    )
    original_result_execute = result_builder.execute

    def result_execute(context: ExecutionContext) -> ExecutionContext:
        updated = original_result_execute(context)
        if updated.recommendation_result is not None:
            return updated

        run_id = updated.run_id or "run-scaffold"
        updated.recommendation_result = RecommendationResult(
            run_id=run_id,
            request_id=updated.recommendation_request.request_id,
            items=(
                RecommendationResultItem(
                    item_id="item-scaffold-1",
                    rank=1,
                    final_score=0.75,
                    reason_summary=None,
                    reason_status=None,
                    is_fallback=False,
                ),
            ),
            result_status=ResultStatus.COMPLETED,
            version_info=dict(updated.config_versions),
        )
        return updated

    result_builder.execute = result_execute  # type: ignore[method-assign]

    return replace(
        ports,
        **{
            attr: StubPipelineModule(module_id=module_id, phase_name=phase_name)
            for attr, module_id, phase_name in _OUTPUT_STUB_PORTS
            if attr != "result_builder"
        },
        result_builder=result_builder,
        reason_generator=StubReasonGenerator(),
    )


def _patch_output_stubs_for_matching_zero_short_circuit(
    ports: OrchestratorPorts,
) -> OrchestratorPorts:
    """Matching 0 件 short-circuit 後も 021 / 022 が呼ばれる経路向け scaffold Output Stub。"""
    from reco.application.final_ranker.models import RankedItems
    from reco.domain import RecommendationResult, RecommendationResultItem, ResultStatus

    snapshot_builder = ports.snapshot_builder

    def snapshot_execute(context: ExecutionContext) -> ExecutionContext:
        context.completed_modules.append(snapshot_builder.module_id)
        return context

    snapshot_builder.execute = snapshot_execute  # type: ignore[method-assign]

    result_builder = ports.result_builder

    def result_execute(context: ExecutionContext) -> ExecutionContext:
        context.completed_modules.append(result_builder.module_id)
        if context.recommendation_result is not None:
            return context

        run_id = context.run_id or "run-scaffold"
        ranked_items = context.ranked_items
        if isinstance(ranked_items, RankedItems) and ranked_items.entries:
            items = tuple(
                RecommendationResultItem(
                    item_id=entry.item_id,
                    rank=entry.rank,
                    final_score=entry.final_score,
                    reason_summary=None,
                    reason_status=None,
                    is_fallback=False,
                )
                for entry in ranked_items.entries
            )
            result_status = ResultStatus.COMPLETED
        else:
            items = (
                RecommendationResultItem(
                    item_id="item-scaffold-1",
                    rank=1,
                    final_score=0.75,
                    reason_summary=None,
                    reason_status=None,
                    is_fallback=False,
                ),
            )
            result_status = ResultStatus.COMPLETED

        context.recommendation_result = RecommendationResult(
            run_id=run_id,
            request_id=context.recommendation_request.request_id,
            items=items,
            result_status=result_status,
            version_info=dict(context.config_versions),
        )
        return context

    result_builder.execute = result_execute  # type: ignore[method-assign]
    return ports


@dataclass
class _BridgedUserFeatureReadRepository:
    """007 の INSERT 行を 008 / 009 の read Port へ橋渡しする。"""

    write_repo: InMemoryUserFeatureRepository

    def register_user_features(
        self,
        recommendation_run_id: str,
        rows: tuple[object, ...],
    ) -> None:
        del recommendation_run_id, rows

    def get_user_features_for_run(
        self,
        recommendation_run_id: str,
    ) -> tuple[object, ...]:
        from reco.application.user_meaning_projector.models import UserFeatureRow

        return tuple(
            UserFeatureRow(
                feature_code=row.feature_code,
                feature_value=row.feature_value,
                feature_normalization_version_id=row.feature_normalization_version_id,
            )
            for row in self.write_repo.inserted_rows
            if row.recommendation_run_id == recommendation_run_id
        )


def _wrap_run_recorder_for_in_memory_registration(
    run_recorder: object,
    *,
    semantic_run_validation: object,
    embedding_run_validation: object,
) -> object:
    original_record_run = run_recorder.record_run

    def record_run(context: ExecutionContext) -> ExecutionContext:
        updated = original_record_run(context)
        run_id = updated.run_id
        if run_id is None:
            return updated

        semantic_version_id = updated.config_versions.get("semantic_config_version_id")
        if semantic_version_id is not None:
            semantic_run_validation.register_run(run_id, semantic_version_id)

        embedding_version_id = updated.config_versions.get("model_versions.embedding")
        if embedding_version_id is not None:
            embedding_run_validation.register_run(run_id, embedding_version_id)

        return updated

    run_recorder.record_run = record_run  # type: ignore[method-assign]
    return run_recorder


def _wrap_user_semantic_extractor_for_user_feature_link(
    extractor: object,
    *,
    user_feature_write_repo: InMemoryUserFeatureRepository,
) -> object:
    original_execute = extractor.execute

    def execute(context: ExecutionContext) -> ExecutionContext:
        updated = original_execute(context)
        run_id = updated.run_id
        if run_id is not None:
            user_feature_write_repo.register_user_semantic(run_id)
        return updated

    extractor.execute = execute  # type: ignore[method-assign]
    return extractor


def _build_scaffold_external_feature_rules():
    """run_recorder の SCAFFOLD_PAIR_KEY（friend × birthday）と整合する feature rule。"""
    from reco.application.config_version_resolver import DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    from reco.application.external_condition_feature_estimator.in_memory_repository import (
        InMemoryFeatureRuleRepository,
        build_default_feature_rule_repository,
    )

    version_id = DEFAULT_SEMANTIC_CONFIG_VERSION_ID
    rules = build_default_feature_rule_repository()
    friend_features = rules.relationship_features.get(("friend_casual", version_id))
    if friend_features is not None:
        rules.relationship_features[("friend", version_id)] = dict(friend_features)
    lover_birthday_delta = rules.pair_deltas.get(("lover", "birthday", version_id))
    if lover_birthday_delta is not None:
        rules.pair_deltas[("friend", "birthday", version_id)] = dict(lover_birthday_delta)
    return rules


def assert_user_meaning_execution_context_populated(
    context: ExecutionContext,
) -> None:
    """Default composition 後に User Meaning フェーズの型付きフィールドが設定されていることを検証する。"""
    assert context.semantic_extraction_result is not None
    assert context.external_feature_estimate is not None
    assert context.internal_feature_estimate is not None
    assert context.user_feature is not None
    assert context.user_meaning is not None
    assert context.user_context is not None
    assert context.query_embedding is not None


def assert_retrieval_execution_context_populated(
    context: ExecutionContext,
) -> None:
    """Default composition 後に Retrieval フェーズの型付きフィールドと観測系メトリクスを検証する。"""
    pool = context.pre_filtered_item_pool
    candidate = context.retrieval_candidate
    validated = context.validated_retrieval_candidate

    assert pool is not None
    assert candidate is not None
    assert validated is not None

    pre_filter_count = context.pre_filter_candidate_count
    retrieval_count = context.retrieval_candidate_count
    post_filter_count = context.post_filter_candidate_count
    pre_filter_latency_ms = context.pre_hard_filter_latency_ms
    retrieval_latency_ms = context.retrieval_latency_ms
    post_filter_latency_ms = context.post_hard_filter_latency_ms

    assert pre_filter_count is not None
    assert retrieval_count is not None
    assert post_filter_count is not None
    assert pre_filter_latency_ms is not None
    assert retrieval_latency_ms is not None
    assert post_filter_latency_ms is not None

    assert pre_filter_count == pool.total_after_filter
    assert retrieval_count == candidate.total_retrieved
    assert retrieval_count == len(candidate.candidates)
    assert post_filter_count == validated.total_validated
    assert post_filter_count == len(validated.candidates)

    # default in-memory catalog（active 2 件）経路の期待値
    assert pre_filter_count == 2
    assert retrieval_count == 2
    assert post_filter_count == 2

    assert pre_filter_latency_ms >= 0
    assert retrieval_latency_ms >= 0
    assert post_filter_latency_ms >= 0


def assert_matching_execution_context_populated(
    context: ExecutionContext,
) -> None:
    """Default composition 後に Matching フェーズの副作用を型付きフィールドで検証する。"""
    feature_match_result = context.feature_match_result
    meaning_match_result = context.meaning_match_result
    context_score_result = context.context_score_result

    feature_matcher_candidate_count = context.feature_matcher_candidate_count
    feature_matcher_excluded_count = context.feature_matcher_excluded_count
    feature_matcher_latency_ms = context.feature_matcher_latency_ms
    meaning_match_aggregator_candidate_count = (
        context.meaning_match_aggregator_candidate_count
    )
    meaning_match_aggregator_latency_ms = context.meaning_match_aggregator_latency_ms
    context_scorer_candidate_count = context.context_scorer_candidate_count
    context_scorer_latency_ms = context.context_scorer_latency_ms

    assert feature_match_result is not None
    assert meaning_match_result is not None
    assert context_score_result is not None
    assert feature_matcher_candidate_count is not None
    assert feature_matcher_excluded_count is not None
    assert feature_matcher_latency_ms is not None
    assert meaning_match_aggregator_candidate_count is not None
    assert meaning_match_aggregator_latency_ms is not None
    assert context_scorer_candidate_count is not None
    assert context_scorer_latency_ms is not None

    assert feature_matcher_candidate_count == feature_match_result.total_matched
    assert feature_matcher_candidate_count == len(feature_match_result.entries)
    assert meaning_match_aggregator_candidate_count == meaning_match_result.total_aggregated
    assert meaning_match_aggregator_candidate_count == len(meaning_match_result.entries)
    assert context_scorer_candidate_count == context_score_result.total_scored
    assert context_scorer_candidate_count == len(context_score_result.entries)

    # default in-memory catalog（active 2 件）経路の期待値
    assert feature_matcher_candidate_count == 2
    assert meaning_match_aggregator_candidate_count == 2
    assert context_scorer_candidate_count == 2

    assert feature_matcher_latency_ms >= 0
    assert meaning_match_aggregator_latency_ms >= 0
    assert context_scorer_latency_ms >= 0


def assert_ranking_execution_context_populated(
    context: ExecutionContext,
) -> None:
    """Default composition 後に Ranking フェーズの副作用を型付きフィールドで検証する。"""
    popularity_score_result = context.popularity_score_result
    risk_penalty_result = context.risk_penalty_result
    final_score_result = context.final_score_result
    ranked_items = context.ranked_items

    popularity_scorer_candidate_count = context.popularity_scorer_candidate_count
    popularity_scorer_latency_ms = context.popularity_scorer_latency_ms
    risk_scorer_candidate_count = context.risk_scorer_candidate_count
    risk_scorer_latency_ms = context.risk_scorer_latency_ms
    final_score_calculator_candidate_count = (
        context.final_score_calculator_candidate_count
    )
    final_score_calculator_latency_ms = context.final_score_calculator_latency_ms
    final_ranker_selected_count = context.final_ranker_selected_count
    final_ranker_latency_ms = context.final_ranker_latency_ms

    assert popularity_score_result is not None
    assert risk_penalty_result is not None
    assert final_score_result is not None
    assert ranked_items is not None
    assert popularity_scorer_candidate_count is not None
    assert popularity_scorer_latency_ms is not None
    assert risk_scorer_candidate_count is not None
    assert risk_scorer_latency_ms is not None
    assert final_score_calculator_candidate_count is not None
    assert final_score_calculator_latency_ms is not None
    assert final_ranker_selected_count is not None
    assert final_ranker_latency_ms is not None

    assert popularity_scorer_candidate_count == popularity_score_result.total_scored
    assert popularity_scorer_candidate_count == len(popularity_score_result.entries)
    assert risk_scorer_candidate_count == risk_penalty_result.total_scored
    assert risk_scorer_candidate_count == len(risk_penalty_result.entries)
    assert final_score_calculator_candidate_count == final_score_result.total_scored
    assert final_score_calculator_candidate_count == len(final_score_result.entries)
    assert final_ranker_selected_count == ranked_items.total_selected
    assert final_ranker_selected_count == len(ranked_items.entries)

    # default in-memory catalog（active 2 件）経路の期待値
    assert popularity_scorer_candidate_count == 2
    assert risk_scorer_candidate_count == 2
    assert final_score_calculator_candidate_count == 2
    assert final_ranker_selected_count == 2

    assert popularity_scorer_latency_ms >= 0
    assert risk_scorer_latency_ms >= 0
    assert final_score_calculator_latency_ms >= 0
    assert final_ranker_latency_ms >= 0


def assert_output_execution_context_populated(
    context: ExecutionContext,
) -> None:
    """Default composition 後に Output フェーズの副作用を型付きフィールドで検証する。"""
    recommendation_result = context.recommendation_result
    assert recommendation_result is not None
    assert recommendation_result.item_count > 0
    assert recommendation_result.result_status is not None

    version_info = recommendation_result.version_info or {}
    assert version_info.get("recommendation_result_id")

    result_builder_item_count = context.result_builder_item_count
    result_builder_latency_ms = context.result_builder_latency_ms
    result_builder_header_persisted = context.result_builder_header_persisted
    snapshot_builder_item_count = context.snapshot_builder_item_count
    snapshot_builder_latency_ms = context.snapshot_builder_latency_ms
    snapshot_builder_items_persisted = context.snapshot_builder_items_persisted
    reason_generator_item_count = context.reason_generator_item_count
    reason_generator_success_count = context.reason_generator_success_count
    reason_generator_fallback_count = context.reason_generator_fallback_count
    reason_generator_persisted = context.reason_generator_persisted
    reason_generation_latency_ms = context.reason_generation_latency_ms

    assert result_builder_item_count is not None
    assert result_builder_latency_ms is not None
    assert result_builder_header_persisted is not None
    assert snapshot_builder_item_count is not None
    assert snapshot_builder_latency_ms is not None
    assert snapshot_builder_items_persisted is not None
    assert reason_generator_item_count is not None
    assert reason_generator_success_count is not None
    assert reason_generator_fallback_count is not None
    assert reason_generator_persisted is not None
    assert reason_generation_latency_ms is not None

    assert result_builder_header_persisted is True
    assert snapshot_builder_items_persisted is True
    assert reason_generator_persisted is True

    assert result_builder_item_count == recommendation_result.item_count
    assert snapshot_builder_item_count == recommendation_result.item_count
    assert reason_generator_item_count == recommendation_result.item_count
    assert (
        reason_generator_success_count + reason_generator_fallback_count
        == reason_generator_item_count
    )

    # default in-memory catalog（active 2 件）経路の期待値
    assert result_builder_item_count == 2
    assert snapshot_builder_item_count == 2
    assert reason_generator_item_count == 2

    assert result_builder_latency_ms >= 0
    assert snapshot_builder_latency_ms >= 0
    assert reason_generation_latency_ms >= 0

    first_item = recommendation_result.items[0]
    assert first_item.reason_summary is not None
    assert first_item.reason_status is not None


def build_wired_ports_with_zero_matching_candidates() -> tuple[
    OrchestratorPorts,
    dict[str, object],
]:
    """Matching 対象 0 件（item_feature 欠損で全候補除外）のデフォルト composition。"""
    from reco.application.feature_matcher import FeatureMatcher
    from reco.application.feature_matcher.in_memory_repository import (
        InMemoryItemFeatureRepository,
        InMemoryFeatureNormalizationRepository,
    )

    ports, helpers = build_wired_default_composition_ports()
    feature_matcher = FeatureMatcher(
        item_feature_repository=InMemoryItemFeatureRepository(),
        normalization=InMemoryFeatureNormalizationRepository(),
    )
    wired_ports = replace(ports, feature_matcher=feature_matcher)
    return _patch_output_stubs_for_matching_zero_short_circuit(wired_ports), helpers


def build_wired_default_composition_ports() -> tuple[OrchestratorPorts, dict[str, object]]:
    """User Meaning 本実装を共有 in-memory 状態で接続したデフォルト composition。"""
    from reco.application.external_condition_feature_estimator import (
        ExternalConditionFeatureEstimator,
    )
    from reco.application.internal_condition_feature_estimator import (
        InternalConditionFeatureEstimator,
        build_default_in_memory_repositories as build_internal_repos,
    )
    from reco.application.query_embedding_generator import QueryEmbeddingGenerator
    from reco.application.query_embedding_generator.in_memory_client import (
        build_default_in_memory_embedding_client,
    )
    from reco.application.query_embedding_generator.in_memory_repository import (
        InMemoryRunValidation as EmbeddingRunValidation,
    )
    from reco.application.user_context_builder import UserContextBuilder
    from reco.application.user_context_builder.in_memory_repository import (
        InMemoryLambdaContextRuleRepository,
        InMemoryUserMeaningRepository,
    )
    from reco.application.user_feature_generator import UserFeatureGenerator
    from reco.application.user_feature_generator.in_memory_repository import (
        InMemoryNormalizationRuleRepository,
        InMemoryUserFeatureRepository,
        build_default_normalization_binding,
    )
    from reco.application.user_meaning_projector import UserMeaningProjector
    from reco.application.user_meaning_projector.in_memory_repository import (
        InMemoryMeaningProjectionConfigRepository,
        build_default_projection_weights,
    )
    from reco.application.user_semantic_extractor import UserSemanticExtractor
    from reco.application.user_semantic_extractor.in_memory_repository import (
        InMemoryRunValidation as SemanticRunValidation,
        build_default_in_memory_repositories as build_semantic_repos,
    )
    from reco.infrastructure.logger.logger import ScaffoldRecoLogger

    ports, helpers = build_default_stub_ports()

    shared_semantic_run_validation = SemanticRunValidation()
    shared_embedding_run_validation = EmbeddingRunValidation()
    user_feature_write_repo = InMemoryUserFeatureRepository()
    user_feature_read_repo = _BridgedUserFeatureReadRepository(
        write_repo=user_feature_write_repo,
    )

    semantic_catalog, _, user_semantic_repo = build_semantic_repos()
    external_feature_rules = _build_scaffold_external_feature_rules()
    internal_concept_rules, _ = build_internal_repos()

    user_semantic_extractor = UserSemanticExtractor(
        catalog=semantic_catalog,
        run_validation=shared_semantic_run_validation,
        user_semantic_repository=user_semantic_repo,
        logger=ScaffoldRecoLogger(),
    )
    user_semantic_extractor = _wrap_user_semantic_extractor_for_user_feature_link(
        user_semantic_extractor,
        user_feature_write_repo=user_feature_write_repo,
    )

    external_feature_estimator = ExternalConditionFeatureEstimator(
        feature_rules=external_feature_rules,
        run_validation=shared_semantic_run_validation,
        logger=ScaffoldRecoLogger(),
    )
    internal_feature_estimator = InternalConditionFeatureEstimator(
        concept_feature_rules=internal_concept_rules,
        run_validation=shared_semantic_run_validation,
        logger=ScaffoldRecoLogger(),
    )
    user_feature_generator = UserFeatureGenerator(
        normalization_rules=InMemoryNormalizationRuleRepository(
            binding=build_default_normalization_binding(),
        ),
        user_features=user_feature_write_repo,
        run_validation=shared_semantic_run_validation,
        logger=ScaffoldRecoLogger(),
    )
    user_meaning_projector = UserMeaningProjector(
        projection_config=InMemoryMeaningProjectionConfigRepository(
            weights=build_default_projection_weights(),
        ),
        user_features=user_feature_read_repo,
        run_validation=shared_semantic_run_validation,
        logger=ScaffoldRecoLogger(),
    )
    user_context_builder = UserContextBuilder(
        lambda_ctx_rules=InMemoryLambdaContextRuleRepository(),
        user_meaning_repo=InMemoryUserMeaningRepository(),
        user_features=user_feature_read_repo,
        run_validation=shared_semantic_run_validation,
        logger=ScaffoldRecoLogger(),
    )
    query_embedding_generator = QueryEmbeddingGenerator(
        embedding_client=build_default_in_memory_embedding_client(),
        run_validation=shared_embedding_run_validation,
        logger=ScaffoldRecoLogger(),
    )

    run_recorder = _wrap_run_recorder_for_in_memory_registration(
        ports.run_recorder,
        semantic_run_validation=shared_semantic_run_validation,
        embedding_run_validation=shared_embedding_run_validation,
    )

    wired_ports = replace(
        ports,
        run_recorder=run_recorder,
        user_semantic_extractor=user_semantic_extractor,
        external_feature_estimator=external_feature_estimator,
        internal_feature_estimator=internal_feature_estimator,
        user_feature_generator=user_feature_generator,
        user_meaning_projector=user_meaning_projector,
        user_context_builder=user_context_builder,
        query_embedding_generator=query_embedding_generator,
    )
    return wired_ports, helpers


def in_memory_error_log_records(error_handler: object) -> list:
    """Return MOD-RECO-029 InMemory records wired through default error_handler."""
    from reco.application.error_log_writer.repository import InMemoryErrorLogRepository
    from reco.application.reco_error_handler import RecoErrorHandler

    if not isinstance(error_handler, RecoErrorHandler):
        msg = "expected RecoErrorHandler from build_default_stub_ports()"
        raise TypeError(msg)

    repository = getattr(error_handler.error_log_writer, "repository", None)
    if not isinstance(repository, InMemoryErrorLogRepository):
        msg = "expected InMemoryErrorLogRepository in default error_log_writer"
        raise TypeError(msg)

    return repository.records


__all__ = [
    "_MATCHING_MODULE_IDS",
    "_OUTPUT_MODULE_IDS",
    "_RANKING_MODULE_IDS",
    "_RETRIEVAL_MODULE_IDS",
    "_USER_MEANING_MODULE_IDS",
    "assert_matching_execution_context_populated",
    "assert_output_execution_context_populated",
    "assert_ranking_execution_context_populated",
    "assert_retrieval_execution_context_populated",
    "assert_user_meaning_execution_context_populated",
    "build_wired_default_composition_ports",
    "build_wired_ports_with_zero_matching_candidates",
    "in_memory_error_log_records",
    "ports_with_matching_stubs",
    "ports_with_output_stubs",
    "ports_with_ranking_stubs",
    "ports_with_retrieval_stubs",
    "ports_with_user_meaning_stubs",
]
