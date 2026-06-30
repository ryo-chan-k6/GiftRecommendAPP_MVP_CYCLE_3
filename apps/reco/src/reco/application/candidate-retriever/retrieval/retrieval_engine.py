"""MOD-RECO-012 retrieval sub-module implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reco.domain.recommendation.inputs import ExecutionMode

from reco.application.candidate_retriever.constants import (
    DEFAULT_CANDIDATE_LIMIT_BATCH,
    DEFAULT_CANDIDATE_LIMIT_UI,
    RETRIEVAL_METHOD_VECTOR,
)
from reco.application.candidate_retriever.errors import RetrievalError
from reco.application.candidate_retriever.models import (
    PreFilteredItemPool,
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from reco.application.candidate_retriever.ports import ItemRepositoryPort

if TYPE_CHECKING:
    from reco.application.query_embedding_generator.models import QueryEmbedding
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


def resolve_candidate_limit(context: ExecutionContext) -> int:
    """Resolve candidate_limit from request.execution (§8.3.4 / §16.1 No.11)."""
    request = context.recommendation_request
    execution = request.execution
    top_k = execution.top_k if execution is not None else None

    if execution is not None and execution.candidate_limit is not None:
        candidate_limit = execution.candidate_limit
    elif context.execution_mode == ExecutionMode.BATCH:
        candidate_limit = DEFAULT_CANDIDATE_LIMIT_BATCH
    else:
        candidate_limit = DEFAULT_CANDIDATE_LIMIT_UI

    if top_k is not None and candidate_limit < top_k:
        return max(candidate_limit, top_k)
    return candidate_limit


def run_retrieval(
    context: ExecutionContext,
    pool: PreFilteredItemPool,
    *,
    item_repository: ItemRepositoryPort,
) -> RetrievalCandidate:
    """Execute Vector Retrieval phase (§5.4 / §8.3.4)."""
    if pool.total_after_filter == 0:
        return RetrievalCandidate(candidates=(), total_retrieved=0)

    query_embedding = getattr(context, "query_embedding", None)
    if query_embedding is None:
        raise RetrievalError("query_embedding is required on execution_context")

    preferred = query_embedding.preferred_embedding
    model_version_id = context.config_versions.get("model_versions.embedding")
    if not model_version_id:
        raise RetrievalError(
            "model_versions.embedding is required on execution_context.config_versions",
        )
    if preferred.model_version_id != model_version_id:
        raise RetrievalError(
            "query_embedding model_version_id mismatch with config_versions",
        )

    predicate = pool.filter_predicate
    if predicate is None:
        raise RetrievalError("filter_predicate is required on pre_filtered_item_pool")

    limit = resolve_candidate_limit(context)

    try:
        hits = item_repository.search_vector_candidates(
            predicate,
            query_vector=preferred.vector,
            model_version_id=model_version_id,
            limit=limit,
        )
    except RetrievalError:
        raise
    except Exception as exc:  # noqa: BLE001 — DB 失敗を GRS-REC-009 へ集約
        raise RetrievalError(
            f"vector retrieval failed for run: {context.run_id}",
        ) from exc

    candidates = tuple(
        RetrievalCandidateItem(
            item_id=hit.item_id,
            similarity_score=hit.similarity_score,
            retrieval_method=RETRIEVAL_METHOD_VECTOR,
        )
        for hit in hits
    )
    return RetrievalCandidate(
        candidates=candidates,
        total_retrieved=len(candidates),
    )
