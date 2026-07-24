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
    repos, db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert len(result.handoff_records) == 1
    record = result.handoff_records[0]
    assert record["op"] == "if_db_batch_015_handoff"
    assert record["model_version_id"] == DEFAULT_EMBEDDING_MODEL_VERSION
    assert len(record["embedding_input_hash"]) == 64
    # BATCH-014 は item_embedding へ DML しない（BATCH-015 責務）
    assert repos.item_embedding_write_count == 0
    assert result.item_embedding_write_count == 0
    upsert_tables = {c["table"] for c in db.upsert_calls}
    assert "item_embedding_input" in upsert_tables
    assert "embedding_input_hash_handoff" not in upsert_tables
    assert "item_embedding" not in upsert_tables
    assert "item_embedding" not in {c["table"] for c in db.write_calls}


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


# --- §16 拡充: Queue フィルタ網羅 -------------------------------------------


def test_feature_continuation_is_processed() -> None:
    repos, _db = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.hashed_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "processing"


def test_embedding_processing_continuation_is_processed() -> None:
    repos, _db = _repos(
        queues=[_queue(qid="igq_emb_p", generation_type="embedding", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.hashed_count == 1
    assert repos.queues["igq_emb_p"]["queue_status"] == "processing"


def test_semantic_queued_is_not_targeted() -> None:
    # semantic は processing（継続）のみ対象。queued は BATCH-010 前段なので対象外
    repos, _db = _repos(
        queues=[_queue(qid="igq_sem_q", generation_type="semantic", queue_status="queued")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.planned_queue_count == 0
    assert result.hashed_count == 0


def test_failed_queue_is_not_targeted() -> None:
    repos, _db = _repos(
        queues=[_queue(qid="igq_failed", generation_type="embedding", queue_status="failed")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.planned_queue_count == 0


def test_claim_sets_processing_for_queued_embedding() -> None:
    repos, _db = _repos()
    assert repos.queues["igq_1"]["queue_status"] == "queued"
    EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert repos.queues["igq_1"]["queue_status"] == "processing"


def test_item_id_filter_limits_targets() -> None:
    repos, _db = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1", item_ids=["it_a"])
    assert result.planned_queue_count == 1
    assert result.succeeded_queue_ids == ["igq_a"]


def test_max_items_limit_is_applied() -> None:
    repos, _db = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1", max_items=1)
    assert result.planned_queue_count == 1


# --- §16 拡充: 部分成功・concurrency・空plan ---------------------------------


def test_partial_success_marks_grs_bat_002() -> None:
    repos, _db = _repos(
        queues=[
            _queue(qid="igq_ok", item_id="it_ok"),
            _queue(qid="igq_ng", item_id="ghost"),
        ],
        items=[_item(item_id="it_ok")],  # it_ok のみ存在、ghost は欠損
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.hashed_count == 1
    assert result.failed_count == 1


def test_concurrent_start_rejected_grs_bat_003() -> None:
    from batch.application.job_run import ScaffoldJobRunTracker

    repos, _db = _repos()
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="run-a")
    result = EmbeddingInputHashJob(repositories=repos, job_run_tracker=tracker).run(
        job_run_id="run-b"
    )
    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes


def test_empty_plan_with_existing_queue_succeeds() -> None:
    # 対象外 queue のみ存在 → GRS-BAT-001 ではなく succeeded
    repos, _db = _repos(
        queues=[_queue(qid="igq_done", generation_type="embedding", queue_status="succeeded")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.status == "succeeded"
    assert "GRS-BAT-001" not in result.error_codes


# --- §16 拡充: IF 境界・冪等キー -------------------------------------------


def test_handoff_op_is_if_db_batch_015_not_014() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    record = result.handoff_records[0]
    assert record["op"] == "if_db_batch_015_handoff"
    assert "if_db_batch_014" not in record["op"]


def test_handoff_preserves_idempotent_key_fields() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    record = result.handoff_records[0]
    # 冪等キー: item_id + model_version_id + embedding_input_hash
    assert record["item_id"] == "it_1"
    assert record["model_version_id"] == DEFAULT_EMBEDDING_MODEL_VERSION
    assert len(record["embedding_input_hash"]) == 64
    assert record["embedding_source_type"] == _SOURCE_TYPE


def test_handoff_context_contains_item_text_fields() -> None:
    repos, _db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    context = result.handoff_records[0]["item_text_context"]
    for key in ("item_id", "item_name", "genre_id", "attributes", "embedding_source_version"):
        assert key in context
    assert "semantic_concepts" not in context


def test_no_item_embedding_dml_across_all_paths() -> None:
    # skip / hashed 双方で item_embedding へ書込しない
    ctx = _context()
    digest = compute_embedding_input_hash(ctx)
    repos, _db = _repos(
        queues=[
            _queue(qid="igq_hash", item_id="it_1"),
            _queue(qid="igq_skip", item_id="it_2"),
        ],
        items=[_item(item_id="it_1"), _item(item_id="it_2")],
        embeddings={
            "it_2": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=compute_embedding_input_hash(_context(_item(item_id="it_2"))),
                )
            ]
        },
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.item_embedding_write_count == 0
    assert repos.item_embedding_write_count == 0
    assert result.hashed_count == 1
    assert result.skipped_count == 1
    _ = digest
