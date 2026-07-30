from __future__ import annotations

import uuid

import pytest

from batch.application.current_versions import (
    CurrentVersionResolveError,
    CurrentVersionResolver,
)
from batch.infrastructure.db import ScaffoldDbReader

SEMANTIC_CONFIG_ID = str(uuid.uuid4())
SEMANTIC_VERSION_ID = str(uuid.uuid4())
NORMALIZATION_VERSION_ID = str(uuid.uuid4())
NORMALIZATION_RULE_ID = str(uuid.uuid4())
EMBEDDING_MODEL_VERSION_ID = str(uuid.uuid4())


def _reader() -> ScaffoldDbReader:
    return ScaffoldDbReader(
        seed_rows={
            "semantic_config": (
                {
                    "semantic_config_id": SEMANTIC_CONFIG_ID,
                    "config_name": "mvp_semantic_config",
                    "is_active": True,
                },
            ),
            "semantic_config_version": (
                {
                    "semantic_config_version_id": SEMANTIC_VERSION_ID,
                    "semantic_config_id": SEMANTIC_CONFIG_ID,
                    "is_current": True,
                },
            ),
            "feature_normalization_version": (
                {
                    "feature_normalization_version_id": NORMALIZATION_VERSION_ID,
                    "normalization_method": "sigmoid",
                    "is_current": True,
                },
            ),
            "normalization_rule": (
                {
                    "normalization_rule_id": NORMALIZATION_RULE_ID,
                    "semantic_config_version_id": SEMANTIC_VERSION_ID,
                    "normalization_method": "sigmoid",
                    "feature_normalization_version_id": NORMALIZATION_VERSION_ID,
                    "is_active": True,
                },
            ),
            "model_version": (
                {
                    "model_version_id": EMBEDDING_MODEL_VERSION_ID,
                    "model_type": "embedding",
                    "is_current": True,
                },
            ),
        }
    )


def test_resolves_current_versions_with_required_series_and_binding() -> None:
    resolver = CurrentVersionResolver(_reader())

    semantic = resolver.resolve_semantic()

    assert semantic == SEMANTIC_VERSION_ID
    assert resolver.resolve_normalization(
        semantic_config_version_id=semantic
    ) == NORMALIZATION_VERSION_ID
    assert resolver.resolve_embedding_model() == EMBEDDING_MODEL_VERSION_ID


@pytest.mark.parametrize(
    ("table", "method", "expected_code"),
    [
        ("semantic_config", "resolve_semantic", "GRS-CFG-002"),
        ("semantic_config_version", "resolve_semantic", "GRS-CFG-002"),
        ("model_version", "resolve_embedding_model", "GRS-CFG-003"),
    ],
)
def test_missing_current_version_fails_before_write(
    table: str,
    method: str,
    expected_code: str,
) -> None:
    reader = _reader()
    reader.seed(table, ())
    resolver = CurrentVersionResolver(reader)

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        getattr(resolver, method)()

    assert exc_info.value.code == expected_code


def test_inactive_semantic_config_is_treated_as_missing() -> None:
    reader = _reader()
    row = reader.seed_rows["semantic_config"][0]
    reader.seed("semantic_config", ({**row, "is_active": False},))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_semantic()

    assert exc_info.value.code == "GRS-CFG-002"


@pytest.mark.parametrize(
    ("table", "id_column"),
    [
        ("semantic_config", "semantic_config_id"),
        ("semantic_config_version", "semantic_config_version_id"),
    ],
)
def test_multiple_current_semantic_rows_are_rejected(table: str, id_column: str) -> None:
    reader = _reader()
    row = reader.seed_rows[table][0]
    reader.seed(table, (row, {**row, id_column: str(uuid.uuid4())}))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_semantic()

    assert exc_info.value.code == "GRS-CFG-002"


@pytest.mark.parametrize(
    ("table", "id_column"),
    [
        ("semantic_config", "semantic_config_id"),
        ("semantic_config_version", "semantic_config_version_id"),
    ],
)
def test_non_uuid_semantic_ids_are_rejected(table: str, id_column: str) -> None:
    reader = _reader()
    row = reader.seed_rows[table][0]
    reader.seed(table, ({**row, id_column: "scaffold-semantic-config-v1"},))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_semantic()

    assert exc_info.value.code == "GRS-CFG-002"


def test_multiple_current_versions_are_rejected() -> None:
    reader = _reader()
    row = reader.seed_rows["model_version"][0]
    reader.seed("model_version", (row, {**row, "model_version_id": str(uuid.uuid4())}))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_embedding_model()

    assert exc_info.value.code == "GRS-CFG-003"


def test_non_uuid_embedding_model_version_is_rejected() -> None:
    reader = _reader()
    row = reader.seed_rows["model_version"][0]
    reader.seed("model_version", ({**row, "model_version_id": "scaffold-embedding-v1"},))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_embedding_model()

    assert exc_info.value.code == "GRS-CFG-003"


def test_missing_current_normalization_version_is_rejected() -> None:
    reader = _reader()
    reader.seed("feature_normalization_version", ())

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_multiple_current_normalization_versions_are_rejected() -> None:
    reader = _reader()
    row = reader.seed_rows["feature_normalization_version"][0]
    reader.seed(
        "feature_normalization_version",
        (row, {**row, "feature_normalization_version_id": str(uuid.uuid4())}),
    )

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_non_uuid_current_version_is_rejected() -> None:
    reader = _reader()
    reader.seed(
        "feature_normalization_version",
        (
            {
                "feature_normalization_version_id": "scaffold-feature-norm-v1",
                "normalization_method": "sigmoid",
                "is_current": True,
            },
        ),
    )

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_missing_normalization_binding_is_rejected() -> None:
    reader = _reader()
    reader.seed("normalization_rule", ())

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_inactive_normalization_binding_is_rejected() -> None:
    reader = _reader()
    row = reader.seed_rows["normalization_rule"][0]
    reader.seed("normalization_rule", ({**row, "is_active": False},))

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_binding_to_stale_normalization_version_is_rejected() -> None:
    """current version が更新されたのに binding が旧 version のままなら失敗させる。"""

    reader = _reader()
    row = reader.seed_rows["normalization_rule"][0]
    reader.seed(
        "normalization_rule",
        ({**row, "feature_normalization_version_id": str(uuid.uuid4())},),
    )

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=SEMANTIC_VERSION_ID
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_binding_of_other_semantic_version_is_not_reused() -> None:
    """binding は semantic_config_version 単位。他 version の行を流用しない。"""

    reader = _reader()

    with pytest.raises(CurrentVersionResolveError) as exc_info:
        CurrentVersionResolver(reader).resolve_normalization(
            semantic_config_version_id=str(uuid.uuid4())
        )

    assert exc_info.value.code == "GRS-CFG-001"


def test_resolver_reads_only_expected_master_tables() -> None:
    """master seed で用意すべきテーブル・列を固定する（実 DB 列との対応）。"""

    reader = _reader()
    resolver = CurrentVersionResolver(reader)
    semantic = resolver.resolve_semantic()
    resolver.resolve_normalization(semantic_config_version_id=semantic)
    resolver.resolve_embedding_model()

    assert [call["table"] for call in reader.fetch_calls] == [
        "semantic_config",
        "semantic_config_version",
        "feature_normalization_version",
        "normalization_rule",
        "model_version",
    ]
    binding_call = reader.fetch_calls[3]
    assert binding_call["equals"] == (
        ("semantic_config_version_id", SEMANTIC_VERSION_ID),
        ("normalization_method", "sigmoid"),
        ("feature_normalization_version_id", NORMALIZATION_VERSION_ID),
        ("is_active", True),
    )
