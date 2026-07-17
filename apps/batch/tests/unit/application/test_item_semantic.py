"""Unit tests for BATCH-010 Item Semantic 生成（仕様書 §16 unit 観点・最小）."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.item_semantic import (
    BATCH_ID,
    ITEM_SEMANTIC_PHASES,
    ItemContext,
    ItemSemanticJob,
    ItemSemanticRepositories,
    ItemSemanticRow,
    QueueRow,
    ScaffoldItemSemanticAdapter,
    build_scaffold_adapter,
    compute_semantic_input_hash,
)
from batch.application.item_semantic.__main__ import build_scaffold_demo_job, main
from batch.application.item_semantic.models import SemanticGenerationContext
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)
_VERSION = "scaffold-semantic-config-v1"
_FORBIDDEN_WRITE_TABLES = frozenset({"item", "product_diff_result"})


def _queue(
    *,
    item_generation_queue_id: str = "igq_1",
    item_id: str = "it_1",
    generation_type: str = "semantic",
    queue_status: str = "queued",
) -> QueueRow:
    return QueueRow(
        item_generation_queue_id=item_generation_queue_id,
        item_id=item_id,
        generation_type=generation_type,  # type: ignore[arg-type]
        queue_status=queue_status,  # type: ignore[arg-type]
        queued_at=_NOW,
    )


def _item(
    *,
    item_id: str = "it_1",
    source: str = "rakuten",
    item_name: str | None = "Gift A",
    genre_name: str | None = "ギフト",
    attributes: tuple[str, ...] = ("包装",),
    tags: tuple[str, ...] = ("季節",),
) -> ItemContext:
    return ItemContext(
        item_id=item_id,
        source=source,
        external_item_code=f"shop:{item_id}",
        active_status="active",
        is_active=True,
        item_name=item_name,
        genre_name=genre_name,
        attributes=attributes,
        tags=tags,
    )


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemContext] | None = None,
    semantics: list[ItemSemanticRow] | None = None,
) -> tuple[ItemSemanticRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ItemSemanticRepositories(
        db_writer=db,
        seed_queues=list(queues or [_queue()]),
        seed_items=list(items or [_item()]),
        seed_semantics=list(semantics or []),
    )
    return repos, db


def test_claim_generate_upsert_keeps_processing() -> None:
    repos, db = _repos()
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-ok")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.claimed_count == 1
    assert result.semantic_generated_count == 1
    assert set(ITEM_SEMANTIC_PHASES).issubset(set(result.completed_phases))
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    assert len(repos.written_item_semantic_rows) == 1
    tables = {c["table"] for c in db.write_calls}
    assert "item_semantic" in tables
    assert "item_generation_queue" in tables
    assert tables.isdisjoint(_FORBIDDEN_WRITE_TABLES)
    assert repos.queue_insert_count == 0
    assert repos.item_write_count == 0


def test_skip_unchanged_no_upsert() -> None:
    ctx = SemanticGenerationContext(
        trace_id="t",
        batch_run_id="r",
        item_generation_queue_id="igq_1",
        item_id="it_1",
        semantic_config_version_id=_VERSION,
        item_name="Gift A",
        genre_name="ギフト",
        attributes=("包装",),
        tags=("季節",),
    )
    h = compute_semantic_input_hash(ctx)
    repos, db = _repos(
        semantics=[
            ItemSemanticRow(
                item_semantic_id="is_existing",
                item_id="it_1",
                semantic_config_version_id=_VERSION,
                semantic_json={"concepts": [{"concept_code": "existing"}]},
                semantic_input_hash=h,
            )
        ]
    )
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-skip")

    assert result.status == "succeeded"
    assert result.semantic_skipped_count == 1
    assert result.semantic_generated_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert repos.written_item_semantic_rows == []
    assert "item_semantic" not in {c["table"] for c in db.write_calls if c.get("op") != "claim"}


def test_generation_type_filter_skips_feature() -> None:
    repos, _ = _repos(
        queues=[
            _queue(item_generation_queue_id="igq_f", item_id="it_f", generation_type="feature"),
            _queue(item_generation_queue_id="igq_s", item_id="it_s", generation_type="semantic"),
        ],
        items=[_item(item_id="it_f"), _item(item_id="it_s", item_name="Semantic Only")],
    )
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-filter")

    assert result.status == "succeeded"
    assert result.non_semantic_skip_count == 1
    assert result.claimed_count == 1
    assert result.semantic_generated_count == 1
    assert repos.queues["igq_f"]["queue_status"] == "queued"
    assert repos.queues["igq_s"]["queue_status"] == "processing"


def test_failed_generation_marks_queue_failed() -> None:
    repos, _ = _repos()
    adapter = ScaffoldItemSemanticAdapter(
        find_existing=lambda *_: None,
        force_fail=True,
    )
    result = ItemSemanticJob(repositories=repos, generator=adapter).run(job_run_id="run-fail")

    assert result.status == "failed"
    assert result.semantic_failed_count == 1
    assert "GRS-BAT-008" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"
    assert repos.written_item_semantic_rows == []


def test_empty_text_generates_empty_concepts() -> None:
    repos, _ = _repos(items=[_item(item_name=None, genre_name=None, attributes=(), tags=())])
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-empty")

    assert result.status == "succeeded"
    assert result.semantic_generated_count == 1
    row = repos.written_item_semantic_rows[0]
    assert row["semantic_json"] == {"concepts": []}


def test_missing_item_fails_grs_db_001() -> None:
    repos, _ = _repos(queues=[_queue(item_id="it_missing")], items=[])
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-missing")

    assert result.semantic_failed_count == 1
    assert "GRS-DB-001" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_partial_success_grs_bat_002() -> None:
    repos, _ = _repos(
        queues=[
            _queue(item_generation_queue_id="igq_ok", item_id="it_ok"),
            _queue(item_generation_queue_id="igq_bad", item_id="it_bad"),
        ],
        items=[_item(item_id="it_ok"), _item(item_id="it_bad")],
    )

    class SelectiveFail(ScaffoldItemSemanticAdapter):
        def generate_item_semantic(self, context: SemanticGenerationContext):  # type: ignore[override]
            if context.item_id == "it_bad":
                self.force_fail = True
            else:
                self.force_fail = False
            return super().generate_item_semantic(context)

    adapter = SelectiveFail(find_existing=lambda *_: None)
    result = ItemSemanticJob(repositories=repos, generator=adapter).run(job_run_id="run-partial")

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.semantic_generated_count == 1
    assert result.semantic_failed_count == 1


def test_if_boundary_no_queue_insert() -> None:
    repos, db = _repos()
    ItemSemanticJob(repositories=repos).run(job_run_id="run-boundary")

    assert repos.queue_insert_count == 0
    for call in db.write_calls:
        if call["table"] == "item_generation_queue":
            for row in call["rows"]:
                assert row.get("op") in {"claim", "update_status", "semantic_success_keep_processing"}


def test_cli_scaffold_demo_exit_0() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli-demo"]) == 0


def test_cli_non_scaffold_exit_3() -> None:
    assert main(["--job-run-id", "no-db"]) == 3


def test_scaffold_demo_builder() -> None:
    job = build_scaffold_demo_job()
    result = job.run(job_run_id="builder")
    assert result.status == "succeeded"
    assert result.semantic_generated_count == 1


def test_build_scaffold_adapter_hash_stable() -> None:
    adapter = build_scaffold_adapter(find_existing=lambda *_: None)
    ctx = SemanticGenerationContext(
        trace_id="t",
        batch_run_id="r",
        item_generation_queue_id="q",
        item_id="it",
        semantic_config_version_id="v1",
        item_name="A",
    )
    r1 = adapter.generate_item_semantic(ctx)
    r2 = adapter.generate_item_semantic(ctx)
    assert r1.status == "generated"
    assert r1.semantic_input_hash == r2.semantic_input_hash
