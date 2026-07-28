"""Unit tests for BATCH-013 Feature正規化（仕様書 §16 最小）."""

from __future__ import annotations

import math

from batch.application.feature_normalization import (
    BATCH_ID,
    DEFAULT_CENTER_FEATURE,
    DEFAULT_K_FEATURE,
    DEFAULT_NORMALIZATION_VERSION,
    FEATURE_NORMALIZATION_PHASES,
    MVP_FEATURE_CODES,
    SOCIAL_FEATURE_CODES,
    SYMBOLIC_FEATURE_CODES,
    ExistingNormalizedAxis,
    FeatureNormalizationJob,
    FeatureNormalizationRepositories,
    ItemRow,
    QueueRow,
    RawFeatureAxis,
    build_scaffold_adapter,
    normalize_sigmoid,
    project_item_meaning,
)
from batch.application.feature_normalization.__main__ import build_scaffold_demo_job, main
from batch.config import load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_VERSION = "scaffold-semantic-config-v1"
_HASH = "b" * 64
_RAW = {
    "formality": 0.8,
    "safety": 0.7,
    "brand_appropriateness": 0.6,
    "emotion": 0.75,
    "novelty": 0.4,
    "intimacy": 0.55,
    "symbolic_identity": 0.5,
    "story_richness": 0.65,
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
    return ItemRow(item_id=item_id, source="rakuten", external_item_code=f"shop:{item_id}")


def _raw_axes(
    *,
    digest: str = _HASH,
    version: str = DEFAULT_NORMALIZATION_VERSION,
    values: dict[str, float] | None = None,
    drop: str | None = None,
) -> list[RawFeatureAxis]:
    src = values or _RAW
    axes: list[RawFeatureAxis] = []
    for code in MVP_FEATURE_CODES:
        if code == drop:
            continue
        axes.append(
            RawFeatureAxis(
                feature_code=code,
                feature_input_hash=digest,
                feature_normalization_version_id=version,
                raw_feature_value=src[code],
            )
        )
    return axes


def _normalized_axes(
    *, digest: str = _HASH, version: str = DEFAULT_NORMALIZATION_VERSION
) -> list[ExistingNormalizedAxis]:
    return [
        ExistingNormalizedAxis(
            feature_code=code,
            feature_input_hash=digest,
            feature_normalization_version_id=version,
        )
        for code in MVP_FEATURE_CODES
    ]


def _repos(
    *,
    queues: list[QueueRow] | None = None,
    items: list[ItemRow] | None = None,
    raw_features: dict | None = None,
    normalized: dict | None = None,
    config_versions: dict | None = None,
) -> tuple[FeatureNormalizationRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = FeatureNormalizationRepositories(
        db_writer=db,
        seed_queues=list(queues) if queues is not None else [_queue()],
        seed_items=list(items) if items is not None else [_item()],
        seed_raw_features=(
            dict(raw_features) if raw_features is not None else {("it_1", _VERSION): _raw_axes()}
        ),
        seed_normalized=dict(normalized or {}),
        seed_config_versions=(
            dict(config_versions) if config_versions is not None else {"it_1": _VERSION}
        ),
    )
    return repos, db


def _job(
    repos: FeatureNormalizationRepositories, *, force_fail: bool = False
) -> FeatureNormalizationJob:
    return FeatureNormalizationJob(
        repositories=repos,
        normalizer=build_scaffold_adapter(force_fail=force_fail),
    )


def test_primary_path_normalizes_eight_axes_and_keeps_processing() -> None:
    repos, db = _repos()
    result = _job(repos).run(job_run_id="run-ok")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.normalized_count == 1
    assert set(FEATURE_NORMALIZATION_PHASES).issubset(set(result.completed_phases))
    assert repos.item_feature_normalized_update_count == len(MVP_FEATURE_CODES)
    assert {r.feature_code for r in repos.normalized_update_rows} == set(MVP_FEATURE_CODES)
    # Queue は processing 維持（後続 Batch が継続）
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    # continue / keep_processing は DB no-op。normalized は update_rows。
    assert db.write_calls == []
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}
    feature_updates = [c for c in db.update_calls if c["table"] == "item_feature"]
    assert len(feature_updates) == len(MVP_FEATURE_CODES)
    meaning_upserts = [c for c in db.upsert_calls if c["table"] == "item_meaning"]
    assert len(meaning_upserts) == 1
    assert meaning_upserts[0]["conflict_columns"] == ("item_id", "semantic_config_version_id")
    assert meaning_upserts[0]["update_columns"] == (
        "feature_normalization_version_id",
        "item_social",
        "item_symbolic",
        "generated_at",
    )


def test_sigmoid_formula_matches_feature_rule_definition() -> None:
    # Featureルール定義書 §14.2/§14.3: sigmoid(k*(raw-center)), center=0.5, k=4.0
    repos, _ = _repos()
    _job(repos).run(job_run_id="run-sigmoid")

    row = next(r for r in repos.normalized_update_rows if r.feature_code == "formality")
    expected = normalize_sigmoid(_RAW["formality"], center=DEFAULT_CENTER_FEATURE, k=DEFAULT_K_FEATURE)
    assert math.isclose(row.normalized_feature_value, expected, rel_tol=1e-9)


def test_neutral_raw_maps_to_half() -> None:
    values = {code: 0.5 for code in MVP_FEATURE_CODES}
    repos, _ = _repos(raw_features={("it_1", _VERSION): _raw_axes(values=values)})
    _job(repos).run(job_run_id="run-neutral")

    for row in repos.normalized_update_rows:
        assert math.isclose(row.normalized_feature_value, 0.5, abs_tol=1e-9)


def test_normalized_values_within_unit_range() -> None:
    repos, _ = _repos()
    _job(repos).run(job_run_id="run-range")
    for row in repos.normalized_update_rows:
        assert 0.0 <= row.normalized_feature_value <= 1.0


def test_does_not_write_raw_feature_value() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-raw-unchanged")

    assert repos.item_feature_raw_write_count == 0
    assert db.write_calls == []
    for call in db.update_calls:
        if call["table"] == "item_feature":
            assert set(call["set_values"].keys()) == {"normalized_feature_value"}
            assert "raw_feature_value" not in call["set_values"]
            assert "op" not in call["set_values"]
    for call in db.upsert_calls:
        if call["table"] == "item_meaning":
            for payload in call["rows"]:
                assert "raw_feature_value" not in payload
                assert "op" not in payload


def test_item_meaning_upsert_projects_social_and_symbolic() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-meaning")

    assert repos.item_meaning_upsert_count == 1
    meaning = repos.item_meaning_rows[0]
    norm = {r.feature_code: r.normalized_feature_value for r in repos.normalized_update_rows}
    exp_social = sum(norm[c] for c in SOCIAL_FEATURE_CODES) / len(SOCIAL_FEATURE_CODES)
    exp_symbolic = sum(norm[c] for c in SYMBOLIC_FEATURE_CODES) / len(SYMBOLIC_FEATURE_CODES)
    assert math.isclose(meaning.item_social, exp_social, rel_tol=1e-9)
    assert math.isclose(meaning.item_symbolic, exp_symbolic, rel_tol=1e-9)
    assert meaning.feature_normalization_version_id == DEFAULT_NORMALIZATION_VERSION
    meaning_upserts = [c for c in db.upsert_calls if c["table"] == "item_meaning"]
    assert len(meaning_upserts) == 1
    payload = meaning_upserts[0]["rows"][0]
    assert payload["feature_normalization_version_id"] == DEFAULT_NORMALIZATION_VERSION
    assert "op" not in payload
    assert "item_meaning_id" not in payload


def test_missing_axis_skips_item_meaning_projection() -> None:
    # project_item_meaning は 8 軸未満で None を返す
    partial = {c: 0.5 for c in MVP_FEATURE_CODES if c != "story_richness"}
    assert project_item_meaning(partial) is None


def test_secondary_path_claims_feature_queued() -> None:
    repos, db = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="queued")],
    )
    result = _job(repos).run(job_run_id="run-secondary")

    assert result.normalized_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "processing"
    claim_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "processing"
    ]
    assert len(claim_updates) == 1
    assert claim_updates[0]["equals"] == (
        ("item_generation_queue_id", "igq_feat"),
        ("queue_status", "queued"),
        ("generation_type", "feature"),
    )


def test_skip_when_normalized_eight_axes_present_same_key() -> None:
    repos, db = _repos(normalized={("it_1", _VERSION): _normalized_axes()})
    result = _job(repos).run(job_run_id="run-skip")

    assert result.skipped_count == 1
    assert result.normalized_count == 0
    assert repos.item_feature_normalized_update_count == 0
    assert repos.item_meaning_upsert_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert "item_feature" not in {c["table"] for c in db.update_calls}
    assert "item_meaning" not in {c["table"] for c in db.upsert_calls}


def test_skip_not_applied_on_version_mismatch() -> None:
    repos, _ = _repos(normalized={("it_1", _VERSION): _normalized_axes(version="old-v0")})
    result = _job(repos).run(job_run_id="run-noskip")

    assert result.normalized_count == 1
    assert result.skipped_count == 0


def test_missing_raw_axis_fails_with_grs_val() -> None:
    repos, _ = _repos(raw_features={("it_1", _VERSION): _raw_axes(drop="safety")})
    result = _job(repos).run(job_run_id="run-missing-raw")

    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_inconsistent_raw_hash_fails() -> None:
    axes = _raw_axes()
    axes[0] = RawFeatureAxis(
        feature_code=axes[0].feature_code,
        feature_input_hash="c" * 64,
        feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
        raw_feature_value=axes[0].raw_feature_value,
    )
    repos, _ = _repos(raw_features={("it_1", _VERSION): axes})
    result = _job(repos).run(job_run_id="run-badhash")

    assert result.status == "failed"
    assert "GRS-VAL-002" in result.error_codes


def test_unresolved_config_version_fails() -> None:
    repos, _ = _repos(config_versions={})
    result = _job(repos).run(job_run_id="run-nocfg")

    assert result.status == "failed"
    assert "GRS-CFG-001" in result.error_codes


def test_normalizer_failure_marks_queue_failed() -> None:
    repos, _ = _repos()
    result = _job(repos, force_fail=True).run(job_run_id="run-normfail")

    assert result.status == "failed"
    assert "GRS-BAT-008" in result.error_codes
    assert repos.queues["igq_1"]["queue_status"] == "failed"


def test_embedding_queue_excluded() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_emb", generation_type="embedding", queue_status="queued")],
        raw_features={},
        config_versions={},
    )
    result = _job(repos).run(job_run_id="run-emb")

    assert result.normalized_count == 0
    assert result.non_target_skip_count == 1
    assert result.status == "succeeded"


def test_does_not_touch_item_semantic_or_raw_or_distribution_metric() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-boundary")

    update_tables = {c["table"] for c in db.update_calls}
    upsert_tables = {c["table"] for c in db.upsert_calls}
    write_tables = {c["table"] for c in db.write_calls}
    assert "item_semantic" not in update_tables | upsert_tables | write_tables
    assert "normalization_distribution_metric" not in update_tables | upsert_tables | write_tables
    assert repos.item_semantic_write_count == 0
    assert repos.item_feature_raw_write_count == 0
    assert repos.normalization_distribution_metric_write_count == 0
    assert repos.queue_insert_count == 0
    assert db.write_calls == []
    for call in db.update_calls:
        assert "op" not in call["set_values"]
    for call in db.upsert_calls:
        for payload in call["rows"]:
            assert "op" not in payload


def test_normalized_and_meaning_written_together() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-tx")

    feature_updates = [c for c in db.update_calls if c["table"] == "item_feature"]
    meaning_upserts = [c for c in db.upsert_calls if c["table"] == "item_meaning"]
    assert len(feature_updates) == len(MVP_FEATURE_CODES)
    assert len(meaning_upserts) == 1
    # item_feature（normalized）が item_meaning より先に書かれる（同一 persist / 同一 tx）
    assert len(db.transaction_calls) == 1
    assert feature_updates
    assert meaning_upserts
    for call in feature_updates:
        assert call["equals"][0][0] == "item_id"
        assert set(call["set_values"].keys()) == {"normalized_feature_value"}
    for call in meaning_upserts:
        for payload in call["rows"]:
            assert "op" not in payload
            assert "raw_feature_value" not in payload
            assert "feature_normalization_version_id" in payload


def test_primary_path_uses_transaction_for_persist() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-tx-wrap")

    assert len(db.transaction_calls) == 1
    feature_updates = [c for c in db.update_calls if c["table"] == "item_feature"]
    meaning_upserts = [c for c in db.upsert_calls if c["table"] == "item_meaning"]
    assert len(feature_updates) == len(MVP_FEATURE_CODES)
    assert len(meaning_upserts) == 1


def test_scaffold_demo_job_succeeds() -> None:
    result = build_scaffold_demo_job().run(job_run_id="demo")
    assert result.status in {"succeeded", "partially_succeeded"}
    assert result.normalized_count == 1
    assert result.item_meaning_upsert_count == 1


def test_cli_scaffold_demo_returns_zero() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.feature_normalization import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "cli"]) == 2


def test_list_load_raw_and_resolve_config_via_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_generation_queue",
        (
            {
                "item_generation_queue_id": "igq_sem",
                "item_id": "it_1",
                "generation_type": "semantic",
                "queue_status": "processing",
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
                "external_item_code": "shop:a",
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
            },
        ),
    )
    reader.seed(
        "item_feature",
        tuple(
            {
                "item_id": "it_1",
                "semantic_config_version_id": _VERSION,
                "feature_code": code,
                "feature_input_hash": _HASH,
                "feature_normalization_version_id": DEFAULT_NORMALIZATION_VERSION,
                "raw_feature_value": 0.5,
                "normalized_feature_value": None,
            }
            for code in MVP_FEATURE_CODES
        ),
    )
    repos = FeatureNormalizationRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    targets, _ = repos.list_target_queues(max_items=10)
    assert [q.item_generation_queue_id for q in targets] == ["igq_sem"]
    assert repos.resolve_semantic_config_version(item_id="it_1") == _VERSION
    raw = repos.load_raw_features(item_id="it_1", semantic_config_version_id=_VERSION)
    assert len(raw) == len(MVP_FEATURE_CODES)
    assert raw[0].feature_input_hash == _HASH


def test_if_shared_003_uses_in_process_adapter_not_http() -> None:
    """§16 No.3: IF-SHARED-003 は in-process Python import で MOD-BATCH-034 相当を呼び出す。"""
    from batch.application.feature_normalization.adapter import (
        FeatureNormalizerPort,
        ScaffoldFeatureNormalizerAdapter,
    )
    from batch.application.feature_normalization.models import (
        NormalizationParams,
        NormalizeContext,
    )

    adapter = build_scaffold_adapter()
    assert isinstance(adapter, ScaffoldFeatureNormalizerAdapter)
    port: FeatureNormalizerPort = adapter
    assert callable(port.normalize_features)
    assert not hasattr(adapter, "base_url")
    assert not hasattr(adapter, "session")
    assert not hasattr(adapter, "http_client")

    ctx = NormalizeContext(
        item_id="it_1",
        semantic_config_version_id=_VERSION,
        feature_input_hash=_HASH,
        feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
        params=NormalizationParams(),
        raw_axes=tuple(_raw_axes()),
        trace_id="test-trace",
    )
    result = adapter.normalize_features(ctx)
    assert result.status == "normalized"
    assert len(result.normalized) == len(MVP_FEATURE_CODES)


def test_config_reads_feature_normalization_fields() -> None:
    settings = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "BATCH_FEATURE_NORMALIZATION_MAX_ITEMS": "240",
            "BATCH_FEATURE_NORMALIZATION_SOURCE": "rakuten",
            "BATCH_FEATURE_NORMALIZATION_QUEUE_BATCH_SIZE": "48",
        }
    )
    assert settings.batch_feature_normalization_max_items == 240
    assert settings.batch_feature_normalization_source == "rakuten"
    assert settings.batch_feature_normalization_queue_batch_size == 48
    assert "240" in repr(settings)


def test_scaffold_settings_include_feature_normalization_defaults() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_feature_normalization_max_items == 1000
    assert settings.batch_feature_normalization_source == "rakuten"
    assert settings.batch_feature_normalization_queue_batch_size == 100


# --- §16 カバレッジ拡充（単体テスト Task #1462） ---


def test_phase_order_follows_spec_section_8_2() -> None:
    """§8.2: Phase が仕様書順（plan→…→finalize）で完走する。"""
    repos, _ = _repos()
    result = _job(repos).run(job_run_id="run-phase-order")
    # 期待順序の部分列として現れる
    idx = [result.completed_phases.index(p) for p in FEATURE_NORMALIZATION_PHASES]
    assert idx == sorted(idx)
    assert result.completed_phases[0] == "plan"
    assert result.completed_phases[-1] == "finalize"


def test_skip_not_applied_on_normalized_hash_mismatch() -> None:
    """§16 No.13: normalized の hash が現行 hash と不一致なら skip しない。"""
    repos, _ = _repos(normalized={("it_1", _VERSION): _normalized_axes(digest="d" * 64)})
    result = _job(repos).run(job_run_id="run-hash-noskip")
    assert result.normalized_count == 1
    assert result.skipped_count == 0


def test_skip_not_applied_when_normalized_axes_incomplete() -> None:
    """§16 No.13: normalized が 8 軸未満なら skip しない。"""
    axes = _normalized_axes()[:-1]  # 7 軸のみ
    repos, _ = _repos(normalized={("it_1", _VERSION): axes})
    result = _job(repos).run(job_run_id="run-incomplete-noskip")
    assert result.normalized_count == 1
    assert result.skipped_count == 0


def test_skip_not_applied_when_normalized_value_missing() -> None:
    """§16 No.13: normalized 値が無効（has_normalized_value=False）なら skip しない。"""
    axes = [
        ExistingNormalizedAxis(
            feature_code=code,
            feature_input_hash=_HASH,
            feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
            has_normalized_value=(code != "safety"),
        )
        for code in MVP_FEATURE_CODES
    ]
    repos, _ = _repos(normalized={("it_1", _VERSION): axes})
    result = _job(repos).run(job_run_id="run-nullnorm-noskip")
    assert result.normalized_count == 1
    assert result.skipped_count == 0


def test_queue_marked_skipped_writes_status_not_keep_processing() -> None:
    """§16 No.14: skip 時は queue_status=skipped（keep_processing でない）。"""
    repos, db = _repos(normalized={("it_1", _VERSION): _normalized_axes()})
    _job(repos).run(job_run_id="run-skip-queue")
    skip_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "skipped"
    ]
    assert len(skip_updates) == 1
    assert all("op" not in c["set_values"] for c in db.update_calls)
    assert db.write_calls == []


def test_queue_keep_processing_on_success() -> None:
    """§16 No.14: 成功時は processing 維持（DB no-op）。"""
    repos, db = _repos()
    _job(repos).run(job_run_id="run-keep")
    assert repos.queues["igq_1"]["queue_status"] == "processing"
    # keep_processing は DB no-op（偽 op=normalize_success_keep_processing 廃止）
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}
    assert db.write_calls == []


def test_batch_already_running_guard() -> None:
    """§13: 多重起動は GRS-BAT-003 で拒否する。"""
    from batch.application.job_run import ScaffoldJobRunTracker

    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="prev-running")
    repos, _ = _repos()
    job = FeatureNormalizationJob(
        repositories=repos,
        normalizer=build_scaffold_adapter(),
        job_run_tracker=tracker,
    )
    result = job.run(job_run_id="run-dup")
    assert "GRS-BAT-003" in result.error_codes
    assert result.normalized_count == 0


def test_partial_success_across_multiple_items() -> None:
    """§16 No.17 / §11: 1 件成功 + 1 件 raw 欠損で partially_succeeded。"""
    queues = [
        _queue(qid="igq_ok", item_id="it_ok"),
        _queue(qid="igq_ng", item_id="it_ng"),
    ]
    items = [_item(item_id="it_ok"), _item(item_id="it_ng")]
    raw = {
        ("it_ok", _VERSION): _raw_axes(),
        ("it_ng", _VERSION): _raw_axes(drop="emotion"),
    }
    repos, _ = _repos(
        queues=queues,
        items=items,
        raw_features=raw,
        config_versions={"it_ok": _VERSION, "it_ng": _VERSION},
    )
    result = _job(repos).run(job_run_id="run-partial")
    assert result.status == "partially_succeeded"
    assert result.normalized_count == 1
    assert result.failed_count == 1
    assert "GRS-BAT-002" in result.error_codes


def test_item_ids_filter_selects_subset() -> None:
    """§6.4 / §9.1: item_ids 指定で対象を絞り込める。"""
    queues = [
        _queue(qid="igq_a", item_id="it_a"),
        _queue(qid="igq_b", item_id="it_b"),
    ]
    items = [_item(item_id="it_a"), _item(item_id="it_b")]
    raw = {("it_a", _VERSION): _raw_axes(), ("it_b", _VERSION): _raw_axes()}
    repos, _ = _repos(
        queues=queues,
        items=items,
        raw_features=raw,
        config_versions={"it_a": _VERSION, "it_b": _VERSION},
    )
    result = _job(repos).run(job_run_id="run-filter", item_ids=["it_a"])
    assert result.planned_queue_count == 1
    assert result.normalized_count == 1
    assert repos.queues["igq_b"]["queue_status"] == "processing"  # 未処理（seed のまま）


def test_fixed_sigmoid_does_not_saturate_within_raw_domain() -> None:
    """§14: raw∈[0,1]・center=0.5・k=4.0 では出力は sigmoid(±2)=約0.12〜0.88 に収まり飽和しない。"""
    values = {code: 1.0 for code in MVP_FEATURE_CODES}
    repos, _ = _repos(raw_features={("it_1", _VERSION): _raw_axes(values=values)})
    result = _job(repos).run(job_run_id="run-saturate")
    # 固定 sigmoid（k=4）は raw=1.0 でも sigmoid(2)≈0.881 で飽和境界(0.99)に達しない
    assert result.saturate_count == 0
    for row in repos.normalized_update_rows:
        assert 0.0 < row.normalized_feature_value < 1.0


def test_normalized_update_preserves_idempotent_key() -> None:
    """§10.1: normalized UPDATE は raw と同一の 5 列冪等キーを保持する。"""
    repos, db = _repos()
    _job(repos).run(job_run_id="run-key")
    for row in repos.normalized_update_rows:
        assert row.feature_input_hash == _HASH
        assert row.feature_normalization_version_id == DEFAULT_NORMALIZATION_VERSION
        assert row.semantic_config_version_id == _VERSION
    for call in db.update_calls:
        if call["table"] != "item_feature":
            continue
        equals_cols = tuple(col for col, _ in call["equals"])
        assert equals_cols == (
            "item_id",
            "semantic_config_version_id",
            "feature_code",
            "feature_input_hash",
            "feature_normalization_version_id",
        )


def test_no_secret_like_values_in_db_writes() -> None:
    """§15: DB 書込 payload に接続情報・認証情報を含めない。"""
    repos, db = _repos()
    _job(repos).run(job_run_id="run-secret")
    forbidden = ("password", "secret", "token", "postgres://", "postgresql://", "@")
    payloads: list[object] = []
    for call in db.write_calls:
        payloads.extend(call["rows"])
    for call in db.update_calls:
        payloads.append(call["set_values"])
        payloads.append(dict(call["equals"]))
    for call in db.upsert_calls:
        payloads.extend(call["rows"])
    for payload in payloads:
        values = payload.values() if isinstance(payload, dict) else [payload]
        for value in values:
            text = str(value).lower()
            for needle in forbidden:
                assert needle not in text


def test_claim_conflict_returns_none_when_rows_affected_zero() -> None:
    """feature claim で rows_affected==0 なら None（競合 skip）。"""
    from batch.infrastructure.db.writer import DbWriteResult

    repos, db = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="queued")],
    )
    original = db.update_rows

    def _zero_claim(
        table: str,
        *,
        set_values: dict[str, object],
        equals: tuple[tuple[str, object], ...],
    ) -> DbWriteResult:
        if table == "item_generation_queue" and set_values.get("queue_status") == "processing":
            return DbWriteResult(rows_affected=0, table=table)
        return original(table, set_values=set_values, equals=equals)

    db.update_rows = _zero_claim  # type: ignore[method-assign]
    claimed = repos.claim_or_continue(item_generation_queue_id="igq_feat")
    assert claimed is None
    assert repos.queues["igq_feat"]["queue_status"] == "queued"