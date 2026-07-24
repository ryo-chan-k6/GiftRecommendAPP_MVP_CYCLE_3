"""E2 T5: DbWriter Protocol / CLI wiring / representative UPSERT / scaffold regression."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from batch.application.embedding_input_hash import __main__ as embedding_input_hash_main
from batch.application.feature_input_hash import __main__ as feature_input_hash_main
from batch.application.product_diff import __main__ as product_diff_main
from batch.infrastructure.db import (
    DatabaseError,
    DbWriter,
    PostgresDbWriter,
    ScaffoldDbWriter,
    create_db_writer,
    mask_database_url,
    resolve_job_db_writer,
)

_APP_ROOT = Path(__file__).resolve().parents[3] / "src" / "batch" / "application"

# Wave A / Wave B CLI modules that must call create_db_writer on non-demo path
_WAVE_A_MAINS = (
    "genre_sync",
    "ranking_snapshot",
    "item_pseudo_diff",
    "raw_staging",
    "product_diff",
    "item_apply",
    "item_active_status",
    "item_recheck",
)
_WAVE_B_MAINS = (
    "item_generation_queue",
    "item_semantic",
    "item_feature",
    "feature_normalization",
    "feature_input_hash",
    "item_embedding",
    "embedding_input_hash",
    "distribution_metrics",
    "import_summary",
)


def _assert_db_writer_protocol(writer: object) -> None:
    """Structural Protocol check without requiring @runtime_checkable."""

    assert hasattr(writer, "backend")
    assert isinstance(writer.backend, str)
    assert callable(getattr(writer, "write_rows", None))
    assert callable(getattr(writer, "upsert_rows", None))
    # typing.Protocol is satisfied structurally for both implementations
    _: DbWriter = writer  # type: ignore[assignment]


def _main_source_calls_create_db_writer(module_name: str) -> bool:
    path = _APP_ROOT / module_name / "__main__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "create_db_writer":
                return True
            if isinstance(func, ast.Attribute) and func.attr == "create_db_writer":
                return True
    return False


def test_scaffold_and_postgres_satisfy_db_writer_protocol() -> None:
    scaffold = ScaffoldDbWriter()
    postgres = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    _assert_db_writer_protocol(scaffold)
    _assert_db_writer_protocol(postgres)
    assert scaffold.backend == "scaffold"
    assert postgres.backend == "postgres"


def test_create_db_writer_protocol_for_all_url_shapes() -> None:
    cases: list[tuple[str | None, type]] = [
        (None, ScaffoldDbWriter),
        ("", ScaffoldDbWriter),
        ("scaffold://local", ScaffoldDbWriter),
        ("postgresql://localhost:5432/gift", PostgresDbWriter),
    ]
    for url, expected in cases:
        writer = create_db_writer(url)
        _assert_db_writer_protocol(writer)
        assert isinstance(writer, expected)


def test_resolve_job_db_writer_scaffold_demo_is_always_scaffold() -> None:
    writer = resolve_job_db_writer(
        scaffold_demo=True,
        database_url="postgresql://user:secret@localhost:5432/gift",
    )
    assert isinstance(writer, ScaffoldDbWriter)
    _assert_db_writer_protocol(writer)


@pytest.mark.parametrize(
    ("conflict", "update"),
    [
        (("batch_run_id", "external_item_code"), ("diff_status", "updated_at")),
        (
            ("batch_run_id", "source", "external_item_code"),
            ("candidate_status", "updated_at"),
        ),
        (
            ("item_id", "semantic_config_version_id", "feature_input_hash"),
            ("feature_input_payload", "computed_at", "updated_at"),
        ),
        (
            ("item_id", "model_version_id", "embedding_input_hash"),
            ("item_text_context", "computed_at", "updated_at"),
        ),
    ],
)
def test_scaffold_upsert_accepts_representative_if_conflict_keys(
    conflict: tuple[str, ...],
    update: tuple[str, ...],
) -> None:
    """代表 IF（006/020/012/015）の冪等キー形状が upsert_rows で受け付けられること。"""

    row = {column: f"v-{column}" for column in (*conflict, *update)}
    writer = ScaffoldDbWriter()
    result = writer.upsert_rows(
        "boundary_table",
        (row,),
        conflict_columns=conflict,
        update_columns=update,
    )
    assert result.rows_affected == 1
    assert writer.upsert_calls[0]["conflict_columns"] == conflict
    assert writer.upsert_calls[0]["update_columns"] == update


def test_postgres_upsert_rejects_conflict_column_missing_from_row() -> None:
    writer = PostgresDbWriter(database_url="postgresql://localhost:5432/gift")
    with pytest.raises(DatabaseError, match="conflict column"):
        writer.upsert_rows(
            "product_diff_result",
            ({"batch_run_id": "r1"},),
            conflict_columns=("batch_run_id", "external_item_code"),
        )


def test_mask_database_url_never_leaks_password_in_common_forms() -> None:
    samples = (
        "postgresql://user:s3cret@localhost:5432/gift",
        "postgres://user:s3cret@db.example:5432/gift",
        "postgresql://user@localhost:5432/gift",
    )
    for sample in samples:
        masked = mask_database_url(sample)
        assert "s3cret" not in masked


@pytest.mark.parametrize("module_name", _WAVE_A_MAINS + _WAVE_B_MAINS)
def test_wave_cli_mains_call_create_db_writer(module_name: str) -> None:
    assert _main_source_calls_create_db_writer(module_name), module_name


def test_scaffold_demo_product_diff_succeeds() -> None:
    code = product_diff_main.main(["--scaffold-demo", "--job-run-id", "t5-pd"])
    assert code == 0


def test_scaffold_demo_feature_input_hash_succeeds() -> None:
    code = feature_input_hash_main.main(["--scaffold-demo", "--job-run-id", "t5-fih"])
    assert code == 0


def test_scaffold_demo_embedding_input_hash_succeeds() -> None:
    code = embedding_input_hash_main.main(["--scaffold-demo", "--job-run-id", "t5-eih"])
    assert code == 0
