"""Unit tests for BATCH-014 Embedding入力hash算出（仕様書 §16 最小）."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.embedding_input_hash import (
    BATCH_ID,
    DEFAULT_EMBEDDING_MODEL_VERSION,
    EMBEDDING_INPUT_HASH_PHASES,
    EmbeddingInputHashJob,
    EmbeddingInputHashRepositories,
    ExistingEmbedding,
    ItemRow,
    QueueRow,
    build_item_text_context,
    compute_embedding_input_hash,
)
from batch.application.embedding_input_hash.__main__ import build_scaffold_demo_job, main
from batch.application.embedding_input_hash.repositories import (
    DEFAULT_EMBEDDING_SOURCE_VERSION,
)
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 19, 12, 0, 0, tzinfo=UTC)
_SOURCE_TYPE = "item_text_context"


def _queue(
    *,
    qid: str = "igq_1",
    item_id: str = "it_1",
    generation_type: str = "embedding",
    queue_status: str = "queued",
) -> QueueRow:
    return QueueRow(
        item_generation_queue_id=qid,
        item_id=item_id,
        generation_type=generation_type,  # type: ignore[arg-type]
        queue_status=queue_status,  # type: ignore[arg-type]
        started_at=_NOW if queue_status == "processing" else None,
        queued_at=_NOW,
    )


def _item(*, item_id: str = "it_1", price: int | None = 1000, **kwargs: object) -> ItemRow:
    defaults = dict(
        item_id=item_id,
        source="rakuten",
        external_item_code=f"shop:{item_id}",
        item_name="高級ハンドクリーム",
        catchcopy="上品で落ち着いた香り",
        item_caption="ギフトに適した保湿クリーム",
        genre_id="100371",
        genre_name="美容・コスメ",
        attributes=("hand_care", "fragrance"),
        tags=("季節",),
        price=price,
        review_average=4.5,
        review_count=10,
    )
    defaults.update(kwargs)
    return ItemRow(**defaults)  # type: ignore[arg-type]


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemRow] | None = None,
    embeddings: dict[str, list[ExistingEmbedding]] | None = None,
) -> tuple[EmbeddingInputHashRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = EmbeddingInputHashRepositories(
        db_writer=db,
        seed_queues=list(queues) if queues is not None else [_queue()],
        seed_items=list(items) if items is not None else [_item()],
        seed_embeddings=dict(embeddings or {}),
    )
    return repos, db


def _context(item: ItemRow | None = None) -> dict:
    return build_item_text_context(
        item=item or _item(),
        embedding_source_type=_SOURCE_TYPE,
        embedding_source_version=DEFAULT_EMBEDDING_SOURCE_VERSION,
    )


# --- hashing -----------------------------------------------------------------


def test_hash_is_sha256_64_hex() -> None:
    digest = compute_embedding_input_hash(_context())
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_same_context_same_hash() -> None:
    assert compute_embedding_input_hash(_context()) == compute_embedding_input_hash(_context())


def test_excluded_fields_do_not_change_hash() -> None:
    base = compute_embedding_input_hash(_context(_item(price=1000, review_average=4.5)))
    changed = compute_embedding_input_hash(_context(_item(price=99999, review_average=1.0)))
    assert base == changed


def test_source_version_changes_hash() -> None:
    ctx_v1 = build_item_text_context(
        item=_item(), embedding_source_type=_SOURCE_TYPE, embedding_source_version="v1"
    )
    ctx_v2 = build_item_text_context(
        item=_item(), embedding_source_type=_SOURCE_TYPE, embedding_source_version="v2"
    )
    assert compute_embedding_input_hash(ctx_v1) != compute_embedding_input_hash(ctx_v2)


def test_context_excludes_semantic_concept() -> None:
    ctx = _context()
    assert "semantic_concepts" not in ctx
    assert ctx["embedding_source_type"] == _SOURCE_TYPE


# --- job flow ----------------------------------------------------------------


def test_primary_path_hashes_and_keeps_processing() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.hashed_count == 1
    assert result.skipped_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    assert set(EMBEDDING_INPUT_HASH_PHASES).issubset(set(result.completed_phases))


def test_handoff_recorded_without_item_embedding_write() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert len(result.handoff_records) == 1
    record = result.handoff_records[0]
    assert record["op"] == "if_db_batch_015_handoff"
    assert record["model_version_id"] == DEFAULT_EMBEDDING_MODEL_VERSION
    assert len(record["embedding_input_hash"]) == 64
    # BATCH-014 は item_embedding へ DML しない（BATCH-015 責務）
    assert repos.item_embedding_write_count == 0
    assert result.item_embedding_write_count == 0


def test_semantic_continuation_is_processed() -> None:
    repos, _db = _repos(
        queues=[_queue(qid="igq_sem", generation_type="semantic", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.hashed_count == 1
    assert repos.queues["igq_sem"]["queue_status"] == "processing"


def test_succeeded_queue_is_not_targeted() -> None:
    repos, _db = _repos(
        queues=[_queue(qid="igq_done", generation_type="embedding", queue_status="succeeded")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.hashed_count == 0
    assert result.planned_queue_count == 0


def test_queue_insert_is_never_performed() -> None:
    repos, _db = _repos()
    EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert repos.queue_insert_count == 0


# --- skip --------------------------------------------------------------------


def test_skip_when_embedding_already_generated() -> None:
    ctx = _context()
    digest = compute_embedding_input_hash(ctx)
    repos, _db = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=digest,
                )
            ]
        },
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.skipped_count == 1
    assert result.hashed_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert len(result.handoff_records) == 0


def test_no_skip_when_hash_differs() -> None:
    repos, _db = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash="0" * 64,
                )
            ]
        },
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.skipped_count == 0
    assert result.hashed_count == 1


def test_no_skip_when_model_version_differs() -> None:
    ctx = _context()
    digest = compute_embedding_input_hash(ctx)
    repos, _db = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id="other-model",
                    embedding_input_hash=digest,
                )
            ]
        },
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.skipped_count == 0
    assert result.hashed_count == 1


# --- errors ------------------------------------------------------------------


def test_forced_hash_failure_marks_failed() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos, force_hash_fail=True).run(job_run_id="r1")

    assert result.failed_count == 1
    assert "GRS-BAT-007" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_missing_item_marks_failed() -> None:
    repos, _db = _repos(queues=[_queue(item_id="ghost")], items=[])
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.failed_count == 1
    assert "GRS-DB-001" in result.error_codes


# --- secret / CLI ------------------------------------------------------------


def test_no_secret_like_value_in_handoff() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    text = repr(result.handoff_records)
    for needle in ("password", "api_key", "secret", "token", "postgresql://"):
        assert needle not in text.lower()


def test_scaffold_demo_job_runs() -> None:
    result = build_scaffold_demo_job().run(job_run_id="demo")
    assert result.status in {"succeeded", "partially_succeeded"}
    assert result.hashed_count >= 1


def test_cli_scaffold_demo_returns_zero() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "demo"]) == 0


def test_cli_without_scaffold_returns_three() -> None:
    assert main([]) == 3
