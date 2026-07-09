"""code-definitions から MVP Feature カタログをロードする。"""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from gift_recommendation.shared_logic.constants import MVP_FEATURE_CODES

SCHEMA_VERSION = "1.0"
FEATURE_CODE_DEFINITION_ID = "feature_code"


def get_package_root(start: Path | None = None) -> Path:
    """shared-logic パッケージルート（pyproject.toml があるディレクトリ）。"""
    current = (start or Path(__file__)).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and candidate.name == "shared-logic":
            return candidate
    raise FileNotFoundError("packages/shared-logic root could not be resolved")


def get_code_definitions_root(package_root: Path | None = None) -> Path:
    """隣接 package `code-definitions` のルート。"""
    root = package_root or get_package_root()
    code_definitions_root = root.parent / "code-definitions"
    if not code_definitions_root.is_dir():
        raise FileNotFoundError(f"code-definitions package not found: {code_definitions_root}")
    return code_definitions_root


def _read_feature_code_document(code_definitions_root: Path) -> dict[str, Any]:
    file_path = code_definitions_root / "semantic" / "feature_code.yaml"
    with file_path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"{file_path}: unsupported schema_version")

    code_definition = document.get("code_definition") or {}
    if code_definition.get("id") != FEATURE_CODE_DEFINITION_ID:
        raise ValueError(f"{file_path}: unexpected code_definition.id")

    return document


def build_feature_codes_from_document(document: dict[str, Any]) -> tuple[str, ...]:
    values = document.get("values") or []
    enabled = [
        entry["value"]
        for entry in values
        if entry.get("enabled", True) and isinstance(entry.get("value"), str)
    ]
    return tuple(enabled)


@lru_cache
def load_mvp_feature_codes(
    code_definitions_root: str | None = None,
) -> tuple[str, ...]:
    """`feature_code` 定義から enabled な MVP 8 軸を返す。"""
    root = (
        Path(code_definitions_root)
        if code_definitions_root is not None
        else get_code_definitions_root()
    )
    document = _read_feature_code_document(root)
    feature_codes = build_feature_codes_from_document(document)

    if feature_codes != MVP_FEATURE_CODES:
        raise ValueError(
            "feature_code catalog mismatch with shared-logic constants: "
            f"expected {MVP_FEATURE_CODES}, got {feature_codes}"
        )

    return feature_codes
