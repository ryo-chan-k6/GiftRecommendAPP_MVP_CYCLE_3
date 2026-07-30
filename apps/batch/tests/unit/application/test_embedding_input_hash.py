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
    repos, db = _repos()
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.hashed_count == 1
    assert result.skipped_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    assert set(EMBEDDING_INPUT_HASH_PHASES).issubset(set(result.completed_phases))
    # claim は update_rows。keep_processing は DB no-op（終端 update なし）。
    claim_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "processing"
    ]
    assert len(claim_updates) == 1
    assert claim_updates[0]["equals"] == (
        ("item_generation_queue_id", "igq_1"),
        ("queue_status", "queued"),
        ("generation_type", "embedding"),
    )
    terminal_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") != "processing"
    ]
    assert terminal_updates == []
    assert db.write_calls == []
    assert all("op" not in str(c.get("set_values", {})) for c in db.update_calls)


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
    repos, db = _repos(
        queues=[_queue(qid="igq_sem", generation_type="semantic", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")

    assert result.hashed_count == 1
    assert repos.queues["igq_sem"]["queue_status"] == "processing"
    # processing 継続は DB no-op（偽 op=continue_processing 廃止）
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}
    assert db.write_calls == []


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
    repos, db = _repos(
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
    skip_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "skipped"
    ]
    assert len(skip_updates) == 1
    assert skip_updates[0]["equals"] == (("item_generation_queue_id", "igq_1"),)


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
    repos, db = _repos()
    result = EmbeddingInputHashJob(repositories=repos, force_hash_fail=True).run(job_run_id="r1")

    assert result.failed_count == 1
    assert "GRS-BAT-007" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"
    fail_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "failed"
    ]
    assert len(fail_updates) == 1


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


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.embedding_input_hash import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main([]) == 2


def test_list_target_queues_and_load_item_via_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_emb",
                "item_id": "it_1",
                "generation_type": "embedding",
                "queue_status": "queued",
                "retry_count": 0,
            },
            {
                "item_generation_queue_id": "igq_sem",
                "item_id": "it_2",
                "generation_type": "semantic",
                "queue_status": "processing",
                "retry_count": 0,
            },
            {
                "item_generation_queue_id": "igq_feat_q",
                "item_id": "it_3",
                "generation_type": "feature",
                "queue_status": "queued",
                "retry_count": 0,
            },
        ),
    )
    reader.seed(
        "item",
        (
            {
                "item_id": "it_1",
                "source": "rakuten",
                "external_item_code": "shop:1",
                "item_name": "Emb",
                "item_caption": None,
                "catchcopy": None,
                "active_status": "active",
                "is_active": True,
                "price": 100,
            },
            {
                "item_id": "it_2",
                "source": "rakuten",
                "external_item_code": "shop:2",
                "item_name": "Sem",
                "item_caption": None,
                "catchcopy": None,
                "active_status": "active",
                "is_active": True,
                "price": 200,
            },
        ),
    )
    repos = EmbeddingInputHashRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    targets, _ = repos.list_target_queues(max_items=10)
    assert [q.item_generation_queue_id for q in targets] == ["igq_emb", "igq_sem"]
    assert sum(1 for c in reader.fetch_calls if c["table"] == "item_generation_queue") >= 4
    item = repos.load_item(item_id="it_1")
    assert item.item_name == "Emb"
    assert item.genre_name is None
    assert item.attributes == ()


def test_feature_continuation_is_processed() -> None:
    repos, db = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.hashed_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "processing"
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}


def test_embedding_processing_continuation_is_processed() -> None:
    repos, db = _repos(
        queues=[_queue(qid="igq_emb_p", generation_type="embedding", queue_status="processing")],
    )
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="r1")
    assert result.hashed_count == 1
    assert repos.queues["igq_emb_p"]["queue_status"] == "processing"
    # embedding+processing 継続も DB no-op
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}


def test_claim_conflict_returns_none_when_rows_affected_zero() -> None:
    """embedding claim で rows_affected==0 なら None（競合 skip）。"""

    from batch.infrastructure.db import DbWriteResult

    repos, _ = _repos()

    def _zero_update(table: str, *, set_values, equals):  # noqa: ANN001
        return DbWriteResult(rows_affected=0, table=table)

    repos.db_writer.update_rows = _zero_update  # type: ignore[method-assign]
    claimed = repos.claim_or_continue(item_generation_queue_id="igq_1")
    assert claimed is None
    assert repos.queues["igq_1"]["queue_status"] == "queued"


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


# --- live DB 経路（#1762 current version 解決） ---

_EMBEDDING_MODEL_VERSION_ID = "c3333333-3333-4333-8333-333333333301"


def _live_reader():
    """master seed の current embedding model_version を持つ reader。"""

    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "model_version",
        (
            {
                "model_version_id": _EMBEDDING_MODEL_VERSION_ID,
                "model_type": "embedding",
                "is_current": True,
            },
            # llm / ranking の current 行が並存しても embedding だけを解決する
            {
                "model_version_id": "c3333333-3333-4333-8333-333333333302",
                "model_type": "llm",
                "is_current": True,
            },
        ),
    )
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_live",
                "item_id": "it_live",
                "generation_type": "embedding",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
                "started_at": None,
                "completed_at": None,
                "error_message": None,
            },
        ),
    )
    reader.seed(
        "item",
        (
            {
                "item_id": "it_live",
                "source": "rakuten",
                "external_item_code": "shop:live",
                "item_name": "Live Gift",
                "item_caption": "caption",
                "catchcopy": "catch",
                "active_status": "active",
                "is_active": True,
                "price": 1500,
            },
        ),
    )
    return reader


def test_live_db_reader_handoff_uses_current_model_version_uuid() -> None:
    """handoff / item_embedding_input に current embedding model UUID が伝播する。"""

    reader = _live_reader()
    db = ScaffoldDbWriter()
    repos = EmbeddingInputHashRepositories(db_writer=db, db_reader=reader)
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="run-live")

    assert result.status == "succeeded"
    assert result.hashed_count == 1
    assert result.handoff_records[0]["model_version_id"] == _EMBEDDING_MODEL_VERSION_ID
    assert result.handoff_records[0]["model_version_id"] != DEFAULT_EMBEDDING_MODEL_VERSION
    input_upserts = [c for c in db.upsert_calls if c["table"] == "item_embedding_input"]
    assert len(input_upserts) == 1
    assert input_upserts[0]["rows"][0]["model_version_id"] == _EMBEDDING_MODEL_VERSION_ID
    assert repos.queues["igq_live"]["queue_status"] == "processing"
    assert repos.item_embedding_write_count == 0


def test_live_db_reader_skip_uses_current_model_version_uuid() -> None:
    """skip 判定も resolver が解決した model_version_id で行う。"""

    reader = _live_reader()
    probe = EmbeddingInputHashRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    digest = compute_embedding_input_hash(
        build_item_text_context(
            item=probe.load_item(item_id="it_live"),
            embedding_source_type=_SOURCE_TYPE,
            embedding_source_version=DEFAULT_EMBEDDING_SOURCE_VERSION,
        )
    )
    reader.seed(
        "item_embedding",
        (
            {
                "item_id": "it_live",
                "model_version_id": _EMBEDDING_MODEL_VERSION_ID,
                "embedding_input_hash": digest,
                "embedding_vector": [0.1, 0.2],
            },
        ),
    )
    repos = EmbeddingInputHashRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="run-live-skip")

    assert result.skipped_count == 1
    assert result.hashed_count == 0
    assert result.handoff_records == []


def test_live_db_reader_resolver_failure_marks_queue_failed() -> None:
    """current embedding model version 欠落は既存の per-row failed 処理へ合流する。"""

    reader = _live_reader()
    reader.seed("model_version", ())
    db = ScaffoldDbWriter()
    repos = EmbeddingInputHashRepositories(db_writer=db, db_reader=reader)
    result = EmbeddingInputHashJob(repositories=repos).run(job_run_id="run-live-fail")

    assert result.status == "failed"
    assert result.failed_count == 1
    assert "GRS-CFG-003" in result.error_codes
    assert result.handoff_records == []
    assert repos.queues["igq_live"]["queue_status"] == "failed"
    failed_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "failed"
    ]
    assert len(failed_updates) == 1
