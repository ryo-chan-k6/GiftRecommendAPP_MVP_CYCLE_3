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
    repos, _ = _repos()
    result = _job(repos).run(job_run_id="run-ok")

    assert result.batch_id == BATCH_ID
    assert result.status == "succeeded"
    assert result.normalized_count == 1
    assert set(FEATURE_NORMALIZATION_PHASES).issubset(set(result.completed_phases))
    assert repos.item_feature_normalized_update_count == len(MVP_FEATURE_CODES)
    assert {r.feature_code for r in repos.normalized_update_rows} == set(MVP_FEATURE_CODES)
    # Queue は processing 維持（後続 Batch が継続）
    assert repos.queues["igq_1"]["queue_status"] == "processing"


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
    for call in db.write_calls:
        if call["table"] == "item_feature":
            for payload in call["rows"]:
                assert "raw_feature_value" not in payload
                assert payload["op"] == "if_db_batch_014_update_normalized"


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
    assert "item_meaning" in {c["table"] for c in db.write_calls}


def test_missing_axis_skips_item_meaning_projection() -> None:
    # project_item_meaning は 8 軸未満で None を返す
    partial = {c: 0.5 for c in MVP_FEATURE_CODES if c != "story_richness"}
    assert project_item_meaning(partial) is None


def test_secondary_path_claims_feature_queued() -> None:
    repos, _ = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="queued")],
    )
    result = _job(repos).run(job_run_id="run-secondary")

    assert result.normalized_count == 1
    assert repos.queues["igq_feat"]["queue_status"] == "processing"


def test_skip_when_normalized_eight_axes_present_same_key() -> None:
    repos, db = _repos(normalized={("it_1", _VERSION): _normalized_axes()})
    result = _job(repos).run(job_run_id="run-skip")

    assert result.skipped_count == 1
    assert result.normalized_count == 0
    assert repos.item_feature_normalized_update_count == 0
    assert repos.item_meaning_upsert_count == 0
    assert repos.queues["igq_1"]["queue_status"] == "skipped"
    assert "item_feature" not in {c["table"] for c in db.write_calls}


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

    tables = {c["table"] for c in db.write_calls}
    assert "item_semantic" not in tables
    assert "normalization_distribution_metric" not in tables
    assert repos.item_semantic_write_count == 0
    assert repos.item_feature_raw_write_count == 0
    assert repos.normalization_distribution_metric_write_count == 0
    assert repos.queue_insert_count == 0
    ops = {
        str(payload.get("op"))
        for c in db.write_calls
        if c["table"] == "item_generation_queue"
        for payload in c["rows"]
    }
    assert "insert" not in ops


def test_normalized_and_meaning_written_together() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-tx")

    tables = [c["table"] for c in db.write_calls]
    assert "item_feature" in tables
    assert "item_meaning" in tables
    # item_feature（normalized）が item_meaning より先に書かれる（同一 persist フェーズ）
    assert tables.index("item_feature") < tables.index("item_meaning")


def test_scaffold_demo_job_succeeds() -> None:
    result = build_scaffold_demo_job().run(job_run_id="demo")
    assert result.status in {"succeeded", "partially_succeeded"}
    assert result.normalized_count == 1
    assert result.item_meaning_upsert_count == 1


def test_cli_scaffold_demo_returns_zero() -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0


def test_cli_without_scaffold_returns_three() -> None:
    assert main(["--job-run-id", "cli"]) == 3


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
