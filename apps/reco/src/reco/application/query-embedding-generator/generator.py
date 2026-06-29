"""MOD-RECO-010 Query Embedding Generator implementation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from time import perf_counter
from typing import TYPE_CHECKING

from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_PURPOSE,
    MODULE_ID,
    PHASE_NAME,
)
from .embedding_validation import validate_embedding_vector
from .errors import QueryEmbeddingGenerationError
from .models import PreferredEmbedding, QueryEmbedding
from .ports import EmbeddingApiClientPort, RunValidationPort

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )
    from reco.application.user_context_builder.models import UserContext


@dataclass
class QueryEmbeddingGenerator:
    """PipelineModulePort implementation for Query Embedding generation."""

    embedding_client: EmbeddingApiClientPort
    run_validation: RunValidationPort | None = None
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        query_embedding = self.generate(context)
        _attach_query_embedding(context, query_embedding)
        context.completed_modules.append(self.module_id)
        return context

    def generate(self, context: ExecutionContext) -> QueryEmbedding:
        started = perf_counter()
        run_id, embedding_query_text, model_version_id = self._validate_context(context)
        self._validate_run_model_version(run_id, model_version_id)

        metadata = {
            "run_id": run_id,
            "trace_id": context.trace_id,
            "purpose": EMBEDDING_PURPOSE,
        }

        try:
            api_result = self.embedding_client.generate(
                embedding_query_text,
                model_version_id,
                metadata,
            )
        except QueryEmbeddingGenerationError:
            raise
        except Exception as exc:  # noqa: BLE001 — API 失敗を GRS-REC-007 へ集約
            raise QueryEmbeddingGenerationError(
                f"embedding API call failed for run: {run_id}",
            ) from exc

        if api_result.model_version_id != model_version_id:
            raise QueryEmbeddingGenerationError(
                "embedding API model_version_id mismatch with config_versions",
            )

        vector = validate_embedding_vector(api_result.vector)
        if api_result.dimensions != EMBEDDING_DIMENSIONS:
            raise QueryEmbeddingGenerationError(
                f"embedding API dimensions mismatch: expected {EMBEDDING_DIMENSIONS}, "
                f"got {api_result.dimensions}",
            )

        source_text_hash = hashlib.sha256(embedding_query_text.encode()).hexdigest()
        preferred_embedding = PreferredEmbedding(
            vector=vector,
            model_version_id=model_version_id,
            dimensions=EMBEDDING_DIMENSIONS,
            source_text_hash=source_text_hash,
        )
        query_embedding = QueryEmbedding(preferred_embedding=preferred_embedding)

        duration_ms = int((perf_counter() - started) * 1_000)
        self._log_generation_summary(
            context,
            model_version_id=model_version_id,
            dimensions=EMBEDDING_DIMENSIONS,
            duration_ms=duration_ms,
            source_text_hash=source_text_hash,
        )
        return query_embedding

    def _validate_context(
        self,
        context: ExecutionContext,
    ) -> tuple[str, str, str]:
        run_id = context.run_id
        if run_id is None:
            raise QueryEmbeddingGenerationError("run_id is required on execution_context")

        user_context = getattr(context, "user_context", None)
        if user_context is None:
            raise QueryEmbeddingGenerationError("user_context is required on execution_context")

        embedding_query_text = _extract_embedding_query_text(user_context)
        if not embedding_query_text or not embedding_query_text.strip():
            raise QueryEmbeddingGenerationError(
                "embedding_query_text is required and must not be empty",
            )

        model_version_id = context.config_versions.get("model_versions.embedding")
        if not model_version_id:
            raise QueryEmbeddingGenerationError(
                "model_versions.embedding is required on execution_context.config_versions",
            )

        return run_id, embedding_query_text, model_version_id

    def _validate_run_model_version(
        self,
        run_id: str,
        model_version_id: str,
    ) -> None:
        if self.run_validation is None:
            return

        run_model_version_id = self.run_validation.get_embedding_model_version_id(run_id)
        if run_model_version_id is None:
            raise QueryEmbeddingGenerationError(f"recommendation_run not found: {run_id}")
        if run_model_version_id != model_version_id:
            raise QueryEmbeddingGenerationError(
                "model_versions.embedding mismatch between run and execution_context",
            )

    def _log_generation_summary(
        self,
        context: ExecutionContext,
        *,
        model_version_id: str,
        dimensions: int,
        duration_ms: int,
        source_text_hash: str,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "query_embedding_generation_completed",
            model_version_id=model_version_id,
            dimensions=dimensions,
            duration_ms=duration_ms,
            source_text_hash=source_text_hash,
            module_id=self.module_id,
        )


def _extract_embedding_query_text(user_context: UserContext) -> str | None:
    preferred_context = getattr(user_context, "preferred_context", None)
    if preferred_context is None:
        return None
    return getattr(preferred_context, "embedding_query_text", None)


def _attach_query_embedding(
    context: ExecutionContext,
    query_embedding: QueryEmbedding,
) -> None:
    # execution_context への型付きフィールド追加は Wiring Task で行う。
    context.query_embedding = query_embedding  # type: ignore[attr-defined]


def build_default_query_embedding_generator() -> QueryEmbeddingGenerator:
    from .in_memory_client import build_default_in_memory_embedding_client
    from .in_memory_repository import build_default_in_memory_run_validation

    return QueryEmbeddingGenerator(
        embedding_client=build_default_in_memory_embedding_client(),
        run_validation=build_default_in_memory_run_validation(),
    )
