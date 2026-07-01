"""Orchestrator 単体テスト向け Port 差し替え・配線ヘルパー。

User Meaning / Retrieval 配線後の ``build_default_stub_ports()`` は
004〜010 および 012 / 013 を本実装とする。
デフォルト composition 経路では User Meaning 向けに in-memory Repository を
共有接続する ``build_wired_default_composition_ports()`` を用いる。
Retrieval 本実装は ``build_default_stub_ports()`` 同梱の in-memory Repository を利用する。

Orchestrator 本体の挙動のみを切り出すテストでは、当該フェーズを Stub に戻す
``ports_with_user_meaning_stubs()`` / ``ports_with_retrieval_stubs()`` を利用する。
User Meaning を Stub に戻す場合は Retrieval 本実装が 010 出力を要求するため、
同時に ``ports_with_retrieval_stubs()`` も適用する。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from reco.application.recommendation_orchestrator import OrchestratorPorts, build_default_stub_ports
from reco.application.recommendation_orchestrator.stubs import StubPipelineModule

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


__all__ = [
    "_RETRIEVAL_MODULE_IDS",
    "_USER_MEANING_MODULE_IDS",
    "assert_user_meaning_execution_context_populated",
    "build_wired_default_composition_ports",
    "ports_with_retrieval_stubs",
    "ports_with_user_meaning_stubs",
]
