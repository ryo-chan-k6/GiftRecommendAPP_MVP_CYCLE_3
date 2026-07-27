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
    assert not any(c["table"] == "item_semantic" for c in db.write_calls)


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


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_semantic import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "job-real"]) == 2


def test_list_claimable_queues_uses_db_reader_when_injected() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_s",
                "item_id": "it_s",
                "generation_type": "semantic",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
                "started_at": None,
                "completed_at": None,
                "error_message": None,
            },
            {
                "item_generation_queue_id": "igq_f",
                "item_id": "it_f",
                "generation_type": "feature",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
                "started_at": None,
                "completed_at": None,
                "error_message": None,
            },
            {
                "item_generation_queue_id": "igq_other_src",
                "item_id": "it_amz",
                "generation_type": "semantic",
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
                "item_id": "it_s",
                "source": "rakuten",
                "external_item_code": "shop:s",
                "item_name": "Semantic Gift",
                "item_caption": None,
                "active_status": "active",
                "is_active": True,
            },
            {
                "item_id": "it_amz",
                "source": "amazon",
                "external_item_code": "shop:amz",
                "item_name": "Other Source",
                "item_caption": None,
                "active_status": "active",
                "is_active": True,
            },
        ),
    )
    repos = ItemSemanticRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    claimable, non_semantic = repos.list_claimable_queues(max_items=10, source="rakuten")
    assert [q.item_generation_queue_id for q in claimable] == ["igq_s"]
    # broad scan equals generation_type=semantic → non-semantic not visible
    assert non_semantic == 0
    assert any(c["table"] == "item_generation_queue" for c in reader.fetch_calls)
    assert any(c["table"] == "item" for c in reader.fetch_calls)


def test_list_claimable_queues_counts_non_semantic_when_queue_ids_set() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_s",
                "item_id": "it_s",
                "generation_type": "semantic",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
            },
            {
                "item_generation_queue_id": "igq_f",
                "item_id": "it_f",
                "generation_type": "feature",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
            },
        ),
    )
    reader.seed(
        "item",
        (
            {
                "item_id": "it_s",
                "source": "rakuten",
                "external_item_code": "shop:s",
                "item_name": "S",
                "item_caption": None,
                "active_status": "active",
                "is_active": True,
            },
            {
                "item_id": "it_f",
                "source": "rakuten",
                "external_item_code": "shop:f",
                "item_name": "F",
                "item_caption": None,
                "active_status": "active",
                "is_active": True,
            },
        ),
    )
    repos = ItemSemanticRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    claimable, non_semantic = repos.list_claimable_queues(
        max_items=10,
        queue_ids=("igq_s", "igq_f"),
    )
    assert [q.item_generation_queue_id for q in claimable] == ["igq_s"]
    assert non_semantic == 1


def test_load_item_and_find_item_semantic_via_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "it_1",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "item_name": "Gift A",
                "item_caption": "caption",
                "active_status": "active",
                "is_active": True,
            },
        ),
    )
    reader.seed(
        "item_semantic",
        (
            {
                "item_semantic_id": "is_1",
                "item_id": "it_1",
                "semantic_config_version_id": _VERSION,
                "semantic_json": {"concepts": [{"concept_code": "formal_refined"}]},
                "generated_at": _NOW,
            },
        ),
    )
    repos = ItemSemanticRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    item = repos.load_item(item_id="it_1")
    assert item.item_id == "it_1"
    assert item.item_name == "Gift A"
    assert item.genre_name is None
    assert item.attributes == ()
    assert item.tags == ()
    assert item.review_texts == ()

    found = repos.find_item_semantic(
        item_id="it_1", semantic_config_version_id=_VERSION
    )
    assert found is not None
    assert found.item_semantic_id == "is_1"
    assert found.semantic_json == {"concepts": [{"concept_code": "formal_refined"}]}
    assert found.semantic_input_hash is None
    assert (
        repos.find_item_semantic(item_id="it_1", semantic_config_version_id="missing")
        is None
    )


def test_claim_queue_hydrates_from_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_db",
                "item_id": "it_1",
                "generation_type": "semantic",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": _NOW,
            },
        ),
    )
    repos = ItemSemanticRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    claimed = repos.claim_queue(item_generation_queue_id="igq_db", started_at=_NOW)
    assert claimed is not None
    assert claimed.queue_status == "processing"
    assert "igq_db" in repos.queues


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


# --- §16 拡充（UT Task） ---


def test_generation_type_filter_skips_embedding() -> None:
    """§16 No.5: embedding 行は claim しない。"""

    repos, _ = _repos(
        queues=[
            _queue(item_generation_queue_id="igq_e", item_id="it_e", generation_type="embedding"),
            _queue(item_generation_queue_id="igq_s", item_id="it_s", generation_type="semantic"),
        ],
        items=[_item(item_id="it_e"), _item(item_id="it_s")],
    )
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-embed")

    assert result.non_semantic_skip_count == 1
    assert result.claimed_count == 1
    assert repos.queues["igq_e"]["queue_status"] == "queued"
    assert repos.queues["igq_s"]["queue_status"] == "processing"


def test_idempotent_upsert_overwrites_same_key() -> None:
    """§16 No.9: 同一 (item_id, version) 再実行で JSON 上書き収束。"""

    repos, _ = _repos(
        semantics=[
            ItemSemanticRow(
                item_semantic_id="is_old",
                item_id="it_1",
                semantic_config_version_id=_VERSION,
                semantic_json={"concepts": [{"concept_code": "old"}]},
                semantic_input_hash="deadbeef" * 8,
            )
        ]
    )
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-upsert-1")
    assert result.semantic_generated_count == 1
    first = repos.item_semantics[("it_1", _VERSION)]
    assert first["item_semantic_id"] == "is_old"
    assert first["semantic_json"] != {"concepts": [{"concept_code": "old"}]}

    # 入力変更 + 再 queued で再生成（同一キー上書き）
    repos.items["it_1"]["item_name"] = "Gift B Renamed"
    repos.queues["igq_1"]["queue_status"] = "queued"
    repos.queues["igq_1"]["started_at"] = None
    result2 = ItemSemanticJob(repositories=repos).run(job_run_id="run-upsert-2")
    assert result2.semantic_generated_count == 1
    second = repos.item_semantics[("it_1", _VERSION)]
    assert second["item_semantic_id"] == "is_old"
    assert second["semantic_json"] != first["semantic_json"]
    assert second["semantic_input_hash"] != first["semantic_input_hash"]


def test_config_version_fixed_on_item_semantic_row() -> None:
    """§16 No.8（unit 代替）: Upsert 行に semantic_config_version_id が固定される。"""

    repos, _ = _repos()
    ItemSemanticJob(repositories=repos).run(job_run_id="run-cfg")
    row = repos.written_item_semantic_rows[0]
    assert row["semantic_config_version_id"] == _VERSION
    assert row["item_id"] == "it_1"


def test_claim_conflict_skips_when_claim_fails() -> None:
    """§9.1: plan 上は queued でも claim 失敗時は当該行 skip。"""

    repos, _ = _repos()

    def _fail_claim(*, item_generation_queue_id: str, started_at=None):  # noqa: ANN001
        _ = item_generation_queue_id, started_at
        return None

    repos.claim_queue = _fail_claim  # type: ignore[method-assign]
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-conflict")

    assert result.status == "succeeded"
    assert result.claim_conflict_skip_count == 1
    assert result.claimed_count == 0
    assert result.semantic_generated_count == 0
    assert repos.written_item_semantic_rows == []


def test_claim_queue_rejects_non_queued_status() -> None:
    """repositories: processing 行への claim は None。"""

    repos, _ = _repos(queues=[_queue(queue_status="processing")])
    assert (
        repos.claim_queue(item_generation_queue_id="igq_1", started_at=_NOW) is None
    )


def test_concurrent_start_rejected_grs_bat_003() -> None:
    """多重起動拒否 GRS-BAT-003。"""

    from batch.application.job_run import ScaffoldJobRunTracker

    repos, _ = _repos()
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="run-a")
    result = ItemSemanticJob(repositories=repos, job_run_tracker=tracker).run(job_run_id="run-b")
    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert result.claimed_count == 0


def test_source_filter_excludes_non_matching_item() -> None:
    """plan: item.source がフィルタと不一致なら対象外。"""

    repos, _ = _repos(items=[_item(source="amazon")])
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-src", source="rakuten")
    assert result.planned_queue_count == 0
    assert result.status == "succeeded"
    assert repos.queues["igq_1"]["queue_status"] == "queued"


def test_max_items_limits_claim_plan() -> None:
    repos, _ = _repos(
        queues=[
            _queue(item_generation_queue_id="igq_a", item_id="it_a"),
            _queue(item_generation_queue_id="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b")],
    )
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-max", max_items=1)
    assert result.planned_queue_count == 1
    assert result.claimed_count == 1


def test_review_texts_excluded_from_semantic_input_hash() -> None:
    """§9.2: item_review は hash 対象外。"""

    base = dict(
        trace_id="t",
        batch_run_id="r",
        item_generation_queue_id="q",
        item_id="it",
        semantic_config_version_id="v1",
        item_name="A",
    )
    h1 = compute_semantic_input_hash(SemanticGenerationContext(**base, review_texts=()))
    h2 = compute_semantic_input_hash(
        SemanticGenerationContext(**base, review_texts=("長いレビュー文",))
    )
    assert h1 == h2


def test_if_shared_001_adapter_called_queue_dml_on_batch() -> None:
    """§16 No.4: IF-SHARED-001 経由。Queue DML は batch repos。"""

    repos, db = _repos()
    calls: list[str] = []

    class CountingAdapter(ScaffoldItemSemanticAdapter):
        def generate_item_semantic(self, context: SemanticGenerationContext):  # type: ignore[override]
            calls.append(context.item_generation_queue_id)
            return super().generate_item_semantic(context)

    adapter = CountingAdapter(
        find_existing=lambda item_id, version_id: repos.find_item_semantic(
            item_id=item_id, semantic_config_version_id=version_id
        )
    )
    result = ItemSemanticJob(repositories=repos, generator=adapter).run(job_run_id="run-if")
    assert calls == ["igq_1"]
    assert result.semantic_generated_count == 1
    queue_ops = [
        row.get("op")
        for c in db.write_calls
        if c["table"] == "item_generation_queue"
        for row in c["rows"]
    ]
    assert "claim" in queue_ops
    assert "semantic_success_keep_processing" in queue_ops


def test_explicit_queue_ids_subset() -> None:
    repos, _ = _repos(
        queues=[
            _queue(item_generation_queue_id="igq_keep", item_id="it_keep"),
            _queue(item_generation_queue_id="igq_skip", item_id="it_skip"),
        ],
        items=[_item(item_id="it_keep"), _item(item_id="it_skip")],
    )
    result = ItemSemanticJob(repositories=repos).run(
        job_run_id="run-subset",
        queue_ids=["igq_keep"],
    )
    assert result.claimed_count == 1
    assert repos.queues["igq_keep"]["queue_status"] == "processing"
    assert repos.queues["igq_skip"]["queue_status"] == "queued"


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    """§16 No.11: fixture / 結果に secret らしき文字列がない。"""

    repos, db = _repos()
    result = ItemSemanticJob(repositories=repos).run(job_run_id="run-sec")
    blob = repr(result) + repr(db.write_calls) + repr(repos.error_logs) + repr(repos.phase_logs)
    forbidden = ("password", "api_key", "secret", "Bearer ", "sk-", "postgresql://")
    lowered = blob.lower()
    for token in forbidden:
        assert token.lower() not in lowered
