"""packages/test-fixtures パス解決・manifest ロード。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURE_SCHEMA_VERSION = "1.0"
FIXTURE_MANIFEST_FILE = "fixtures/manifest.json"


def get_package_root(start: Path | None = None) -> Path:
    """test-fixtures パッケージルート（pyproject.toml があるディレクトリ）。"""
    current = (start or Path(__file__)).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / "pyproject.toml").exists() and candidate.name == "test-fixtures":
            return candidate
    raise FileNotFoundError("packages/test-fixtures root could not be resolved")


def resolve_fixture_path(package_root: Path, relative_path: str) -> Path:
    return package_root / relative_path


@lru_cache
def load_fixture_manifest(package_root: str | None = None) -> dict[str, Any]:
    root = Path(package_root) if package_root else get_package_root()
    manifest_path = resolve_fixture_path(root, FIXTURE_MANIFEST_FILE)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))

    if document.get("schemaVersion") != FIXTURE_SCHEMA_VERSION:
        raise ValueError(f"{manifest_path}: unsupported schemaVersion")

    return document


def read_json_fixture(package_root: Path, relative_path: str) -> dict[str, Any]:
    file_path = resolve_fixture_path(package_root, relative_path)
    return json.loads(file_path.read_text(encoding="utf-8"))


def load_fixture_item(item_key: str, package_root: Path | None = None) -> dict[str, Any]:
    root = package_root or get_package_root()
    manifest = load_fixture_manifest(str(root))
    item = (manifest.get("items") or {}).get(item_key)
    if not item:
        raise KeyError(f"Unknown fixture item: {item_key}")
    return read_json_fixture(root, item["path"])


def load_mvp_user_features_baseline(package_root: Path | None = None) -> dict[str, Any]:
    return load_fixture_item("mvp_user_features_baseline", package_root)


def load_recommendation_request_boss_thanks_minimal(
    package_root: Path | None = None,
) -> dict[str, Any]:
    return load_fixture_item("recommendation_request_boss_thanks_minimal", package_root)
