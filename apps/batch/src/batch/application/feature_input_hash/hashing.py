"""Payload builder / canonicalize / SHA-256 for BATCH-011 (§9)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from batch.application.feature_input_hash.models import ItemRow, ItemSemanticRow


def _norm_text(value: str | None) -> str:
    return "" if value is None else value.strip()


def _norm_list(values: tuple[str, ...] | list[str]) -> list[str]:
    return sorted(v.strip() for v in values if str(v).strip())


def extract_semantic_concepts(semantic_json: dict[str, Any]) -> list[str]:
    concepts = semantic_json.get("concepts") or []
    codes: list[str] = []
    if isinstance(concepts, list):
        for entry in concepts:
            if isinstance(entry, dict):
                code = entry.get("concept_code")
                if code is not None and str(code).strip():
                    codes.append(str(code).strip())
            elif isinstance(entry, str) and entry.strip():
                codes.append(entry.strip())
    return sorted(codes)


def build_feature_input_payload(
    *,
    item: ItemRow,
    semantic: ItemSemanticRow,
    semantic_config_version_id: str,
) -> dict[str, Any]:
    """Build payload per バッチ設計方針書 §13.3（price/review 等は含めない）。"""

    return {
        "item_id": item.item_id,
        "item_name": _norm_text(item.item_name),
        "catchcopy": _norm_text(item.catchcopy),
        "item_caption": _norm_text(item.item_caption),
        "genre_id": _norm_text(item.genre_id),
        "genre_name": _norm_text(item.genre_name),
        "attributes": _norm_list(item.attributes),
        "tags": _norm_list(item.tags),
        "semantic_concepts": extract_semantic_concepts(semantic.semantic_json),
        "semantic_config_version_id": semantic_config_version_id,
    }


def canonicalize_payload(payload: dict[str, Any]) -> str:
    """Stable JSON for hashing: sorted keys, compact separators."""

    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_feature_input_hash(payload: dict[str, Any]) -> str:
    """SHA-256 lowercase hex (64 chars)."""

    canonical = canonicalize_payload(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
