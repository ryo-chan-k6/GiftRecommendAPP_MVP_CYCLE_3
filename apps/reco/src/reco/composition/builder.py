"""Composition root builders for MOD-RECO-001 Orchestrator ports."""

from __future__ import annotations

from dataclasses import replace

from reco.application.config_version_resolver import (
    ConfigVersionResolver,
    build_production_config_repository,
)
from reco.application.recommendation_orchestrator import (
    OrchestratorPorts,
    build_default_stub_ports,
)
from reco.infrastructure.db.repositories.postgres_aware_user_feature_repository import (
    PostgresAwareUserFeatureRepository,
)
from reco.infrastructure.db.repositories.postgres_normalization_rule_repository import (
    PostgresNormalizationRuleRepository,
)
from reco.infrastructure.db.repositories.postgres_run_validation import (
    PostgresRunValidation,
)
from reco.infrastructure.db.repositories.postgres_user_semantic_repository import (
    PostgresUserSemanticRepository,
)
from reco.infrastructure.db.session import DatabaseSession, create_database_session

from .config import CompositionMode, resolve_database_url
from .observability import ObservabilityRepositories, build_production_observability_modules


def _inject_run_validation(
    ports: OrchestratorPorts,
    run_validation: PostgresRunValidation,
) -> OrchestratorPorts:
    """Replace InMemory RunValidation on early pipeline modules."""

    return replace(
        ports,
        user_semantic_extractor=replace(
            ports.user_semantic_extractor,
            run_validation=run_validation,
        ),
        external_feature_estimator=replace(
            ports.external_feature_estimator,
            run_validation=run_validation,
        ),
        internal_feature_estimator=replace(
            ports.internal_feature_estimator,
            run_validation=run_validation,
        ),
        user_feature_generator=replace(
            ports.user_feature_generator,
            run_validation=run_validation,
        ),
        user_meaning_projector=replace(
            ports.user_meaning_projector,
            run_validation=run_validation,
        ),
        user_context_builder=replace(
            ports.user_context_builder,
            run_validation=run_validation,
        ),
        query_embedding_generator=replace(
            ports.query_embedding_generator,
            run_validation=run_validation,
        ),
    )


def _inject_user_semantic_ports(
    ports: OrchestratorPorts,
    *,
    user_semantic_repository: PostgresUserSemanticRepository,
    user_feature_repository: PostgresAwareUserFeatureRepository,
    normalization_rules: PostgresNormalizationRuleRepository,
) -> OrchestratorPorts:
    """Wire Postgres user_semantic / user_feature / normalization binding."""

    return replace(
        ports,
        user_semantic_extractor=replace(
            ports.user_semantic_extractor,
            user_semantic_repository=user_semantic_repository,
        ),
        user_feature_generator=replace(
            ports.user_feature_generator,
            user_features=user_feature_repository,
            normalization_rules=normalization_rules,
        ),
        user_meaning_projector=replace(
            ports.user_meaning_projector,
            user_features=user_feature_repository,
        ),
        user_context_builder=replace(
            ports.user_context_builder,
            user_features=user_feature_repository,
        ),
    )


def build_production_ports(
    *,
    database_url: str | None = None,
    database_session: DatabaseSession | None = None,
) -> tuple[OrchestratorPorts, dict[str, object]]:
    """Build production composition with Postgres observability and config versions."""

    base_ports, base_helpers = build_default_stub_ports()
    session = database_session or create_database_session(
        resolve_database_url(database_url),
    )
    observability = build_production_observability_modules(session)
    config_resolver = ConfigVersionResolver(
        repository=build_production_config_repository(session),
    )
    repositories = observability["observability_repositories"]
    assert isinstance(repositories, ObservabilityRepositories)
    run_validation = PostgresRunValidation(run_repository=repositories.run_repository)
    user_semantic_repository = PostgresUserSemanticRepository(session=session)
    user_feature_repository = PostgresAwareUserFeatureRepository(session=session)
    normalization_rules = PostgresNormalizationRuleRepository(session=session)

    ports = replace(
        _inject_user_semantic_ports(
            _inject_run_validation(base_ports, run_validation),
            user_semantic_repository=user_semantic_repository,
            user_feature_repository=user_feature_repository,
            normalization_rules=normalization_rules,
        ),
        config_resolver=config_resolver,  # type: ignore[arg-type]
        run_recorder=observability["run_recorder"],  # type: ignore[arg-type]
        phase_log_writer=observability["phase_log_writer"],  # type: ignore[arg-type]
        error_handler=observability["error_handler"],  # type: ignore[arg-type]
        metric_logger=observability["metric_logger"],  # type: ignore[arg-type]
    )
    helpers = {
        **base_helpers,
        **observability,
        "config_repository": config_resolver.repository,
        "run_validation": run_validation,
        "user_semantic_repository": user_semantic_repository,
        "user_feature_repository": user_feature_repository,
        "normalization_rule_repository": normalization_rules,
    }
    return ports, helpers


def build_composition_ports(
    mode: CompositionMode = CompositionMode.DEFAULT,
    *,
    database_url: str | None = None,
    database_session: DatabaseSession | None = None,
) -> tuple[OrchestratorPorts, dict[str, object]]:
    """Select MVP default or production composition at the composition boundary."""

    if mode is CompositionMode.DEFAULT:
        return build_default_stub_ports()
    return build_production_ports(
        database_url=database_url,
        database_session=database_session,
    )
