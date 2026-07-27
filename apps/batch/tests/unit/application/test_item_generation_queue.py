"""Unit tests for BATCH-009 商品意味生成キュー登録（仕様書 §16 unit 観点）."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.item_generation_queue import (
    BATCH_ID,
    ITEM_GENERATION_QUEUE_PHASES,
    ItemGenerationQueueJob,
    ItemGenerationQueueRepositories,
    ItemRow,
    MeaningSnapshot,
    ProductDiffRow,
    QueueRow,
)
from batch.infrastructure.db import ScaffoldDbWriter

_HASH_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_HASH_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)

_FORBIDDEN_BOUNDARY_TABLES = frozenset({"item", "product_diff_result"})


def _diff(
    *,
    product_diff_result_id: str = "pdr_1",
    batch_run_id: str = "diff-run-1",
    staging_item_id: str = "si_1",
    external_item_code: str = "shop:gift-1",
    diff_status: str = "new",
    old_hash: str | None = None,
    new_hash: str | None = _HASH_A,
    previous_meaning: MeaningSnapshot | None = None,
    previous_price: int | None = None,
    previous_item_url: str | None = None,
    previous_review_average: float | None = None,
    previous_review_count: int | None = None,
    previous_availability: int | None = None,
    config_version_only: bool = False,
    feature_input_hash_only: bool = False,
    embedding_only: bool = False,
) -> ProductDiffRow:
    return ProductDiffRow(
        product_diff_result_id=product_diff_result_id,
        batch_run_id=batch_run_id,
        staging_item_id=staging_item_id,
        external_item_code=external_item_code,
        diff_status=diff_status,  # type: ignore[arg-type]
        old_hash=old_hash,
        new_hash=new_hash,
        previous_meaning=previous_meaning,
        previous_price=previous_price,
        previous_item_url=previous_item_url,
        previous_review_average=previous_review_average,
        previous_review_count=previous_review_count,
        previous_availability=previous_availability,
        config_version_only=config_version_only,
        feature_input_hash_only=feature_input_hash_only,
        embedding_only=embedding_only,
    )


def _item(
    *,
    external_item_code: str = "shop:gift-1",
    item_id: str | None = None,
    active_status: str = "active",
    is_active: bool = True,
    normalized_hash: str | None = _HASH_A,
    item_name: str | None = "Gift A",
    item_caption: str | None = None,
    catchcopy: str | None = None,
    external_genre_id: str | None = None,
    price: int | None = 2500,
    item_url: str | None = "https://item.example/gift-1",
    review_average: float | None = 4.0,
    review_count: int | None = 10,
    availability: int | None = 1,
) -> ItemRow:
    return ItemRow(
        item_id=item_id or f"it_{external_item_code.replace(':', '_')}",
        source="rakuten",
        external_item_code=external_item_code,
        active_status=active_status,
        is_active=is_active,
        normalized_hash=normalized_hash,
        item_name=item_name,
        item_caption=item_caption,
        catchcopy=catchcopy,
        external_genre_id=external_genre_id,
        price=price,
        item_url=item_url,
        review_average=review_average,
        review_count=review_count,
        availability=availability,
    )


def _repos(
    *,
    diffs: list[ProductDiffRow] | None = None,
    items: list[ItemRow] | None = None,
    queues: list[QueueRow] | None = None,
) -> tuple[ItemGenerationQueueRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ItemGenerationQueueRepositories(
        db_writer=db,
        seed_diffs=list(diffs or [_diff()]),
        seed_items=list(items or [_item()]),
        seed_queues=list(queues or []),
    )
    return repos, db


def test_new_registers_semantic_insert() -> None:
    repos, db = _repos()
    job = ItemGenerationQueueJob(repositories=repos)

    result = job.run(job_run_id="run-new")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.queue_inserted_count == 1
    assert result.queue_semantic_count == 1
    assert set(ITEM_GENERATION_QUEUE_PHASES).issubset(set(result.completed_phases))
    assert len(repos.queues) == 1
    row = repos.queues[0]
    assert row["generation_type"] == "semantic"
    assert row["queue_status"] == "queued"
    assert row["retry_count"] == 0
    assert {c["table"] for c in db.write_calls} == {"item_generation_queue"}


def test_updated_meaning_registers_semantic() -> None:
    repos, _ = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Old Gift"),
            )
        ],
        items=[_item(normalized_hash=_HASH_B, item_name="New Gift")],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-meaning")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 1
    assert result.queue_semantic_count == 1
    assert repos.queues[0]["generation_type"] == "semantic"


def test_non_meaning_only_change_skips() -> None:
    repos, db = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Gift A"),
                previous_price=2000,
            )
        ],
        items=[_item(normalized_hash=_HASH_B, item_name="Gift A", price=3000)],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-non-meaning")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert result.queue_non_meaning_skip_count == 1
    assert "shop:gift-1" in result.skipped_external_codes
    assert db.write_calls == []


def test_non_meaning_review_only_change_skips() -> None:
    """§9.2: reviewAverage / reviewCount のみ変更は登録しない（price/url previous なし）。"""

    repos, db = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Gift A"),
                previous_review_average=3.5,
                previous_review_count=5,
            )
        ],
        items=[
            _item(
                normalized_hash=_HASH_B,
                item_name="Gift A",
                review_average=4.8,
                review_count=20,
            )
        ],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-review-only")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert result.queue_non_meaning_skip_count == 1
    assert "shop:gift-1" in result.skipped_external_codes
    assert db.write_calls == []


def test_non_meaning_availability_only_change_skips() -> None:
    """§9.2: availability のみ変更は登録しない（price/url previous なし）。"""

    repos, db = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Gift A"),
                previous_availability=0,
            )
        ],
        items=[
            _item(
                normalized_hash=_HASH_B,
                item_name="Gift A",
                availability=1,
            )
        ],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-availability-only")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert result.queue_non_meaning_skip_count == 1
    assert "shop:gift-1" in result.skipped_external_codes
    assert db.write_calls == []


def test_non_active_item_skips() -> None:
    repos, db = _repos(
        items=[_item(active_status="inactive", is_active=False)],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-inactive")

    assert result.status == "succeeded"
    assert result.queue_inactive_skip_count == 1
    assert result.queue_inserted_count == 0
    assert db.write_calls == []


def test_unchanged_and_unavailable_skip_at_plan() -> None:
    repos, db = _repos(
        diffs=[
            _diff(
                product_diff_result_id="pdr_unchanged",
                external_item_code="shop:unchanged",
                diff_status="unchanged",
            ),
            _diff(
                product_diff_result_id="pdr_unavailable",
                external_item_code="shop:unavailable",
                diff_status="unavailable",
            ),
        ],
        items=[
            _item(external_item_code="shop:unchanged"),
            _item(external_item_code="shop:unavailable"),
        ],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-skip-status")

    assert result.status == "succeeded"
    assert result.planned_diff_count == 0
    assert result.queue_unchanged_skip_count == 1
    assert result.queue_unavailable_skip_count == 1
    assert result.queue_inserted_count == 0
    assert db.write_calls == []
    # empty plan: 未実行 Phase を機械追記しない
    assert result.completed_phases == ["plan", "finalize"]


def test_active_queued_row_updates_queued_at_only() -> None:
    item = _item()
    repos, db = _repos(
        items=[item],
        queues=[
            QueueRow(
                item_generation_queue_id="igq_existing",
                item_id=item.item_id,
                generation_type="semantic",
                queue_status="queued",
                retry_count=0,
                queued_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ],
    )
    before_count = len(repos.queues)
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-touch")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert result.queue_queued_at_updated_count == 1
    assert len(repos.queues) == before_count
    assert repos.queues[0]["item_generation_queue_id"] == "igq_existing"
    assert repos.queues[0]["queued_at"] != datetime(2026, 1, 1, tzinfo=UTC)
    assert db.write_calls == []
    assert len(db.update_calls) == 1
    assert db.update_calls[0]["table"] == "item_generation_queue"
    assert db.update_calls[0]["set_values"] == {
        "queued_at": repos.queues[0]["queued_at"],
    }
    assert db.update_calls[0]["equals"] == (
        ("item_generation_queue_id", "igq_existing"),
    )
    assert all("op" not in str(c) for c in db.update_calls)


def test_processing_active_row_skips_register() -> None:
    item = _item()
    repos, db = _repos(
        items=[item],
        queues=[
            QueueRow(
                item_generation_queue_id="igq_processing",
                item_id=item.item_id,
                generation_type="semantic",
                queue_status="processing",
                retry_count=0,
                queued_at=_NOW,
            )
        ],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-processing")

    assert result.status == "succeeded"
    assert result.queue_processing_skip_count == 1
    assert result.queue_inserted_count == 0
    assert db.write_calls == []


def test_config_version_only_registers_feature() -> None:
    repos, _ = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_A,
                previous_meaning=MeaningSnapshot(item_name="Gift A"),
                config_version_only=True,
            )
        ],
        items=[_item(normalized_hash=_HASH_A, item_name="Gift A")],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-feature")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 1
    assert result.queue_feature_count == 1
    assert repos.queues[0]["generation_type"] == "feature"


def test_does_not_mutate_item_or_product_diff_result() -> None:
    repos, db = _repos()
    item_before = dict(repos.items[("rakuten", "shop:gift-1")])
    diff_before = dict(repos.product_diff_results["pdr_1"])

    ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-boundary")

    assert repos.items[("rakuten", "shop:gift-1")] == item_before
    assert repos.product_diff_results["pdr_1"] == diff_before
    assert repos.item_write_count == 0
    assert repos.product_diff_write_count == 0
    assert _FORBIDDEN_BOUNDARY_TABLES.isdisjoint({c["table"] for c in db.write_calls})


def test_max_items_filter_limits_plan() -> None:
    repos, _ = _repos(
        diffs=[
            _diff(product_diff_result_id="pdr_a", external_item_code="shop:a"),
            _diff(product_diff_result_id="pdr_b", external_item_code="shop:b"),
        ],
        items=[
            _item(external_item_code="shop:a", item_id="it_a"),
            _item(external_item_code="shop:b", item_id="it_b"),
        ],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-max", max_items=1)

    assert result.status == "succeeded"
    assert result.planned_diff_count == 1
    assert result.queue_inserted_count == 1


def test_cli_scaffold_demo_passes_filters(monkeypatch) -> None:
    from batch.application.item_generation_queue import __main__ as cli

    captured: dict[str, object] = {}

    class _FakeJob:
        def run(self, **kwargs):  # type: ignore[no-untyped-def]
            captured.update(kwargs)

            class _Result:
                status = "succeeded"
                succeeded_external_codes = ["shop:1"]
                failed_external_codes: list[str] = []
                skipped_external_codes: list[str] = []
                queue_inserted_count = 1
                queue_queued_at_updated_count = 0
                queue_semantic_count = 1
                completed_phases = list(ITEM_GENERATION_QUEUE_PHASES)

            return _Result()

    monkeypatch.setattr(cli, "build_scaffold_demo_job", lambda: _FakeJob())
    code = cli.main(
        [
            "--scaffold-demo",
            "--job-run-id",
            "job-cli",
            "--max-items",
            "42",
            "--source",
            "rakuten",
            "--diff-batch-run-id",
            "run-x",
            "--external-item-codes",
            "shop:1, shop:2",
        ]
    )
    assert code == 0
    assert captured["job_run_id"] == "job-cli"
    assert captured["max_items"] == 42
    assert captured["source"] == "rakuten"
    assert captured["diff_batch_run_id"] == "run-x"
    assert captured["external_item_codes"] == ("shop:1", "shop:2")


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_generation_queue import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "job-real"]) == 2


def test_list_eligible_diffs_uses_db_reader_when_injected() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "product_diff_result",
        (
            {
                "product_diff_result_id": "pdr_new",
                "batch_run_id": "run-1",
                "staging_item_id": "si_a",
                "external_item_code": "shop:a",
                "old_hash": None,
                "new_hash": _HASH_A,
                "diff_status": "new",
                "judged_at": None,
            },
            {
                "product_diff_result_id": "pdr_unchanged",
                "batch_run_id": "run-1",
                "staging_item_id": "si_b",
                "external_item_code": "shop:b",
                "old_hash": _HASH_A,
                "new_hash": _HASH_A,
                "diff_status": "unchanged",
                "judged_at": None,
            },
            {
                "product_diff_result_id": "pdr_unavail",
                "batch_run_id": "run-1",
                "staging_item_id": "si_c",
                "external_item_code": "shop:c",
                "old_hash": _HASH_A,
                "new_hash": _HASH_B,
                "diff_status": "unavailable",
                "judged_at": None,
            },
        ),
    )
    reader.seed(
        "item",
        (
            {
                "item_id": "it_a",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "active_status": "active",
                "is_active": True,
                "normalized_hash": _HASH_A,
                "item_name": "A",
                "item_caption": None,
                "catchcopy": None,
                "external_genre_id": None,
                "price": 1000,
                "item_url": "https://item.example/a",
            },
        ),
    )
    repos = ItemGenerationQueueRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    eligible, unavailable, unchanged = repos.list_eligible_diffs(max_items=10)
    assert [d.product_diff_result_id for d in eligible] == ["pdr_new"]
    assert unavailable == 1
    assert unchanged == 1
    # DDL に無い previous_* は既定
    assert eligible[0].previous_meaning is None
    assert eligible[0].config_version_only is False


def test_load_item_and_find_active_queue_via_db_reader() -> None:
    from datetime import UTC, datetime

    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item",
        (
            {
                "item_id": "it_1",
                "source": "rakuten",
                "external_item_code": "shop:a",
                "active_status": "active",
                "is_active": True,
                "normalized_hash": _HASH_A,
                "item_name": "A",
                "item_caption": None,
                "catchcopy": None,
                "external_genre_id": None,
                "price": 1000,
                "item_url": "https://item.example/a",
            },
        ),
    )
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_1",
                "item_id": "it_1",
                "generation_type": "semantic",
                "queue_status": "queued",
                "retry_count": 0,
                "queued_at": datetime.now(UTC),
            },
        ),
    )
    repos = ItemGenerationQueueRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    item = repos.load_item(source="rakuten", external_item_code="shop:a")
    assert item.item_id == "it_1"
    assert item.review_average is None
    assert item.availability is None
    active = repos.find_active_queue(item_id="it_1", generation_type="semantic")
    assert active is not None
    assert active["item_generation_queue_id"] == "igq_1"
    assert repos.find_active_queue(item_id="it_1", generation_type="feature") is None


def test_feature_input_hash_only_skips_in_mvp() -> None:
    repos, db = _repos(
        diffs=[_diff(diff_status="updated", feature_input_hash_only=True)],
        items=[_item()],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-fih")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert db.write_calls == []


def test_embedding_only_skips_in_mvp() -> None:
    repos, db = _repos(
        diffs=[_diff(diff_status="updated", embedding_only=True)],
        items=[_item()],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-emb")

    assert result.status == "succeeded"
    assert result.queue_inserted_count == 0
    assert db.write_calls == []


def test_excluded_and_unavailable_active_status_skips() -> None:
    """§16 No.3: unavailable / excluded も非 active として登録しない。"""

    for status in ("unavailable", "excluded"):
        repos, db = _repos(
            items=[_item(active_status=status, is_active=False)],
        )
        result = ItemGenerationQueueJob(repositories=repos).run(job_run_id=f"run-{status}")
        assert result.status == "succeeded"
        assert result.queue_inactive_skip_count == 1
        assert result.queue_inserted_count == 0
        assert db.write_calls == []


def test_idempotent_rerun_converges_to_queued_at_touch() -> None:
    """§16 No.11: 同一条件の再実行で INSERT せず queued_at 更新に収束。"""

    repos, _ = _repos()
    job = ItemGenerationQueueJob(repositories=repos)
    first = job.run(job_run_id="run-idem-1")
    assert first.queue_inserted_count == 1
    assert len(repos.queues) == 1
    queue_id = repos.queues[0]["item_generation_queue_id"]
    first_queued_at = repos.queues[0]["queued_at"]

    second = job.run(job_run_id="run-idem-2")
    assert second.status == "succeeded"
    assert second.queue_inserted_count == 0
    assert second.queue_queued_at_updated_count == 1
    assert len(repos.queues) == 1
    assert repos.queues[0]["item_generation_queue_id"] == queue_id
    assert repos.queues[0]["queued_at"] != first_queued_at


def test_partial_success_one_item_fails_grs_bat_002(monkeypatch) -> None:
    """§16 No.12: 一部失敗で partially_succeeded + GRS-BAT-002。"""

    from batch.application.item_generation_queue.job import ItemGenerationQueueError

    repos, _ = _repos(
        diffs=[
            _diff(product_diff_result_id="pdr_ok", external_item_code="shop:ok"),
            _diff(product_diff_result_id="pdr_ng", external_item_code="shop:ng"),
        ],
        items=[
            _item(external_item_code="shop:ok", item_id="it_ok"),
            _item(external_item_code="shop:ng", item_id="it_ng"),
        ],
    )
    original = repos.insert_queue

    def _insert(*, item_id: str, generation_type: str, queued_at):  # type: ignore[no-untyped-def]
        if item_id == "it_ng":
            raise ItemGenerationQueueError("GRS-DB-002", "queue insert failed")
        return original(item_id=item_id, generation_type=generation_type, queued_at=queued_at)

    monkeypatch.setattr(repos, "insert_queue", _insert)
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-partial")

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert "shop:ok" in result.succeeded_external_codes
    assert "shop:ng" in result.failed_external_codes
    assert result.queue_inserted_count == 1
    assert result.queue_register_failed_count == 1


def test_if_boundary_writes_only_item_generation_queue() -> None:
    """§16 No.9/10 unit 代替: IF-DB-BATCH-010 のみ書込。item / Diff / 派生なし。"""

    repos, db = _repos()
    ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-if")
    tables = {c["table"] for c in db.write_calls}
    assert tables == {"item_generation_queue"}
    assert db.update_calls == []
    assert repos.item_write_count == 0
    assert repos.product_diff_write_count == 0
    for call in db.write_calls:
        assert "active_status" not in str(call["rows"])
        for row in call["rows"]:
            assert "op" not in row
            # DDL uuid PK（client 生成）
            qid = row["item_generation_queue_id"]
            assert isinstance(qid, str) and len(qid) == 36


def test_scaffold_partial_unique_prevents_duplicate_active_insert() -> None:
    """§16 No.8 unit 代替: active (item_id, generation_type) 二重 INSERT を避ける。"""

    repos, _ = _repos()
    job = ItemGenerationQueueJob(repositories=repos)
    job.run(job_run_id="run-uq-1")
    job.run(job_run_id="run-uq-2")
    active = [
        q
        for q in repos.queues
        if q["queue_status"] in {"queued", "processing"}
        and q["generation_type"] == "semantic"
        and q["item_id"] == "it_shop_gift-1"
    ]
    assert len(active) == 1


def test_missing_item_fails_grs_db_001() -> None:
    """§8.2: Item 欠落は当該行失敗（GRS-DB-001）。"""

    db = ScaffoldDbWriter()
    repos = ItemGenerationQueueRepositories(
        db_writer=db,
        seed_diffs=[_diff(external_item_code="shop:missing")],
        seed_items=[],
        seed_queues=[],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-miss")
    assert result.status == "failed"
    assert "shop:missing" in result.failed_external_codes
    assert "GRS-DB-001" in result.error_codes
    assert result.queue_inserted_count == 0


def test_concurrent_start_rejected_grs_bat_003() -> None:
    """多重起動拒否（実装の GRS-BAT-003）。"""

    from batch.application.job_run import ScaffoldJobRunTracker

    repos, _ = _repos()
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="run-a")
    result = ItemGenerationQueueJob(repositories=repos, job_run_tracker=tracker).run(
        job_run_id="run-b"
    )
    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert result.queue_inserted_count == 0


def test_meaning_change_beats_config_version_only_flag() -> None:
    """意味影響ありなら config_version_only フラグより semantic を優先。"""

    repos, _ = _repos(
        diffs=[
            _diff(
                diff_status="updated",
                old_hash=_HASH_A,
                new_hash=_HASH_B,
                previous_meaning=MeaningSnapshot(item_name="Old"),
                config_version_only=True,
            )
        ],
        items=[_item(normalized_hash=_HASH_B, item_name="New")],
    )
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-priority")
    assert result.status == "succeeded"
    assert result.queue_semantic_count == 1
    assert repos.queues[0]["generation_type"] == "semantic"


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    """§16 No.13: fixture / 結果に secret らしき文字列がない。"""

    repos, db = _repos()
    result = ItemGenerationQueueJob(repositories=repos).run(job_run_id="run-sec")
    blob = repr(result) + repr(db.write_calls) + repr(db.update_calls) + repr(repos.error_logs)
    for needle in ("sk-", "password=", "Bearer ", "DATABASE_URL=", "OPENAI_API_KEY="):
        assert needle not in blob
