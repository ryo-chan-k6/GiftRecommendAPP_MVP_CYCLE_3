"""Unit tests for BATCH-015 Item Embedding生成（仕様書 §16 unit 観点）.

fixture/mock のみ。実 DB / 実 OpenAI / secret に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.item_embedding import (
    BATCH_ID,
    DEFAULT_EMBEDDING_MODEL_VERSION,
    DEFAULT_EMBEDDING_SOURCE_TYPE,
    EMBEDDING_DIMENSION,
    ITEM_EMBEDDING_PHASES,
    EmbeddingHashHandoff,
    ExistingEmbedding,
    ItemEmbeddingJob,
    ItemEmbeddingRepositories,
    ItemRow,
    QueueRow,
    build_deterministic_stub_vector,
    build_scaffold_adapter,
    is_valid_embedding_input_hash,
    resolve_config_version,
    serialize_embedding_input,
)
from batch.application.item_embedding.__main__ import build_scaffold_demo_job, main
from batch.application.job_run import ScaffoldJobRunTracker
from batch.config import scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 20, 12, 0, 0, tzinfo=UTC)
_HASH = "a" * 64
_HASH_B = "b" * 64


def _queue(
    *,
    qid: str = "igq_1",
    item_id: str = "it_1",
    generation_type: str = "embedding",
    queue_status: str = "processing",
) -> QueueRow:
    return QueueRow(
        item_generation_queue_id=qid,
        item_id=item_id,
        generation_type=generation_type,  # type: ignore[arg-type]
        queue_status=queue_status,  # type: ignore[arg-type]
        started_at=_NOW if queue_status == "processing" else None,
        queued_at=_NOW,
    )


def _item(*, item_id: str = "it_1") -> ItemRow:
    return ItemRow(
        item_id=item_id,
        source="rakuten",
        external_item_code=f"shop:{item_id}",
    )


def _context(*, item_id: str = "it_1") -> dict:
    return {
        "item_id": item_id,
        "item_name": "高級ハンドクリーム",
        "catchcopy": "上品",
        "item_caption": "ギフト向け",
        "genre_id": "100371",
        "genre_name": "美容・コスメ",
        "attributes": ["hand_care"],
        "tags": ["季節"],
        "embedding_source_type": "item_text_context",
        "embedding_source_version": "scaffold-embedding-source-v1",
    }


def _handoff(
    *,
    item_id: str = "it_1",
    qid: str = "igq_1",
    digest: str = _HASH,
    model_version_id: str = DEFAULT_EMBEDDING_MODEL_VERSION,
) -> EmbeddingHashHandoff:
    return EmbeddingHashHandoff(
        item_id=item_id,
        item_generation_queue_id=qid,
        model_version_id=model_version_id,
        embedding_source_type="item_text_context",
        embedding_source_version="scaffold-embedding-source-v1",
        embedding_input_hash=digest,
        item_text_context=_context(item_id=item_id),
    )


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemRow] | None = None,
    handoffs: list[EmbeddingHashHandoff] | None = None,
    embeddings: dict[str, list[ExistingEmbedding]] | None = None,
) -> tuple[ItemEmbeddingRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ItemEmbeddingRepositories(
        db_writer=db,
        seed_queues=list(queues) if queues is not None else [_queue()],
        seed_items=list(items) if items is not None else [_item()],
        seed_handoffs=list(handoffs) if handoffs is not None else [_handoff()],
        seed_embeddings=dict(embeddings or {}),
    )
    return repos, db


def _run(
    repos: ItemEmbeddingRepositories,
    *,
    tracker: ScaffoldJobRunTracker | None = None,
    force_fail: bool = False,
) -> object:
    job = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(force_fail=force_fail),
        job_run_tracker=tracker or ScaffoldJobRunTracker(),
    )
    return job.run(job_run_id="ut-run")


# --- scaffold / hash validation ---------------------------------------------


def test_stub_vector_is_1536_deterministic() -> None:
    a = build_deterministic_stub_vector(seed_text="hello")
    b = build_deterministic_stub_vector(seed_text="hello")
    c = build_deterministic_stub_vector(seed_text="other")
    assert len(a) == EMBEDDING_DIMENSION
    assert a == b
    assert a != c


def test_hash_validation_64_hex() -> None:
    assert is_valid_embedding_input_hash(_HASH)
    assert not is_valid_embedding_input_hash("short")
    assert not is_valid_embedding_input_hash("A" * 64)  # uppercase rejected


def test_serialize_embedding_input_is_stable() -> None:
    text = serialize_embedding_input(_context())
    assert "item_id" in text
    assert serialize_embedding_input(_context()) == text


# --- happy path / IF boundaries ---------------------------------------------


def test_generate_upsert_and_queue_succeeded() -> None:
    repos, db = _repos()
    result = _run(repos)
    assert result.status == "succeeded"
    assert result.generated_count == 1
    assert result.item_embedding_write_count == 1
    assert result.hash_recompute_count == 0
    assert result.distribution_metric_write_count == 0
    assert result.queue_insert_count == 0
    assert result.item_write_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "succeeded"
    row = repos.upsert_rows[0]
    assert row.embedding_source_type == "item_text_context"
    assert len(row.embedding_vector) == EMBEDDING_DIMENSION
    assert row.embedding_input_hash == _HASH
    assert row.model_version_id == DEFAULT_EMBEDDING_MODEL_VERSION
    assert "plan" in result.completed_phases
    assert "upsert_embedding" in result.completed_phases
    assert "finalize" in result.completed_phases
    assert set(ITEM_EMBEDDING_PHASES).issubset(set(result.completed_phases))
    assert BATCH_ID == "BATCH-015"
    # processing 継続は DB no-op。終端は update_rows。item_embedding は upsert_rows。
    assert db.write_calls == []
    emb_upserts = [c for c in db.upsert_calls if c["table"] == "item_embedding"]
    assert len(emb_upserts) == 1
    assert emb_upserts[0]["conflict_columns"] == (
        "item_id",
        "model_version_id",
        "embedding_input_hash",
    )
    assert emb_upserts[0]["update_columns"] == (
        "embedding_source_type",
        "embedding_vector",
        "generated_at",
    )
    terminal_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "succeeded"
    ]
    assert len(terminal_updates) == 1
    # api_call_log にベクトル全文・secret なし
    for log in repos.api_call_logs:
        assert "embedding_vector" not in log
        assert "OPENAI" not in str(log)
        assert "api_key" not in str(log).lower()


def test_handoff_missing_fails_queue() -> None:
    repos, _ = _repos(handoffs=[])
    result = _run(repos)
    assert result.status == "failed"
    assert result.failed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "failed"
    assert result.item_embedding_write_count == 0


def test_handoff_invalid_hash_fails() -> None:
    bad = _handoff(digest="not-a-valid-hash")
    repos, _ = _repos(handoffs=[bad])
    result = _run(repos)
    assert result.failed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_does_not_recompute_hash() -> None:
    repos, _ = _repos()
    original = repos.handoffs["it_1"].embedding_input_hash
    result = _run(repos)
    assert result.hash_recompute_count == 0
    assert repos.upsert_rows[0].embedding_input_hash == original


# --- skip -------------------------------------------------------------------


def test_skip_when_same_three_key_exists() -> None:
    repos, _ = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=_HASH,
                    has_vector=True,
                )
            ]
        }
    )
    result = _run(repos)
    assert result.status == "succeeded"
    assert result.skipped_count == 1
    assert result.generated_count == 0
    assert result.item_embedding_write_count == 0
    assert result.api_call_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"


# --- queue targeting --------------------------------------------------------


def test_semantic_continuation_reaches_succeeded() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_sem", generation_type="semantic", queue_status="processing")],
        items=[_item()],
        handoffs=[_handoff(qid="igq_sem")],
    )
    result = _run(repos)
    assert result.generated_count == 1
    assert repos.queues["igq_sem"]["queue_status"] == "succeeded"


def test_embedding_queued_claim_then_succeeded() -> None:
    repos, db = _repos(
        queues=[_queue(queue_status="queued")],
    )
    result = _run(repos)
    assert result.claimed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "succeeded"
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
    assert all("op" not in str(c.get("set_values", {})) for c in db.update_calls)


# --- partial / concurrent ---------------------------------------------------


def test_partial_success_grs_bat_002() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_ok", item_id="it_ok"),
            _queue(qid="igq_bad", item_id="it_bad"),
        ],
        items=[_item(item_id="it_ok"), _item(item_id="it_bad")],
        handoffs=[
            _handoff(item_id="it_ok", qid="igq_ok", digest=_HASH),
            # it_bad: no handoff → failed
        ],
    )
    result = _run(repos)
    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.generated_count == 1
    assert result.failed_count == 1


def test_already_running_grs_bat_003() -> None:
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="other")
    repos, _ = _repos()
    result = _run(repos, tracker=tracker)
    assert "GRS-BAT-003" in result.error_codes
    assert result.generated_count == 0


def test_force_fail_generator() -> None:
    repos, _ = _repos()
    result = _run(repos, force_fail=True)
    assert result.failed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "failed"


# --- CLI / config -----------------------------------------------------------


def test_scaffold_demo_cli_succeeds() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "demo"]) == 0
    job = build_scaffold_demo_job()
    result = job.run(job_run_id="demo2")
    assert result.status == "succeeded"
    assert result.generated_count == 2


def test_non_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_embedding import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "x"]) == 2


def test_live_embedding_without_key_exits_2(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    # ensure load_batch_settings sees empty key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main(["--scaffold-demo", "--live-embedding"]) == 2


def test_list_load_handoff_via_db_reader() -> None:
    import json

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
                "active_status": "active",
                "is_active": True,
            },
            {
                "item_id": "it_2",
                "source": "rakuten",
                "external_item_code": "shop:2",
                "active_status": "active",
                "is_active": True,
            },
        ),
    )
    context = {
        "item_id": "it_1",
        "item_name": "Gift",
        "embedding_source_type": "item_text_context",
        "embedding_source_version": "scaffold-embedding-source-v1",
    }
    reader.seed(
        "item_embedding_input",
        (
            {
                "item_id": "it_1",
                "model_version_id": DEFAULT_EMBEDDING_MODEL_VERSION,
                "embedding_source_type": "item_text_context",
                "embedding_input_hash": _HASH,
                "item_text_context": json.dumps(context, ensure_ascii=False, sort_keys=True),
                "item_generation_queue_id": "igq_emb",
                "computed_at": _NOW,
            },
        ),
    )
    repos = ItemEmbeddingRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    targets, _ = repos.list_target_queues(max_items=10)
    assert [q.item_generation_queue_id for q in targets] == ["igq_emb", "igq_sem"]
    assert sum(1 for c in reader.fetch_calls if c["table"] == "item_generation_queue") >= 4
    item = repos.load_item(item_id="it_1")
    assert item.external_item_code == "shop:1"
    handoff = repos.load_hash_handoff(item_id="it_1")
    assert handoff is not None
    assert handoff.embedding_input_hash == _HASH
    assert handoff.item_text_context["item_name"] == "Gift"
    assert handoff.embedding_source_version == "scaffold-embedding-source-v1"


def test_skip_via_db_reader_item_embedding() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_embedding",
        (
            {
                "item_id": "it_1",
                "model_version_id": DEFAULT_EMBEDDING_MODEL_VERSION,
                "embedding_input_hash": _HASH,
                "embedding_vector": (0.1,) * 8,
                "embedding_source_type": "item_text_context",
            },
        ),
    )
    repos = ItemEmbeddingRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    assert repos.should_skip_embedding_generation(
        item_id="it_1",
        model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
        embedding_input_hash=_HASH,
    )
    assert any(c["table"] == "item_embedding" for c in reader.fetch_calls)


def test_cli_non_demo_runs_job_with_live_reader(monkeypatch) -> None:
    """DATABASE_URL ありなら exit 3 固定せず Job を起動する。"""

    from dataclasses import replace

    from batch.application.item_embedding import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    reader = ScaffoldDbReader()
    reader.backend = "postgres"

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_settings(),
            database_url="postgresql://localhost:5432/gift",
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(cli, "resolve_job_db_reader", lambda **_kwargs: reader)

    code = cli.main(["--job-run-id", "wave-f", "--max-items", "1"])
    # empty SELECT → plan failed (exit 1). Important: Job started (not config/exit-2/old exit-3).
    assert code == 1
    assert reader.fetch_calls


def test_cli_non_demo_live_embedding_wires_client(monkeypatch) -> None:
    """非 demo で --live-embedding が create_embedding_client(live=True) に配線される."""

    from dataclasses import replace

    from batch.application.item_embedding import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter
    from batch.infrastructure.external_ai import ScaffoldEmbeddingClient

    reader = ScaffoldDbReader()
    reader.backend = "postgres"
    calls: list[dict[str, object]] = []

    def _fake_create(api_key: str | None, *, live: bool = False, fallback=None):
        calls.append({"api_key_present": bool(api_key), "live": live})
        return ScaffoldEmbeddingClient()

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_settings(),
            database_url="postgresql://localhost:5432/gift",
            openai_api_key="sk-test-not-real",
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(cli, "resolve_job_db_reader", lambda **_kwargs: reader)
    monkeypatch.setattr(cli, "create_embedding_client", _fake_create)

    code = cli.main(["--job-run-id", "wave-f-live", "--live-embedding", "--max-items", "1"])
    assert code == 1
    assert calls == [{"api_key_present": True, "live": True}]


def test_cli_non_demo_live_embedding_without_key_exits_2(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_embedding import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings
    from batch.infrastructure.db import ScaffoldDbReader, ScaffoldDbWriter

    reader = ScaffoldDbReader()
    reader.backend = "postgres"

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(
            scaffold_settings(),
            database_url="postgresql://localhost:5432/gift",
            openai_api_key=None,
        ),
    )
    monkeypatch.setattr(cli, "create_db_writer", lambda _url: ScaffoldDbWriter())
    monkeypatch.setattr(cli, "resolve_job_db_reader", lambda **_kwargs: reader)

    assert cli.main(["--job-run-id", "no-key", "--live-embedding"]) == 2


def test_config_keys_present() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_item_embedding_max_items == 1000
    assert settings.batch_item_embedding_source == "rakuten"
    assert settings.batch_item_embedding_queue_batch_size == 100


# --- §16 拡充: IF-VEC-BATCH-001 冪等・再実行収束 ---------------------------


def test_upsert_passes_vector_literal_to_writer() -> None:
    """IF-VEC-BATCH-001: upsert_rows に embedding_vector（pgvector literal）を含める。"""

    repos, db = _repos()
    _run(repos)
    emb_upserts = [c for c in db.upsert_calls if c["table"] == "item_embedding"]
    assert emb_upserts
    payload = emb_upserts[0]["rows"][0]
    assert "op" not in payload
    assert "has_vector" not in payload
    assert "embedding_dimension" not in payload
    assert "item_embedding_id" not in payload
    assert "embedding_vector" in payload
    vector = payload["embedding_vector"]
    assert isinstance(vector, str)
    assert vector.startswith("[") and vector.endswith("]")
    assert vector.count(",") == EMBEDDING_DIMENSION - 1
    assert emb_upserts[0]["conflict_columns"] == (
        "item_id",
        "model_version_id",
        "embedding_input_hash",
    )
    assert emb_upserts[0]["update_columns"] == (
        "embedding_source_type",
        "embedding_vector",
        "generated_at",
    )
    assert db.write_calls == []


def test_same_three_key_rerun_converges_to_skip() -> None:
    """同一 3 列キー再実行: 1 回目 Upsert → 2 回目 skip・Queue skipped."""

    repos, _ = _repos(
        queues=[_queue(qid="igq_1", queue_status="queued")],
    )
    first = _run(repos)
    assert first.generated_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "succeeded"
    writes_after_first = repos.item_embedding_write_count
    api_logs_after_first = len(repos.api_call_logs)

    # 再実行用に queue を queued に戻す（同一 handoff・同一冪等キー）
    repos.queues["igq_1"]["queue_status"] = "queued"
    repos.queues["igq_1"]["completed_at"] = None
    second = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(),
        job_run_tracker=ScaffoldJobRunTracker(),
    ).run(job_run_id="ut-rerun")
    assert second.skipped_count == 1
    assert second.generated_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert repos.item_embedding_write_count == writes_after_first
    assert len(repos.api_call_logs) == api_logs_after_first  # skip 時は API 追加なし


def test_no_skip_when_hash_differs() -> None:
    repos, _ = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=_HASH_B,
                    has_vector=True,
                )
            ]
        }
    )
    result = _run(repos)
    assert result.generated_count == 1
    assert result.skipped_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "succeeded"


def test_no_skip_when_model_version_differs() -> None:
    repos, _ = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id="other-model-v1",
                    embedding_input_hash=_HASH,
                    has_vector=True,
                )
            ]
        }
    )
    result = _run(repos)
    assert result.generated_count == 1
    assert result.skipped_count == 0


def test_skip_requires_has_vector_true() -> None:
    repos, _ = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=_HASH,
                    has_vector=False,
                )
            ]
        }
    )
    result = _run(repos)
    assert result.generated_count == 1
    assert result.skipped_count == 0


# --- §16 拡充: Queue フィルタ網羅 -------------------------------------------


def test_feature_continuation_reaches_succeeded() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="processing")],
        handoffs=[_handoff(qid="igq_feat")],
    )
    result = _run(repos)
    assert result.generated_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "succeeded"


def test_semantic_queued_is_not_targeted() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_sem_q", generation_type="semantic", queue_status="queued")],
    )
    result = _run(repos)
    assert result.planned_queue_count == 0
    assert result.generated_count == 0
    assert repos.queues["igq_sem_q"]["queue_status"] == "queued"


def test_feature_queued_is_not_targeted() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_feat_q", generation_type="feature", queue_status="queued")],
    )
    result = _run(repos)
    assert result.planned_queue_count == 0
    assert repos.queues["igq_feat_q"]["queue_status"] == "queued"


def test_succeeded_queue_is_not_targeted() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_done", generation_type="embedding", queue_status="succeeded")],
    )
    result = _run(repos)
    assert result.planned_queue_count == 0
    assert result.status == "succeeded"


def test_failed_queue_is_not_targeted() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_failed", generation_type="embedding", queue_status="failed")],
    )
    result = _run(repos)
    assert result.planned_queue_count == 0


def test_skipped_queue_is_not_targeted() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_skip", generation_type="embedding", queue_status="skipped")],
    )
    result = _run(repos)
    assert result.planned_queue_count == 0


def test_empty_plan_with_existing_queue_succeeds() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_done", generation_type="embedding", queue_status="succeeded")],
    )
    result = _run(repos)
    assert result.status == "succeeded"
    assert "GRS-BAT-001" not in result.error_codes


def test_item_id_filter_limits_targets() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
        handoffs=[
            _handoff(item_id="it_a", qid="igq_a"),
            _handoff(item_id="it_b", qid="igq_b", digest=_HASH_B),
        ],
    )
    job = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(),
        job_run_tracker=ScaffoldJobRunTracker(),
    )
    result = job.run(job_run_id="ut-filter", item_ids=["it_a"])
    assert result.planned_queue_count == 1
    assert result.succeeded_queue_ids == ["igq_a"]
    assert repos.queues["igq_b"]["queue_status"] == "processing"


def test_queue_ids_filter_limits_targets() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
        handoffs=[
            _handoff(item_id="it_a", qid="igq_a"),
            _handoff(item_id="it_b", qid="igq_b", digest=_HASH_B),
        ],
    )
    job = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(),
        job_run_tracker=ScaffoldJobRunTracker(),
    )
    result = job.run(job_run_id="ut-qid", queue_ids=["igq_b"])
    assert result.planned_queue_count == 1
    assert result.succeeded_queue_ids == ["igq_b"]


def test_max_items_limit_is_applied() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
        handoffs=[
            _handoff(item_id="it_a", qid="igq_a"),
            _handoff(item_id="it_b", qid="igq_b", digest=_HASH_B),
        ],
    )
    job = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(),
        job_run_tracker=ScaffoldJobRunTracker(),
    )
    result = job.run(job_run_id="ut-max", max_items=1)
    assert result.planned_queue_count == 1


def test_source_filter_excludes_non_matching_item() -> None:
    repos, _ = _repos(
        items=[
            ItemRow(item_id="it_1", source="amazon", external_item_code="a:1"),
        ],
    )
    job = ItemEmbeddingJob(
        repositories=repos,
        generator=build_scaffold_adapter(),
        job_run_tracker=ScaffoldJobRunTracker(),
    )
    result = job.run(job_run_id="ut-src", source="rakuten")
    assert result.planned_queue_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "processing"


# --- §16 拡充: handoff 検証失敗経路 ----------------------------------------


def test_missing_item_marks_failed() -> None:
    repos, _ = _repos(items=[])
    result = _run(repos)
    assert result.failed_count == 1
    assert "GRS-DB-001" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_handoff_model_version_mismatch_fails() -> None:
    bad = _handoff(model_version_id="wrong-model")
    repos, _ = _repos(handoffs=[bad])
    result = _run(repos)
    assert result.failed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_handoff_source_type_mismatch_fails() -> None:
    handoff = EmbeddingHashHandoff(
        item_id="it_1",
        item_generation_queue_id="igq_1",
        model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
        embedding_source_type="other_type",
        embedding_source_version="scaffold-embedding-source-v1",
        embedding_input_hash=_HASH,
        item_text_context=_context(),
    )
    repos, _ = _repos(handoffs=[handoff])
    result = _run(repos)
    assert result.failed_count == 1


def test_handoff_empty_context_fails() -> None:
    handoff = EmbeddingHashHandoff(
        item_id="it_1",
        item_generation_queue_id="igq_1",
        model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
        embedding_source_type=DEFAULT_EMBEDDING_SOURCE_TYPE,
        embedding_source_version="scaffold-embedding-source-v1",
        embedding_input_hash=_HASH,
        item_text_context={},
    )
    repos, _ = _repos(handoffs=[handoff])
    result = _run(repos)
    assert result.failed_count == 1


# --- §16 拡充: IF 境界（015 消費 / 016 非使用 / hash 非再計算） -------------


def test_if_db_batch_016_not_used() -> None:
    repos, db = _repos()
    result = _run(repos)
    assert result.distribution_metric_write_count == 0
    assert repos.distribution_metric_write_count == 0
    tables = {c["table"] for c in db.write_calls} | {c["table"] for c in db.upsert_calls}
    assert "item_embedding_distribution_metric" not in tables
    assert "embedding_distribution_metric" not in tables


def test_hash_never_recomputed_on_skip_and_fail() -> None:
    # skip 経路
    repos_skip, _ = _repos(
        embeddings={
            "it_1": [
                ExistingEmbedding(
                    model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
                    embedding_input_hash=_HASH,
                    has_vector=True,
                )
            ]
        }
    )
    skip_result = _run(repos_skip)
    assert skip_result.hash_recompute_count == 0

    # fail 経路
    repos_fail, _ = _repos(handoffs=[])
    fail_result = _run(repos_fail)
    assert fail_result.hash_recompute_count == 0


def test_queue_insert_and_item_write_never_performed() -> None:
    repos, _ = _repos()
    result = _run(repos)
    assert result.queue_insert_count == 0
    assert result.item_write_count == 0
    assert repos.queue_insert_count == 0
    assert repos.item_write_count == 0


def test_embedding_source_type_fixed_to_item_text_context() -> None:
    repos, _ = _repos()
    result = _run(repos)
    assert repos.upsert_rows[0].embedding_source_type == DEFAULT_EMBEDDING_SOURCE_TYPE
    assert DEFAULT_EMBEDDING_SOURCE_TYPE == "item_text_context"
    config = resolve_config_version(item_id="it_1")
    assert config.embedding_source_type == DEFAULT_EMBEDDING_SOURCE_TYPE
    assert result.generated_count == 1


def test_scaffold_adapter_does_not_call_real_openai() -> None:
    """scaffold-first: 実 OpenAI 非呼出（スタブベクトルのみ）."""

    adapter = build_scaffold_adapter()
    assert adapter.__class__.__name__ == "ScaffoldItemEmbeddingAdapter"
    repos, _ = _repos()
    result = _run(repos)
    assert result.generated_count == 1
    assert len(repos.upsert_rows[0].embedding_vector) == 1536


# --- §16 拡充: secret / ベクトル全文非含有 ---------------------------------


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    forbidden = (
        "sk-",
        "openai_api_key",
        "api_key",
        "bearer ",
        "password",
        "secret_token",
    )
    handoff = _handoff()
    blob = (str(handoff) + str(_context()) + serialize_embedding_input(_context())).lower()
    for token in forbidden:
        assert token not in blob

    repos, db = _repos()
    _run(repos)
    for log in repos.api_call_logs:
        text = str(log).lower()
        assert "embedding_vector" not in text
        for token in forbidden:
            assert token not in text
    for log in repos.phase_logs + repos.error_logs:
        text = str(log)
        assert "embedding_vector" not in text
        # ログ経路に 1536 次元の vector 全文を出さない
        assert text.count(",") < 100
    for call in db.upsert_calls:
        if call["table"] != "item_embedding":
            continue
        for row in call["rows"]:
            assert "op" not in row
            assert "_embedding_vector" not in row
            assert "has_vector" not in row
            assert "embedding_dimension" not in row
            # Writer には vector（literal）を渡す（本番 SQL 必須）
            assert "embedding_vector" in row
            assert isinstance(row["embedding_vector"], str)
            row_text = str({k: v for k, v in row.items() if k != "embedding_vector"}).lower()
            for token in forbidden:
                assert token not in row_text
    assert db.write_calls == []


def test_claim_conflict_returns_none_when_rows_affected_zero() -> None:
    """embedding claim で rows_affected==0 なら None（競合 skip）。"""

    from batch.infrastructure.db import DbWriteResult

    repos, _ = _repos(queues=[_queue(queue_status="queued")])

    def _zero_update(table: str, *, set_values, equals):  # noqa: ANN001
        return DbWriteResult(rows_affected=0, table=table)

    repos.db_writer.update_rows = _zero_update  # type: ignore[method-assign]
    claimed = repos.claim_or_continue(item_generation_queue_id="igq_1")
    assert claimed is None
    assert repos.queues["igq_1"]["queue_status"] == "queued"


def test_module_constants_not_mod_batch_015_recheck() -> None:
    """MOD-BATCH-015（Recheck）と混同しない（BATCH_ID / phases）。"""

    assert BATCH_ID == "BATCH-015"
    assert "recheck" not in " ".join(ITEM_EMBEDDING_PHASES).lower()
