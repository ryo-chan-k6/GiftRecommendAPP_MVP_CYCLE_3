"""Unit tests for BATCH-015 Item Embedding生成（仕様書 §16 最小）."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.item_embedding import (
    BATCH_ID,
    DEFAULT_EMBEDDING_MODEL_VERSION,
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
    repos, _db = _repos()
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
    repos, _ = _repos(
        queues=[_queue(queue_status="queued")],
    )
    result = _run(repos)
    assert result.claimed_count == 1
    assert repos.queues["igq_1"]["queue_status"] == "succeeded"


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


def test_non_scaffold_demo_exits_3() -> None:
    assert main(["--job-run-id", "x"]) == 3


def test_config_keys_present() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_item_embedding_max_items == 1000
    assert settings.batch_item_embedding_source == "rakuten"
    assert settings.batch_item_embedding_queue_batch_size == 100
