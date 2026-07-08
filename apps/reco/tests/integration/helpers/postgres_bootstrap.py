"""Postgres bootstrap and query helpers for §14 No.10 E2E integration tests."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from reco.application.config_version_resolver.in_memory_repository import (
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_MATCHING_PARAMETER_JSON,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
)
from reco.application.recommendation_run_recorder import (
    SCAFFOLD_PAIR_KEY,
    RecommendationRunRecorder,
)
from reco.composition.builder import build_composition_ports, build_production_ports
from reco.composition.config import CompositionMode
from reco.domain import (
    ExecutionCondition,
    ExecutionMode,
    OccasionCondition,
    RecommendationRequest,
    RelationshipCondition,
)
from reco.infrastructure.db.repositories.pair_master_reader import InMemoryPairMasterReader
from reco.infrastructure.db.session import DatabaseSession

_DEFAULT_RANKING_PARAMETER_JSON = {
    "ranking_weights": {"context": 0.70, "popularity": 0.20, "risk": 0.10},
    "lambda_mmr": 0.75,
    "mmr_candidate_limit": 50,
    "top_k_default": 10,
    "diversity_method": "mmr",
}


def ensure_observability_ddl(session: DatabaseSession) -> bool:
    """Return True when observability tables required by §14 No.10 exist."""
    row = session.query_one(
        """
        SELECT
          to_regclass('public.metric_log') IS NOT NULL AS has_metric_log,
          to_regclass('public.phase_log') IS NOT NULL AS has_phase_log,
          to_regclass('public.error_log') IS NOT NULL AS has_error_log,
          to_regclass('public.recommendation_run') IS NOT NULL AS has_run
        """,
    )
    if row is None:
        return False
    return all(bool(row[key]) for key in row)


def ensure_config_version_seed_rows(session: DatabaseSession) -> None:
    """Upsert in-memory-aligned config version rows for Postgres FK checks."""
    session.execute(
        """
        INSERT INTO semantic_config (
          semantic_config_id, config_name, config_description, is_active, created_at
        ) VALUES (%s, %s, %s, true, %s)
        ON CONFLICT (config_name) DO NOTHING
        """,
        (
            DEFAULT_SEMANTIC_CONFIG_ID,
            "mvp_semantic_config",
            "integration test semantic config",
            datetime.now(UTC),
        ),
    )
    session.execute(
        """
        INSERT INTO semantic_config_version (
          semantic_config_version_id,
          semantic_config_id,
          version_label,
          is_current,
          valid_from,
          valid_to,
          created_at
        ) VALUES (%s, %s, %s, true, %s, %s, %s)
        ON CONFLICT (semantic_config_id, version_label) DO NOTHING
        """,
        (
            DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
            DEFAULT_SEMANTIC_CONFIG_ID,
            "v1.0.0",
            datetime.now(UTC),
            datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC),
            datetime.now(UTC),
        ),
    )

    for model_version_id, provider, model_name, model_type in (
        (
            DEFAULT_EMBEDDING_MODEL_VERSION_ID,
            "openai",
            "text-embedding-3-small",
            "embedding",
        ),
        (
            "b1111111-1111-4111-8111-111111111102",
            "openai",
            "gpt-4o-mini",
            "llm",
        ),
        (
            "b1111111-1111-4111-8111-111111111103",
            "internal",
            "mvp_ranking_v1",
            "ranking",
        ),
    ):
        session.execute(
            """
            INSERT INTO model_version (
              model_version_id,
              provider,
              model_name,
              model_type,
              version_label,
              is_current,
              created_at
            ) VALUES (%s, %s, %s, %s, %s, true, %s)
            ON CONFLICT (model_version_id) DO NOTHING
            """,
            (
                model_version_id,
                provider,
                model_name,
                model_type,
                "v001",
                datetime.now(UTC),
            ),
        )

    session.execute(
        """
        INSERT INTO ranking_config (
          ranking_config_id,
          config_name,
          config_version,
          parameter_json,
          is_current,
          created_at
        ) VALUES (%s, %s, %s, %s::jsonb, true, %s)
        ON CONFLICT (ranking_config_id) DO NOTHING
        """,
        (
            DEFAULT_RANKING_CONFIG_ID,
            "mvp_ranking_config",
            "v001",
            json.dumps(_DEFAULT_RANKING_PARAMETER_JSON),
            datetime.now(UTC),
        ),
    )
    session.execute(
        """
        INSERT INTO matching_config (
          matching_config_id,
          config_name,
          config_version,
          parameter_json,
          is_current,
          created_at
        ) VALUES (%s, %s, %s, %s::jsonb, true, %s)
        ON CONFLICT (matching_config_id) DO NOTHING
        """,
        (
            DEFAULT_MATCHING_CONFIG_ID,
            "mvp_matching_config",
            "v001",
            json.dumps(DEFAULT_MATCHING_PARAMETER_JSON),
            datetime.now(UTC),
        ),
    )


def resolve_postgres_pair_id(session: DatabaseSession) -> str:
    """Resolve a real pair_master UUID for scaffold friend × birthday mapping."""
    row = session.query_one(
        """
        SELECT pair_id
        FROM pair_master
        WHERE relationship_code = %s
          AND occasion_code = %s
          AND is_active = true
        LIMIT 1
        """,
        ("friend_casual", "birthday"),
    )
    if row is None:
        msg = "pair_master row for friend_casual × birthday is required for integration tests"
        raise RuntimeError(msg)
    return str(row["pair_id"])


def insert_recommendation_request(
    session: DatabaseSession,
    *,
    request_id: str,
    trace_id: str,
) -> None:
    """Insert a minimal recommendation_request row for MOD-RECO-002 FK."""
    payload = {
        "request_id": request_id,
        "relationship_code": "friend",
        "occasion_code": "birthday",
    }
    session.execute(
        """
        INSERT INTO recommendation_request (
          recommendation_request_id,
          request_mode,
          relationship_code,
          occasion_code,
          currency,
          top_k,
          request_payload,
          validated_payload,
          trace_id,
          validated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
        ON CONFLICT (recommendation_request_id) DO NOTHING
        """,
        (
            request_id,
            "ui",
            "friend",
            "birthday",
            "JPY",
            5,
            json.dumps(payload),
            json.dumps(payload),
            trace_id,
            datetime.now(UTC),
        ),
    )


def build_production_ports_for_postgres(
    session: DatabaseSession,
) -> tuple[object, dict[str, object]]:
    """Build production composition and align pair_id with Postgres FK."""
    ensure_config_version_seed_rows(session)
    pair_id = resolve_postgres_pair_id(session)
    ports, helpers = build_production_ports(database_session=session)
    run_recorder = ports.run_recorder
    if not isinstance(run_recorder, RecommendationRunRecorder):
        msg = "expected RecommendationRunRecorder from build_production_ports()"
        raise TypeError(msg)

    patched_recorder = replace(
        run_recorder,
        pair_reader=InMemoryPairMasterReader(
            pairs={SCAFFOLD_PAIR_KEY: pair_id},
        ),
    )
    ports = replace(ports, run_recorder=patched_recorder)
    return ports, helpers


def build_composition_ports_production_for_postgres(
    session: DatabaseSession,
) -> tuple[object, dict[str, object]]:
    """Exercise CompositionMode.PRODUCTION selection with Postgres session."""
    ensure_config_version_seed_rows(session)
    pair_id = resolve_postgres_pair_id(session)
    ports, helpers = build_composition_ports(
        CompositionMode.PRODUCTION,
        database_session=session,
    )
    run_recorder = ports.run_recorder
    if not isinstance(run_recorder, RecommendationRunRecorder):
        msg = "expected RecommendationRunRecorder from build_composition_ports(PRODUCTION)"
        raise TypeError(msg)

    patched_recorder = replace(
        run_recorder,
        pair_reader=InMemoryPairMasterReader(
            pairs={SCAFFOLD_PAIR_KEY: pair_id},
        ),
    )
    ports = replace(ports, run_recorder=patched_recorder)
    return ports, helpers


def sample_integration_request(*, request_id: str) -> RecommendationRequest:
    return RecommendationRequest(
        request_id=request_id,
        relationship=RelationshipCondition(relationship_code="friend"),
        occasion=OccasionCondition(occasion_code="birthday"),
        execution=ExecutionCondition(mode=ExecutionMode.UI, top_k=5),
    )


def new_request_id() -> str:
    return str(uuid4())


def fetch_recommendation_run(
    session: DatabaseSession,
    run_id: str,
) -> dict[str, object] | None:
    return session.query_one(
        """
        SELECT
          recommendation_run_id,
          recommendation_request_id,
          pair_id,
          run_status,
          started_at,
          completed_at
        FROM recommendation_run
        WHERE recommendation_run_id = %s
        """,
        (run_id,),
    )


def fetch_phase_logs_for_run(
    session: DatabaseSession,
    run_id: str,
) -> list[dict[str, object]]:
    return session.query(
        """
        SELECT
          phase_log_id,
          trace_id,
          owner_id,
          phase_name,
          phase_status,
          error_code
        FROM phase_log
        WHERE owner_type = 'recommendation_run'
          AND owner_id = %s
        ORDER BY created_at
        """,
        (run_id,),
    )


def fetch_error_logs_for_trace(
    session: DatabaseSession,
    trace_id: str,
) -> list[dict[str, object]]:
    return session.query(
        """
        SELECT
          error_log_id,
          trace_id,
          request_id,
          error_code,
          error_detail_json
        FROM error_log
        WHERE trace_id = %s
        ORDER BY occurred_at
        """,
        (trace_id,),
    )


def fetch_metric_log_for_run(
    session: DatabaseSession,
    run_id: str,
) -> dict[str, object] | None:
    return session.query_one(
        """
        SELECT
          metric_log_id,
          trace_id,
          recommendation_run_id,
          final_result_count,
          recommendation_empty,
          metric_source,
          recommendation_latency_ms
        FROM metric_log
        WHERE recommendation_run_id = %s
        """,
        (run_id,),
    )


def count_reco_score_distribution_metrics(
    session: DatabaseSession,
    run_id: str,
) -> int:
    row = session.query_one(
        """
        SELECT COUNT(*)::int AS count
        FROM reco_score_distribution_metric
        WHERE recommendation_run_id = %s
        """,
        (run_id,),
    )
    if row is None:
        return 0
    return int(row["count"])
