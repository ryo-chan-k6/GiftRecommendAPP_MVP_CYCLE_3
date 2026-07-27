"""Unit tests for BATCH-016 分布メトリクス集計（仕様書 §16 最小 / scaffold-first）.

fixture/mock のみ。実 DB / secret に依存しない。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.distribution_metrics import (
    BATCH_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION,
    DISTRIBUTION_METRICS_PHASES,
    MVP_FEATURE_CODES,
    PHASE_FEATURE_DISTRIBUTION_RECORDED,
    DistributionMetricsJob,
    DistributionMetricsRepositories,
    ItemEmbeddingRow,
    ItemFeatureRow,
    ItemMeaningRow,
    UserMeaningRow,
    compute_distribution_stats,
    resolve_scope,
)
from batch.application.distribution_metrics.__main__ import build_scaffold_demo_job, main
from batch.application.job_run import ScaffoldJobRunTracker
from batch.config import load_batch_settings, scaffold_batch_settings
from batch.infrastructure.db import ScaffoldDbWriter

_VERSION = DEFAULT_SEMANTIC_CONFIG_VERSION
_NORM_VERSION = "scaffold-feature-normalization-v1"
_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=UTC)
_HASH = "a" * 64

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
_NORM = {
    "formality": 0.82,
    "safety": 0.71,
    "brand_appropriateness": 0.62,
    "emotion": 0.77,
    "novelty": 0.42,
    "intimacy": 0.56,
    "symbolic_identity": 0.51,
    "story_richness": 0.66,
}


def _features(*, items: tuple[str, ...] = ("it_1", "it_2")) -> list[ItemFeatureRow]:
    rows: list[ItemFeatureRow] = []
    for idx, item_id in enumerate(items):
        scale = 1.0 - (idx * 0.05)
        for code in MVP_FEATURE_CODES:
            rows.append(
                ItemFeatureRow(
                    item_id=item_id,
                    semantic_config_version_id=_VERSION,
                    feature_code=code,
                    raw_feature_value=_RAW[code] * scale,
                    normalized_feature_value=_NORM[code] * scale,
                    feature_normalization_version_id=_NORM_VERSION,
                )
            )
    return rows


def _meanings(*, items: tuple[str, ...] = ("it_1", "it_2")) -> list[ItemMeaningRow]:
    return [
        ItemMeaningRow(
            item_id=item_id,
            semantic_config_version_id=_VERSION,
            item_social=0.7 - i * 0.05,
            item_symbolic=0.55 - i * 0.05,
            feature_normalization_version_id=_NORM_VERSION,
        )
        for i, item_id in enumerate(items)
    ]


def _user_meanings() -> list[UserMeaningRow]:
    return [
        UserMeaningRow(
            user_id="usr_1",
            semantic_config_version_id=_VERSION,
            user_social=0.6,
            user_symbolic=0.45,
            lambda_ctx=0.5,
            feature_normalization_version_id=_NORM_VERSION,
        ),
        UserMeaningRow(
            user_id="usr_2",
            semantic_config_version_id=_VERSION,
            user_social=0.55,
            user_symbolic=0.4,
            lambda_ctx=0.48,
            feature_normalization_version_id=_NORM_VERSION,
        ),
    ]


def _embeddings() -> list[ItemEmbeddingRow]:
    return [
        ItemEmbeddingRow(
            item_id="it_1",
            model_version_id="scaffold-embedding-model-v1",
            embedding_input_hash=_HASH,
        )
    ]


def _repos(
    *,
    features: list[ItemFeatureRow] | None = None,
    meanings: list[ItemMeaningRow] | None = None,
    user_meanings: list[UserMeaningRow] | None = None,
    embeddings: list[ItemEmbeddingRow] | None = None,
) -> tuple[DistributionMetricsRepositories, ScaffoldDbWriter]:
    db = ScaffoldDbWriter()
    repos = DistributionMetricsRepositories(
        db_writer=db,
        seed_item_features=features if features is not None else _features(),
        seed_item_meanings=meanings if meanings is not None else _meanings(),
        seed_user_meanings=user_meanings if user_meanings is not None else _user_meanings(),
        seed_item_embeddings=embeddings if embeddings is not None else _embeddings(),
    )
    return repos, db


def _run(
    repos: DistributionMetricsRepositories,
    *,
    job_run_id: str = "run-1",
    trigger_mode: str = "dispatch",
    include_item_embedding: bool = False,
    include_user_meaning: bool = False,
    aggregation_scope: str | None = None,
    tracker: ScaffoldJobRunTracker | None = None,
):
    job = DistributionMetricsJob(
        repositories=repos,
        job_run_tracker=tracker,
    )
    return job.run(
        job_run_id=job_run_id,
        trigger_mode=trigger_mode,
        semantic_config_version_id=_VERSION,
        aggregation_scope=aggregation_scope,
        include_item_embedding=include_item_embedding,
        include_user_meaning=include_user_meaning,
        now=_NOW,
    )


def test_happy_path_upserts_three_metric_tables_and_single_phase_log() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.status == "succeeded"
    assert result.feature_metric_upsert_count > 0
    assert result.meaning_metric_upsert_count > 0
    assert result.normalization_metric_upsert_count > 0

    tables = {c["table"] for c in db.write_calls}
    assert "feature_distribution_metric" in tables
    assert "meaning_distribution_metric" in tables
    assert "normalization_distribution_metric" in tables

    phase_names = [p["phase"] for p in repos.phase_logs]
    assert phase_names == [PHASE_FEATURE_DISTRIBUTION_RECORDED]
    assert repos.phase_logs[0]["status"] == "succeeded"
    assert "meaning_distribution_metric_recorded" not in phase_names
    assert "normalization_distribution_metric_recorded" not in phase_names

    # 論理 Phase は仕様書 §8.2 順
    idx = [result.completed_phases.index(p) for p in DISTRIBUTION_METRICS_PHASES]
    assert idx == sorted(idx)


def test_adjacent_if_non_write_counters_stay_zero() -> None:
    repos, db = _repos()
    result = _run(repos)

    assert result.item_feature_write_count == 0
    assert result.item_meaning_write_count == 0
    assert result.item_embedding_write_count == 0
    assert result.embedding_hash_write_count == 0
    assert repos.item_feature_write_count == 0
    assert repos.item_meaning_write_count == 0
    assert repos.item_embedding_write_count == 0
    assert repos.embedding_hash_write_count == 0

    forbidden = {
        "item_feature",
        "item_meaning",
        "item_embedding",
        "embedding_input_hash",
    }
    written = {c["table"] for c in db.write_calls}
    assert written.isdisjoint(forbidden)

    for call in db.write_calls:
        for row in call["rows"]:
            assert row.get("op") == "if_db_batch_016_upsert"


def test_embedding_and_user_meaning_skipped_when_flags_off() -> None:
    repos, _ = _repos()
    result = _run(repos, include_item_embedding=False, include_user_meaning=False)

    assert result.include_item_embedding is False
    assert result.include_user_meaning is False
    assert result.item_embedding_read_count == 0
    assert result.user_meaning_aggregated is False
    assert all(r.entity_type == "item" for r in repos.meaning_metric_rows)


def test_user_meaning_aggregated_when_flag_on() -> None:
    repos, _ = _repos()
    result = _run(repos, include_user_meaning=True)

    assert result.user_meaning_aggregated is True
    user_rows = [r for r in repos.meaning_metric_rows if r.entity_type == "user"]
    assert user_rows
    layers = {r.value_layer for r in user_rows}
    assert "social" in layers
    assert "symbolic" in layers
    assert "lambda_ctx" in layers


def test_aggregation_scope_dispatch_batch_run() -> None:
    scope = resolve_scope(
        trigger_mode="dispatch",
        job_run_id="run-dispatch",
        semantic_config_version_id=_VERSION,
        now=_NOW,
    )
    assert scope.aggregation_scope == "batch_run"
    assert scope.aggregation_key is None

    repos, _ = _repos()
    result = _run(repos, trigger_mode="dispatch")
    assert result.aggregation_scope == "batch_run"
    assert result.aggregation_key is None


def test_aggregation_scope_schedule_daily() -> None:
    scope = resolve_scope(
        trigger_mode="schedule",
        job_run_id="run-schedule",
        semantic_config_version_id=_VERSION,
        now=_NOW,
    )
    assert scope.aggregation_scope == "daily"
    assert scope.aggregation_key == "2026-07-21"

    repos, _ = _repos()
    result = _run(repos, trigger_mode="schedule")
    assert result.aggregation_scope == "daily"
    assert result.aggregation_key == "2026-07-21"


def test_aggregation_scope_chain_batch_run() -> None:
    scope = resolve_scope(
        trigger_mode="chain",
        job_run_id="run-chain",
        semantic_config_version_id=_VERSION,
        now=_NOW,
    )
    assert scope.aggregation_scope == "batch_run"
    assert scope.aggregation_key is None


def test_stddev_none_when_sample_count_lt_2() -> None:
    stats = compute_distribution_stats([0.5])
    assert stats.sample_count == 1
    assert stats.mean == 0.5
    assert stats.stddev is None
    assert stats.min_value == 0.5
    assert stats.max_value == 0.5

    # 単一 item のみ seed → feature 各軸 sample_count=1 → stddev None
    repos, _ = _repos(features=_features(items=("it_only",)), meanings=_meanings(items=("it_only",)))
    result = _run(repos)
    assert result.status == "succeeded"
    assert all(r.sample_count == 1 for r in repos.feature_metric_rows)
    assert all(r.stddev is None for r in repos.feature_metric_rows)


def test_cli_scaffold_demo_returns_zero(capsys) -> None:
    assert main(["--scaffold-demo", "--job-run-id", "cli"]) == 0
    out = capsys.readouterr().out
    assert "BATCH-016 scaffold demo" in out
    assert "status=succeeded" in out


def test_cli_without_scaffold_requires_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.distribution_metrics import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings as scaffold_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "cli"]) == 2


def test_load_item_features_and_meanings_via_db_reader() -> None:
    from batch.infrastructure.db import ScaffoldDbReader

    reader = ScaffoldDbReader()
    reader.seed(
        "item_feature",
        (
            {
                "item_id": "it_1",
                "semantic_config_version_id": _VERSION,
                "feature_code": "formality",
                "raw_feature_value": 0.8,
                "normalized_feature_value": 0.82,
                "feature_normalization_version_id": _NORM_VERSION,
            },
            {
                "item_id": "it_1",
                "semantic_config_version_id": "other-version",
                "feature_code": "formality",
                "raw_feature_value": 0.1,
                "normalized_feature_value": 0.11,
                "feature_normalization_version_id": _NORM_VERSION,
            },
        ),
    )
    reader.seed(
        "item_meaning",
        (
            {
                "item_id": "it_1",
                "semantic_config_version_id": _VERSION,
                "item_social": 0.7,
                "item_symbolic": 0.55,
                "feature_normalization_version_id": _NORM_VERSION,
            },
        ),
    )
    reader.seed(
        "item_embedding",
        (
            {
                "item_id": "it_1",
                "model_version_id": "scaffold-embedding-model-v1",
                "embedding_input_hash": _HASH,
            },
        ),
    )
    repos = DistributionMetricsRepositories(
        db_writer=ScaffoldDbWriter(),
        db_reader=reader,
    )
    features = repos.load_item_features(semantic_config_version_id=_VERSION)
    assert len(features) == 1
    assert features[0].feature_code == "formality"
    meanings = repos.load_item_meanings(semantic_config_version_id=_VERSION)
    assert len(meanings) == 1
    assert meanings[0].item_social == 0.7
    embeddings = repos.load_item_embeddings()
    assert len(embeddings) == 1
    assert any(c["table"] == "item_feature" for c in reader.fetch_calls)
    assert any(c["table"] == "item_meaning" for c in reader.fetch_calls)
    assert any(c["table"] == "item_embedding" for c in reader.fetch_calls)


def test_cli_non_demo_runs_job_with_live_reader(monkeypatch) -> None:
    """DATABASE_URL ありなら exit 3 固定せず Job を起動する。"""

    from dataclasses import replace

    from batch.application.distribution_metrics import __main__ as cli
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

    code = cli.main(["--job-run-id", "wave-g", "--semantic-config-version-id", _VERSION])
    # empty SELECT → validation failed (exit 1). Important: Job started (not exit-2/old exit-3).
    assert code == 1
    assert reader.fetch_calls


def test_missing_item_feature_fails_without_phase_log() -> None:
    repos, db = _repos(features=[], meanings=_meanings())
    result = _run(repos)
    assert result.status == "failed"
    assert "GRS-VAL-001" in result.error_codes
    assert repos.phase_logs == []
    assert db.write_calls == []


def test_partial_success_phase_log_matches_job_status() -> None:
    # MVP 外 feature のみ → feature/normalization 集計 0 件、meaning のみ残る
    non_mvp = [
        ItemFeatureRow(
            item_id="it_1",
            semantic_config_version_id=_VERSION,
            feature_code="not_an_mvp_feature",
            raw_feature_value=0.5,
            normalized_feature_value=0.5,
            feature_normalization_version_id=_NORM_VERSION,
        )
    ]
    repos, _ = _repos(features=non_mvp, meanings=_meanings())
    result = _run(repos)

    assert result.status == "partially_succeeded"
    assert "GRS-BAT-002" in result.error_codes
    assert result.feature_metric_upsert_count == 0
    assert result.meaning_metric_upsert_count > 0
    assert result.normalization_metric_upsert_count == 0
    assert repos.phase_logs == [
        {"phase": PHASE_FEATURE_DISTRIBUTION_RECORDED, "status": "partially_succeeded"}
    ]
    assert result.completed_phases.index("record_phase") < result.completed_phases.index(
        "finalize"
    )


def test_already_running_grs_bat_003() -> None:
    tracker = ScaffoldJobRunTracker()
    tracker.start(batch_id=BATCH_ID, job_run_id="other")
    repos, db = _repos()
    result = _run(repos, tracker=tracker)
    assert "GRS-BAT-003" in result.error_codes
    assert result.status == "failed"
    assert result.feature_metric_upsert_count == 0
    assert db.write_calls == []


def test_fixture_and_printed_output_have_no_secret_like_values(capsys) -> None:
    forbidden = (
        "sk-",
        "openai_api_key",
        "api_key",
        "bearer ",
        "password",
        "secret_token",
        "postgresql://",
        "DATABASE_URL",
    )
    features = _features()
    meanings = _meanings()
    blob = (str(features) + str(meanings) + str(_user_meanings()) + str(_embeddings())).lower()
    for token in forbidden:
        assert token not in blob

    repos, _ = _repos()
    _run(repos)
    for log in repos.error_logs + repos.phase_logs:
        text = str(log).lower()
        for token in forbidden:
            assert token not in text

    assert main(["--scaffold-demo", "--job-run-id", "sec-check"]) == 0
    printed = capsys.readouterr().out.lower()
    for token in forbidden:
        assert token not in printed


def test_config_keys_loadable_via_scaffold_and_loader() -> None:
    settings = scaffold_batch_settings()
    assert settings.batch_distribution_metrics_aggregation_scope is None
    assert settings.batch_distribution_metrics_semantic_config_version_id is None
    assert settings.batch_distribution_metrics_include_item_embedding is False
    assert settings.batch_distribution_metrics_include_user_meaning is False

    loaded = load_batch_settings(
        environ={
            "APP_ENV": "dev",
            "OBJECT_STORAGE_BUCKET": "raw-dev",
            "BATCH_DISTRIBUTION_METRICS_AGGREGATION_SCOPE": "daily",
            "BATCH_DISTRIBUTION_METRICS_SEMANTIC_CONFIG_VERSION_ID": "cfg-v1",
            "BATCH_DISTRIBUTION_METRICS_INCLUDE_ITEM_EMBEDDING": "true",
            "BATCH_DISTRIBUTION_METRICS_INCLUDE_USER_MEANING": "false",
        }
    )
    assert loaded.batch_distribution_metrics_aggregation_scope == "daily"
    assert loaded.batch_distribution_metrics_semantic_config_version_id == "cfg-v1"
    assert loaded.batch_distribution_metrics_include_item_embedding is True
    assert loaded.batch_distribution_metrics_include_user_meaning is False
    assert "daily" in repr(loaded)
    assert "cfg-v1" in repr(loaded)


def test_scaffold_demo_job_succeeds() -> None:
    result = build_scaffold_demo_job().run(job_run_id="demo", now=_NOW)
    assert result.status == "succeeded"
    assert result.feature_metric_upsert_count > 0


def test_include_item_embedding_reads_but_does_not_write() -> None:
    repos, db = _repos()
    result = _run(repos, include_item_embedding=True)
    assert result.item_embedding_read_count == 1
    assert result.item_embedding_write_count == 0
    assert "item_embedding" not in {c["table"] for c in db.write_calls}


def test_env_keys_registered() -> None:
    from batch.config import BATCH_ENV_KEYS

    assert "BATCH_DISTRIBUTION_METRICS_AGGREGATION_SCOPE" in BATCH_ENV_KEYS
    assert "BATCH_DISTRIBUTION_METRICS_SEMANTIC_CONFIG_VERSION_ID" in BATCH_ENV_KEYS
    assert "BATCH_DISTRIBUTION_METRICS_INCLUDE_ITEM_EMBEDDING" in BATCH_ENV_KEYS
    assert "BATCH_DISTRIBUTION_METRICS_INCLUDE_USER_MEANING" in BATCH_ENV_KEYS


def test_feature_metrics_emit_raw_and_normalized_for_all_mvp_eight_codes() -> None:
    """§16 No.4: feature raw / normalized × MVP 8 軸。"""

    repos, _ = _repos()
    result = _run(repos)
    assert result.status == "succeeded"

    by_layer: dict[str, set[str]] = {"raw": set(), "normalized": set()}
    for row in repos.feature_metric_rows:
        assert row.table == "feature_distribution_metric"
        assert row.feature_code is not None
        by_layer[row.value_layer].add(row.feature_code)

    assert by_layer["raw"] == set(MVP_FEATURE_CODES)
    assert by_layer["normalized"] == set(MVP_FEATURE_CODES)
    assert len(repos.feature_metric_rows) == len(MVP_FEATURE_CODES) * 2


def test_meaning_metrics_item_social_and_symbolic_layers() -> None:
    """§16 No.5（前半）: item meaning は social / symbolic。"""

    repos, _ = _repos()
    result = _run(repos)
    assert result.status == "succeeded"

    item_rows = [r for r in repos.meaning_metric_rows if r.entity_type == "item"]
    layers = {r.value_layer for r in item_rows}
    assert layers == {"social", "symbolic"}
    assert all(r.feature_normalization_version_id == _NORM_VERSION for r in item_rows)


def test_meaning_metrics_split_rows_when_feature_normalization_version_mixed() -> None:
    """§16 No.5（後半）: feature_normalization_version_id 混在時は行分割。"""

    meanings = [
        ItemMeaningRow(
            item_id="it_a",
            semantic_config_version_id=_VERSION,
            item_social=0.7,
            item_symbolic=0.55,
            feature_normalization_version_id="norm-v1",
        ),
        ItemMeaningRow(
            item_id="it_b",
            semantic_config_version_id=_VERSION,
            item_social=0.65,
            item_symbolic=0.5,
            feature_normalization_version_id="norm-v2",
        ),
    ]
    repos, _ = _repos(features=_features(items=("it_a", "it_b")), meanings=meanings)
    result = _run(repos)
    assert result.status == "succeeded"

    item_rows = [r for r in repos.meaning_metric_rows if r.entity_type == "item"]
    versions = {r.feature_normalization_version_id for r in item_rows}
    assert versions == {"norm-v1", "norm-v2"}
    # version × (social, symbolic) = 4 行
    assert len(item_rows) == 4
    for ver in ("norm-v1", "norm-v2"):
        ver_layers = {r.value_layer for r in item_rows if r.feature_normalization_version_id == ver}
        assert ver_layers == {"social", "symbolic"}
        assert all(
            r.sample_count == 1 for r in item_rows if r.feature_normalization_version_id == ver
        )


def test_normalization_metrics_emit_raw_and_sigmoid_layers() -> None:
    """§16 No.6（前半）: normalization は raw / sigmoid。"""

    repos, _ = _repos()
    result = _run(repos)
    assert result.status == "succeeded"

    layers = {r.value_layer for r in repos.normalization_metric_rows}
    assert layers == {"raw", "sigmoid"}
    codes = {r.feature_code for r in repos.normalization_metric_rows}
    assert codes == set(MVP_FEATURE_CODES)
    for row in repos.normalization_metric_rows:
        assert row.feature_normalization_version_id == _NORM_VERSION
        if row.value_layer == "sigmoid":
            assert row.sigma_zero_count is not None
        else:
            assert row.sigma_zero_count is None


def test_normalization_sigma_zero_count_when_stddev_zero() -> None:
    """§16 No.6（後半）: sigmoid 層で stddev==0.0 のとき sigma_zero_count = n。"""

    # 全 item で同一 normalized → stddev 0、raw は分散あり
    features = [
        ItemFeatureRow(
            item_id=item_id,
            semantic_config_version_id=_VERSION,
            feature_code=code,
            raw_feature_value=0.5 + i * 0.1,
            normalized_feature_value=0.42,
            feature_normalization_version_id=_NORM_VERSION,
        )
        for i, item_id in enumerate(("it_1", "it_2", "it_3"))
        for code in MVP_FEATURE_CODES
    ]
    meanings = _meanings(items=("it_1", "it_2", "it_3"))
    repos, _ = _repos(features=features, meanings=meanings)
    result = _run(repos)
    assert result.status == "succeeded"

    sigmoid_rows = [r for r in repos.normalization_metric_rows if r.value_layer == "sigmoid"]
    assert sigmoid_rows
    for row in sigmoid_rows:
        assert row.sample_count == 3
        assert row.stddev == 0.0
        assert row.sigma_zero_count == 3

    raw_rows = [r for r in repos.normalization_metric_rows if r.value_layer == "raw"]
    assert raw_rows
    for row in raw_rows:
        assert row.sigma_zero_count is None
        assert row.stddev is not None and row.stddev > 0.0


def test_batch_run_rerun_upserts_same_unique_key_without_duplicate_rows() -> None:
    """§16 No.7: aggregation_scope=batch_run の冪等 UPSERT。"""

    repos, _ = _repos()
    first = _run(repos, job_run_id="run-rerun")
    assert first.status == "succeeded"
    feature_n = len(repos.feature_metric_rows)
    meaning_n = len(repos.meaning_metric_rows)
    norm_n = len(repos.normalization_metric_rows)
    assert feature_n > 0

    second = _run(repos, job_run_id="run-rerun")
    assert second.status == "succeeded"
    assert len(repos.feature_metric_rows) == feature_n
    assert len(repos.meaning_metric_rows) == meaning_n
    assert len(repos.normalization_metric_rows) == norm_n
    assert all(r.batch_run_id == "run-rerun" for r in repos.feature_metric_rows)


def test_daily_scope_partial_unique_rerun_overwrites_by_aggregation_key() -> None:
    """§16 No.8（daily）: 部分 UNIQUE により同一 aggregation_key は上書き。"""

    repos, _ = _repos()
    first = _run(repos, job_run_id="run-daily-1", trigger_mode="schedule")
    assert first.status == "succeeded"
    assert first.aggregation_scope == "daily"
    assert first.aggregation_key == "2026-07-21"
    feature_n = len(repos.feature_metric_rows)
    first_means = {r.feature_code: r.mean for r in repos.feature_metric_rows if r.value_layer == "raw"}

    # 入力を変えて再実行（別 batch_run_id、同一 daily key）
    repos.item_features = [
        ItemFeatureRow(
            item_id=item_id,
            semantic_config_version_id=_VERSION,
            feature_code=code,
            raw_feature_value=0.9,
            normalized_feature_value=0.91,
            feature_normalization_version_id=_NORM_VERSION,
        )
        for item_id in ("it_1", "it_2")
        for code in MVP_FEATURE_CODES
    ]
    second = _run(repos, job_run_id="run-daily-2", trigger_mode="schedule")
    assert second.status == "succeeded"
    assert len(repos.feature_metric_rows) == feature_n
    assert all(r.batch_run_id == "run-daily-2" for r in repos.feature_metric_rows)
    assert all(r.aggregation_key == "2026-07-21" for r in repos.feature_metric_rows)
    overwritten = {
        r.feature_code: r.mean for r in repos.feature_metric_rows if r.value_layer == "raw"
    }
    assert overwritten != first_means
    assert all(m == 0.9 for m in overwritten.values())


def test_semantic_config_version_scope_resolve_and_partial_unique_upsert() -> None:
    """§16 No.8（semantic_config_version）: resolve と部分 UNIQUE UPSERT。"""

    scope = resolve_scope(
        trigger_mode="dispatch",
        job_run_id="run-scv-1",
        semantic_config_version_id=_VERSION,
        aggregation_scope_override="semantic_config_version",
        now=_NOW,
    )
    assert scope.aggregation_scope == "semantic_config_version"
    assert scope.aggregation_key is None
    assert scope.semantic_config_version_id == _VERSION

    repos, _ = _repos()
    first = _run(
        repos,
        job_run_id="run-scv-1",
        aggregation_scope="semantic_config_version",
    )
    assert first.status == "succeeded"
    assert first.aggregation_scope == "semantic_config_version"
    feature_n = len(repos.feature_metric_rows)
    meaning_n = len(repos.meaning_metric_rows)
    norm_n = len(repos.normalization_metric_rows)

    second = _run(
        repos,
        job_run_id="run-scv-2",
        aggregation_scope="semantic_config_version",
    )
    assert second.status == "succeeded"
    assert len(repos.feature_metric_rows) == feature_n
    assert len(repos.meaning_metric_rows) == meaning_n
    assert len(repos.normalization_metric_rows) == norm_n
    assert all(r.batch_run_id == "run-scv-2" for r in repos.feature_metric_rows)
    assert all(r.aggregation_scope == "semantic_config_version" for r in repos.feature_metric_rows)
    assert all(r.aggregation_key is None for r in repos.feature_metric_rows)
