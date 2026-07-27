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
    # continue / keep_processing は DB no-op。item_feature は upsert_rows。
    assert db.write_calls == []
    assert "item_generation_queue" not in {c["table"] for c in db.update_calls}
    feature_upserts = [c for c in db.upsert_calls if c["table"] == "item_feature"]
    assert len(feature_upserts) == 1
    assert feature_upserts[0]["conflict_columns"] == (
        "item_id",
        "semantic_config_version_id",
        "feature_code",
        "feature_input_hash",
        "feature_normalization_version_id",
    )
    assert feature_upserts[0]["update_columns"] == ("raw_feature_value", "generated_at")


def test_upsert_records_raw_hash_and_norm_but_not_normalized() -> None:
    repos, db = _repos()
    _job(repos).run(job_run_id="run-raw")

    row = next(r for r in repos.upsert_rows if r.feature_code == "formality")
    assert row.feature_input_hash == _HASH
    assert row.feature_normalization_version_id == DEFAULT_NORMALIZATION_VERSION
    assert 0.0 <= row.raw_feature_value <= 1.0
    # normalized_feature_value / op / item_feature_id は Upsert payload に含めない
    for call in db.upsert_calls:
        if call["table"] == "item_feature":
            for payload in call["rows"]:
                assert "normalized_feature_value" not in payload
                assert "op" not in payload
                assert "item_feature_id" not in payload


def test_secondary_path_claims_feature_queued() -> None:
    repos, db = _repos(
        queues=[_queue(qid="igq_feat", generation_type="feature", queue_status="queued")],
    )
    result = _job(repos).run(job_run_id="run-secondary")

    assert result.generated_count == 1
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
    assert db.write_calls == []


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
    assert "item_feature" not in {c["table"] for c in db.upsert_calls}
    assert "item_feature" not in {c["table"] for c in db.write_calls}
    skip_updates = [
        c
        for c in db.update_calls
        if c["table"] == "item_generation_queue"
        and c["set_values"].get("queue_status") == "skipped"
    ]
    assert len(skip_updates) == 1


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

    assert "item_semantic" not in {c["table"] for c in db.write_calls}
    assert "item_semantic" not in {c["table"] for c in db.upsert_calls}
    assert repos.item_semantic_write_count == 0
    assert repos.queue_insert_count == 0
    # 主経路 continue / keep_processing は no-op。偽 op キー / INSERT なし。
    assert db.write_calls == []
    for call in db.update_calls:
        assert "op" not in call.get("set_values", {})
    for call in db.upsert_calls:
        for row in call["rows"]:
            assert "op" not in row
    feature_upserts = [c for c in db.upsert_calls if c["table"] == "item_feature"]
    assert len(feature_upserts) == 1


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


def test_cli_without_scaffold_demo_exits_2_without_database_url(monkeypatch) -> None:
    from dataclasses import replace

    from batch.application.item_feature import __main__ as cli
    from batch.config._scaffold import scaffold_batch_settings

    monkeypatch.setattr(
        cli,
        "load_batch_settings",
        lambda: replace(scaffold_batch_settings(), database_url=None),
    )
    assert cli.main(["--job-run-id", "cli"]) == 2


def test_list_and_load_via_db_reader() -> None:
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
                "item_name": "Gift",
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
                "generated_at": None,
            },
        ),
    )
    reader.seed(
        "item_feature_input",
        (
            {
                "item_id": "it_1",
                "semantic_config_version_id": _VERSION,
                "feature_input_hash": _HASH,
            },
        ),
    )
    repos = ItemFeatureRepositories(db_writer=ScaffoldDbWriter(), db_reader=reader)
    targets, _ = repos.list_target_queues(max_items=10)
    assert [q.item_generation_queue_id for q in targets] == ["igq_sem"]
    assert repos.load_item(item_id="it_1").item_name == "Gift"
    assert repos.load_item(item_id="it_1").genre_id is None
    handoff = repos.load_hash_handoff(item_id="it_1", semantic_config_version_id=_VERSION)
    assert handoff is not None
    assert handoff.feature_input_hash == _HASH


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


def test_if_shared_002_uses_in_process_adapter_not_http() -> None:
    """§16 No.3: IF-SHARED-002 は in-process Python import で MOD-RECO-027 相当を呼び出す。

    HTTP API 化していないことを確認する。Port 互換の in-process アダプタが
    HTTP client 属性を持たず、直接 generate できることを検証する。
    """
    from batch.application.item_feature.adapter import (
        ItemFeatureGeneratorPort,
        ScaffoldItemFeatureAdapter,
    )
    from batch.application.item_feature.models import FeatureGenerationContext

    repos, _ = _repos()
    adapter = build_scaffold_adapter(concept_feature_rules=_RULES)

    # Protocol 互換・Scaffold 実装であること（HTTP client ではない）
    assert isinstance(adapter, ScaffoldItemFeatureAdapter)
    port: ItemFeatureGeneratorPort = adapter
    assert callable(port.generate_item_feature)
    assert not hasattr(adapter, "base_url")
    assert not hasattr(adapter, "session")
    assert not hasattr(adapter, "http_client")

    # in-process で生成できることを確認（HTTP を使わない）
    ctx = FeatureGenerationContext(
        trace_id="test-trace",
        item_id="it_1",
        semantic_config_version_id=_VERSION,
        feature_input_hash=_HASH,
        feature_normalization_version_id=DEFAULT_NORMALIZATION_VERSION,
        concepts=[],
    )
    result = adapter.generate_item_feature(ctx)
    assert result.status == "generated"
    assert len(result.features) == len(MVP_FEATURE_CODES)


def test_rule_based_generation_without_llm() -> None:
    """§16 No.5: MVP はルールベース。LLM を呼ばず Concept Rule のみで生成する。

    仕様書 §18.1 の「Scaffold 不要」は LLM Scaffold を指す。
    本実装の ScaffoldItemFeatureAdapter は in-process のルールベース実装であり、
    LLM を呼び出さず 8 軸を生成することを確認する。
    """
    repos, _ = _repos(
        semantics=[_semantic(concepts=[
            {"concept_code": "formal_refined", "confidence": 0.9},
            {"concept_code": "emotional_warm", "confidence": 0.8},
        ])]
    )
    _job(repos).run(job_run_id="run-rule-based")

    # 8 軸が生成されていることを確認
    assert repos.item_feature_write_count == len(MVP_FEATURE_CODES)

    # formality と emotion は baseline (0.5) から変化しているはず
    # （ルールベース計算: 0.5 + delta×weight×confidence）
    formality_row = next(r for r in repos.upsert_rows if r.feature_code == "formality")
    emotion_row = next(r for r in repos.upsert_rows if r.feature_code == "emotion")

    # baseline から変化していることを確認（ルールが適用されている）
    assert formality_row.raw_feature_value != 0.5
    assert emotion_row.raw_feature_value != 0.5

    # [0.0, 1.0] 範囲内であることを確認
    assert 0.0 <= formality_row.raw_feature_value <= 1.0
    assert 0.0 <= emotion_row.raw_feature_value <= 1.0

