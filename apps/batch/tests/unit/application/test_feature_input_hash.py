"""Unit tests for BATCH-011 Feature入力hash算出（仕様書 §16 最小）."""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.feature_input_hash import (
    BATCH_ID,
    DEFAULT_NORMALIZATION_VERSION,
    FEATURE_INPUT_HASH_PHASES,
    MVP_FEATURE_CODES,
    ExistingFeatureAxis,
    FeatureInputHashJob,
    FeatureInputHashRepositories,
    ItemRow,
    ItemSemanticRow,
    QueueRow,
    build_feature_input_payload,
    compute_feature_input_hash,
)
from batch.application.feature_input_hash.__main__ import build_scaffold_demo_job, main
from batch.infrastructure.db import ScaffoldDbWriter

_NOW = datetime(2026, 7, 17, 12, 0, 0, tzinfo=UTC)
_VERSION = "scaffold-semantic-config-v1"


def _queue(
    *,
    qid: str = "igq_1",
    item_id: str = "it_1",
    generation_type: str = "semantic",
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


def _semantic(*, item_id: str = "it_1") -> ItemSemanticRow:
    return ItemSemanticRow(
        item_id=item_id,
        semantic_config_version_id=_VERSION,
        semantic_json={"concepts": [{"concept_code": "formal_refined", "confidence": 0.9}]},
    )


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemRow] | None = None,
    semantics: list[ItemSemanticRow] | None = None,
    features: dict | None = None,
) -> tuple[FeatureInputHashRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = FeatureInputHashRepositories(
        db_writer=db,
        seed_queues=list(queues) if queues is not None else [_queue()],
        seed_items=list(items) if items is not None else [_item()],
        seed_semantics=list(semantics) if semantics is not None else [_semantic()],
        seed_features=dict(features or {}),
    )
    return repos, db


def _complete_axes(digest: str) -> list[ExistingFeatureAxis]:
    return [
        ExistingFeatureAxis(
            feature_code=code,
            feature_input_hash=digest,
            feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
            has_normalized_value=True,
        )
        for code in MVP_FEATURE_CODES
    ]


def test_hash_success_handoff_keeps_processing() -> None:
    repos, db = _repos()
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-ok")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.hashed_count == 1
    assert set(FEATURE_INPUT_HASH_PHASES).issubset(set(result.completed_phases))
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    assert len(repos.handoff_records) == 1
    h = str(repos.handoff_records[0]["feature_input_hash"])
    assert len(h) == 64 and h == h.lower()
    tables = {c["table"] for c in db.write_calls}
    assert "feature_input_hash_handoff" in tables
    assert "item_feature" not in tables
    assert "item_semantic" not in tables
    assert repos.item_feature_write_count == 0
    assert repos.item_semantic_write_count == 0
    assert repos.queue_insert_count == 0


def test_identical_input_same_hash() -> None:
    item = _item()
    sem = _semantic()
    p1 = build_feature_input_payload(
        item=item, semantic=sem, semantic_config_version_id=_VERSION
    )
    p2 = build_feature_input_payload(
        item=item, semantic=sem, semantic_config_version_id=_VERSION
    )
    assert compute_feature_input_hash(p1) == compute_feature_input_hash(p2)


def test_excluded_fields_do_not_change_hash() -> None:
    base = build_feature_input_payload(
        item=_item(price=1000, review_average=4.0, review_count=1),
        semantic=_semantic(),
        semantic_config_version_id=_VERSION,
    )
    other = build_feature_input_payload(
        item=_item(price=99999, review_average=1.0, review_count=999),
        semantic=_semantic(),
        semantic_config_version_id=_VERSION,
    )
    assert compute_feature_input_hash(base) == compute_feature_input_hash(other)
    assert "price" not in base
    assert "review_average" not in base


def test_embedding_queue_excluded() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_e", item_id="it_e", generation_type="embedding", queue_status="queued"),
            _queue(qid="igq_s", item_id="it_s"),
        ],
        items=[_item(item_id="it_e"), _item(item_id="it_s")],
        semantics=[_semantic(item_id="it_e"), _semantic(item_id="it_s")],
    )
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-emb")
    assert result.non_target_skip_count == 1
    assert result.hashed_count == 1
    assert repos.queues["igq_e"]["queue_status"] == "queued"


def test_skip_when_eight_axes_complete() -> None:
    item = _item()
    sem = _semantic()
    digest = compute_feature_input_hash(
        build_feature_input_payload(item=item, semantic=sem, semantic_config_version_id=_VERSION)
    )
    repos, _ = _repos(features={("it_1", _VERSION): _complete_axes(digest)})
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-skip")
    assert result.skipped_count == 1
    assert result.hashed_count == 0
    assert repos.handoff_records == []
    assert repos.queues["igq_1"]["queue_status"] == "skipped"


def test_no_skip_when_axis_missing() -> None:
    item = _item()
    sem = _semantic()
    digest = compute_feature_input_hash(
        build_feature_input_payload(item=item, semantic=sem, semantic_config_version_id=_VERSION)
    )
    axes = _complete_axes(digest)[:7]
    repos, _ = _repos(features={("it_1", _VERSION): axes})
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-noskip")
    assert result.hashed_count == 1
    assert result.skipped_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "processing"


def test_failed_marks_queue_grs_bat_007() -> None:
    repos, _ = _repos()
    result = FeatureInputHashJob(repositories=repos, force_hash_fail=True).run(job_run_id="run-fail")
    assert result.status == "failed"
    assert "GRS-BAT-007" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"
    assert repos.handoff_records == []


def test_missing_semantic_fails() -> None:
    repos, _ = _repos(semantics=[])
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-miss")
    assert result.failed_count == 1
    assert "GRS-DB-001" in result.error_codes


def test_partial_success() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_ok", item_id="it_ok"), _queue(qid="igq_bad", item_id="it_bad")],
        items=[_item(item_id="it_ok"), _item(item_id="it_bad")],
        semantics=[_semantic(item_id="it_ok")],  # it_bad missing semantic
    )
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-partial")
    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.hashed_count == 1
    assert result.failed_count == 1


def test_feature_queued_claim_path() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_f", generation_type="feature", queue_status="queued")],
    )
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-feat")
    assert result.hashed_count == 1
    assert repos.queues["igq_f"]["queue_status"] == "processing"


def test_cli_scaffold_and_exit_3() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0
    assert main(["--job-run-id", "no-db"]) == 3


def test_scaffold_demo_builder() -> None:
    result = build_scaffold_demo_job().run(job_run_id="builder")
    assert result.status == "succeeded"
    assert result.hashed_count == 1


# --- §16 拡充（UT Task） ---


def test_no_skip_when_raw_only_normalized_missing() -> None:
    """§16 No.12: raw のみ（normalized なし）→ handoff + processing 維持。"""

    item = _item()
    sem = _semantic()
    digest = compute_feature_input_hash(
        build_feature_input_payload(item=item, semantic=sem, semantic_config_version_id=_VERSION)
    )
    axes = [
        ExistingFeatureAxis(
            feature_code=code,
            feature_input_hash=digest,
            feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
            has_normalized_value=False,
        )
        for code in MVP_FEATURE_CODES
    ]
    repos, _ = _repos(features={("it_1", _VERSION): axes})
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-raw")
    assert result.hashed_count == 1
    assert result.skipped_count == 0
    assert len(repos.handoff_records) == 1
    assert repos.queues["igq_1"]["queue_status"] == "processing"


def test_no_skip_when_normalization_version_mismatch() -> None:
    """§16 No.12: norm version 不一致 → handoff + processing 維持。"""

    item = _item()
    sem = _semantic()
    digest = compute_feature_input_hash(
        build_feature_input_payload(item=item, semantic=sem, semantic_config_version_id=_VERSION)
    )
    axes = [
        ExistingFeatureAxis(
            feature_code=code,
            feature_input_hash=digest,
            feature_normalization_version_id="old-norm-v0",
            has_normalized_value=True,
        )
        for code in MVP_FEATURE_CODES
    ]
    repos, _ = _repos(features={("it_1", _VERSION): axes})
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-norm")
    assert result.hashed_count == 1
    assert result.skipped_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "processing"


def test_meaning_change_changes_hash() -> None:
    """意味影響項目変更で hash が変わる。"""

    base = build_feature_input_payload(
        item=_item(item_name="A"),
        semantic=_semantic(),
        semantic_config_version_id=_VERSION,
    )
    changed = build_feature_input_payload(
        item=_item(item_name="B"),
        semantic=_semantic(),
        semantic_config_version_id=_VERSION,
    )
    assert compute_feature_input_hash(base) != compute_feature_input_hash(changed)


def test_if_boundary_no_forbidden_writes() -> None:
    """§16 No.4 / No.10: Queue INSERT・item/semantic/feature 書込なし。"""

    repos, db = _repos()
    FeatureInputHashJob(repositories=repos).run(job_run_id="run-boundary")
    assert repos.queue_insert_count == 0
    assert repos.item_write_count == 0
    assert repos.item_semantic_write_count == 0
    assert repos.item_feature_write_count == 0
    forbidden = {"item", "item_semantic", "item_feature"}
    assert forbidden.isdisjoint({c["table"] for c in db.write_calls})
    for call in db.write_calls:
        if call["table"] == "item_generation_queue":
            for row in call["rows"]:
                assert row.get("op") in {
                    "continue_processing",
                    "claim",
                    "update_status",
                    "hash_success_keep_processing",
                }


def test_concurrent_start_rejected_grs_bat_003() -> None:
    from batch.application.job_run import ScaffoldJobRunTracker

    repos, _ = _repos()
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="run-a")
    result = FeatureInputHashJob(repositories=repos, job_run_tracker=tracker).run(
        job_run_id="run-b"
    )
    assert result.status == "failed"
    assert "GRS-BAT-003" in result.error_codes
    assert result.hashed_count == 0


def test_claim_conflict_skips_when_claim_fails() -> None:
    repos, _ = _repos()

    def _fail_claim(*, item_generation_queue_id: str, started_at=None):  # noqa: ANN001
        _ = item_generation_queue_id, started_at
        return None

    repos.claim_or_continue = _fail_claim  # type: ignore[method-assign]
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-conflict")
    assert result.claim_conflict_skip_count == 1
    assert result.hashed_count == 0


def test_source_filter_and_max_items() -> None:
    repos, _ = _repos(
        queues=[
            _queue(qid="igq_a", item_id="it_a"),
            _queue(qid="igq_b", item_id="it_b"),
        ],
        items=[_item(item_id="it_a"), _item(item_id="it_b", source="amazon")],
        semantics=[_semantic(item_id="it_a"), _semantic(item_id="it_b")],
    )
    # amazon は source=rakuten で除外 → 1 件のみ
    result = FeatureInputHashJob(repositories=repos).run(
        job_run_id="run-src", source="rakuten", max_items=10
    )
    assert result.planned_queue_count == 1
    assert result.hashed_count == 1

    repos2, _ = _repos(
        queues=[
            _queue(qid="igq_1", item_id="it_1"),
            _queue(qid="igq_2", item_id="it_2"),
        ],
        items=[_item(item_id="it_1"), _item(item_id="it_2")],
        semantics=[_semantic(item_id="it_1"), _semantic(item_id="it_2")],
    )
    result2 = FeatureInputHashJob(repositories=repos2).run(job_run_id="run-max", max_items=1)
    assert result2.planned_queue_count == 1


def test_fixture_and_logs_have_no_secret_like_values() -> None:
    """§16 No.9: secret らしき文字列なし。"""

    repos, db = _repos()
    result = FeatureInputHashJob(repositories=repos).run(job_run_id="run-sec")
    blob = (
        repr(result)
        + repr(db.write_calls)
        + repr(repos.error_logs)
        + repr(repos.handoff_records)
    ).lower()
    for token in ("password", "api_key", "secret", "bearer ", "sk-", "postgresql://"):
        assert token not in blob
