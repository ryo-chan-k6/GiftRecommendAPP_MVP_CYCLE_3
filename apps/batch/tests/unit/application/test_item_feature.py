"""Unit tests for BATCH-012 Item Feature生成（仕様書 §16 最小）."""

from __future__ import annotations

from batch.application.item_feature import (
    BATCH_ID,
    DEFAULT_NORMALIZATION_VERSION,
    ITEM_FEATURE_PHASES,
    MVP_FEATURE_CODES,
    ExistingFeatureAxis,
    FeatureInputHashHandoff,
    ItemFeatureJob,
    ItemFeatureRepositories,
    ItemRow,
    ItemSemanticRow,
    QueueRow,
    build_scaffold_adapter,
)
from batch.application.item_feature.__main__ import build_scaffold_demo_job, main
from batch.config import load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_VERSION = "scaffold-semantic-config-v1"
_HASH = "b" * 64
_RULES = {
    "formal_refined": {"formality": 0.3, "brand_appropriateness": 0.2},
    "emotional_warm": {"emotion": 0.4, "intimacy": 0.2},
}


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
    )


def _item(*, item_id: str = "it_1") -> ItemRow:
    return ItemRow(
        item_id=item_id,
        source="rakuten",
        external_item_code=f"shop:{item_id}",
        item_name="高級ハンドクリーム",
        genre_id="100371",
        genre_name="美容・コスメ",
    )


def _semantic(*, item_id: str = "it_1", concepts: list | None = None) -> ItemSemanticRow:
    if concepts is None:
        concepts = [{"concept_code": "formal_refined", "confidence": 0.9}]
    return ItemSemanticRow(
        item_id=item_id,
        semantic_config_version_id=_VERSION,
        semantic_json={"concepts": concepts},
    )


def _handoff(*, item_id: str = "it_1", feature_input_hash: str = _HASH) -> FeatureInputHashHandoff:
    return FeatureInputHashHandoff(
        item_id=item_id,
        semantic_config_version_id=_VERSION,
        feature_input_hash=feature_input_hash,
    )


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemRow] | None = None,
    semantics: list[ItemSemanticRow] | None = None,
    handoffs: list[FeatureInputHashHandoff] | None = None,
    features: dict | None = None,
) -> tuple[ItemFeatureRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = ItemFeatureRepositories(
        db_writer=db,
        seed_queues=list(queues) if queues is not None else [_queue()],
        seed_items=list(items) if items is not None else [_item()],
        seed_semantics=list(semantics) if semantics is not None else [_semantic()],
        seed_handoffs=list(handoffs) if handoffs is not None else [_handoff()],
        seed_features=dict(features or {}),
        concept_feature_rules=_RULES,
    )
    return repos, db


def _job(repos: ItemFeatureRepositories, *, force_fail: bool = False) -> ItemFeatureJob:
    return ItemFeatureJob(
        repositories=repos,
        generator=build_scaffold_adapter(concept_feature_rules=_RULES, force_fail=force_fail),
    )


def _complete_axes(*, digest: str = _HASH, has_raw: bool = True) -> list[ExistingFeatureAxis]:
    return [
        ExistingFeatureAxis(
            feature_code=code,
            feature_input_hash=digest,
            feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
            has_raw_value=has_raw,
        )
        for code in MVP_FEATURE_CODES
    ]


def test_primary_path_generates_eight_axes_and_keeps_processing() -> None:
    repos, db = _repos()
    result = _job(repos).run(job_run_id="run-ok")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.generated_count == 1
    assert set(ITEM_FEATURE_PHASES).issubset(set(result.completed_phases))
    # 8 軸 Upsert
    assert repos.item_feature_write_count == len(MVP_FEATURE_CODES)
    assert {r.feature_code for r in repos.upsert_rows} == set(MVP_FEATURE_CODES)
    # Queue は processing 維持（BATCH-013 継続）
    assert repos.queues["igq_1"]["queue_status"] == "processing"


def test_upsert_records_raw_hash_and_norm_but_not_normalized() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-raw")

    row = next(r for r in repos.upsert_rows if r.feature_code == "formality")
    assert row.feature_input_hash == _HASH
    assert row.feature_normalization_version_id == DEFAULT_NORMALIZATION_VERSION
    assert 0.0 <= row.raw_feature_value <= 1.0
    # normalized_feature_value は Upsert payload に含めない（BATCH-013 責務）
    for call in db.write_calls:
        if call["table"] == "item_feature":
            for payload in call["rows"]:
                assert "normalized_feature_value" not in payload


def test_secondary_path_claims_feature_queued() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="queued")],
    )
    result = _job(repos).run(job_run_id="run-secondary")

    assert result.generated_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "processing"


def test_concept_zero_yields_baseline_half() -> None:
    repos, _ = _repos(semantics=[_semantic(concepts=[])])
    _job(repos).run(job_run_id="run-zero")

    assert repos.item_feature_write_count == len(MVP_FEATURE_CODES)
    assert all(abs(r.raw_feature_value - 0.5) < 1e-9 for r in repos.upsert_rows)


def test_skip_when_eight_axes_present_same_key() -> None:
    features = {("it_1", _VERSION): _complete_axes()}
    repos, db = _repos(features=features)
    result = _job(repos).run(job_run_id="run-skip")

    assert result.skipped_count == 1
    assert result.generated_count == 0
    assert repos.item_feature_write_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert "item_feature" not in {c["table"] for c in db.write_calls}


def test_skip_not_applied_on_hash_mismatch() -> None:
    features = {("it_1", _VERSION): _complete_axes(digest="c" * 64)}
    repos, _ = _repos(features=features)
    result = _job(repos).run(job_run_id="run-noskip")

    assert result.generated_count == 1
    assert result.skipped_count == 0


def test_skip_ignores_missing_normalized_value() -> None:
    # raw はあるが normalized 相当は無関係（has_raw_value=True）→ skip 成立
    features = {("it_1", _VERSION): _complete_axes()}
    repos, _ = _repos(features=features)
    result = _job(repos).run(job_run_id="run-skip-raw-only")
    assert result.skipped_count == 1


def test_missing_handoff_fails_with_grs_bat_008() -> None:
    repos, _ = _repos(handoffs=[])
    result = _job(repos).run(job_run_id="run-nohandoff")

    assert result.status == "failed"
    assert "GRS-BAT-008" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_invalid_hash_format_fails() -> None:
    repos, _ = _repos(handoffs=[_handoff(feature_input_hash="not-a-hash")])
    result = _job(repos).run(job_run_id="run-badhash")

    assert result.status == "failed"
    assert "GRS-BAT-008" in result.error_codes


def test_generator_failure_marks_queue_failed() -> None:
    repos, _ = _repos()
    result = _job(repos, force_fail=True).run(job_run_id="run-genfail")

    assert result.status == "failed"
    assert "GRS-BAT-008" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_embedding_queue_excluded() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_emb", generation_type="embedding", queue_status="queued")],
        handoffs=[],
    )
    result = _job(repos).run(job_run_id="run-emb")

    assert result.generated_count == 0
    assert result.non_target_skip_count == 1
    assert result.status == "succeeded"


def test_does_not_touch_item_semantic_or_insert_queue() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-boundary")

    tables = {c["table"] for c in db.write_calls}
    assert "item_semantic" not in tables
    assert repos.item_semantic_write_count == 0
    assert repos.queue_insert_count == 0
    # Queue 書込は status update のみ
    ops = {
        str(payload.get("op"))
        for c in db.write_calls
        if c["table"] == "item_generation_queue"
        for payload in c["rows"]
    }
    assert "insert" not in ops


def test_no_hash_recomputation_uses_handoff_value() -> None:
    repos, _ = _repos(handoffs=[_handoff(feature_input_hash=_HASH)])
    _job(repos).run(job_run_id="run-handoff")

    assert all(r.feature_input_hash == _HASH for r in repos.upsert_rows)


def test_scaffold_demo_job_succeeds() -> None:
    result = build_scaffold_demo_job().run(job_run_id="demo")
    assert result.status in {"succeeded", "partially_succeeded"}
    assert result.generated_count == 1


def test_cli_scaffold_demo_returns_zero() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0


def test_cli_without_scaffold_returns_three() -> None:
    assert main(["--job-run-id", "cli"]) == 3


def test_config_reads_item_feature_fields() -> None:
    settings = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "BATCH_ITEM_FEATURE_MAX_ITEMS": "320",
            "BATCH_ITEM_FEATURE_SOURCE": "rakuten",
            "BATCH_ITEM_FEATURE_QUEUE_BATCH_SIZE": "60",
        }
    )
    assert settings.batch_item_feature_max_items == 320
    assert settings.batch_item_feature_source == "rakuten"
    assert settings.batch_item_feature_queue_batch_size == 60
    assert "320" in repr(settings)


def test_scaffold_settings_include_item_feature_defaults() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_item_feature_max_items == 1000
    assert settings.batch_item_feature_source == "rakuten"
    assert settings.batch_item_feature_queue_batch_size == 100
