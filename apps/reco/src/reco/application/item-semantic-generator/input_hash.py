"""semantic_input_hash calculation for MOD-RECO-026 (§8.3.6)."""

from __future__ import annotations

import hashlib
import json

from .models import ItemSemanticGenerationContext


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _normalize_list(values: tuple[str, ...]) -> list[str]:
    return sorted(value.strip() for value in values if value.strip())


def compute_semantic_input_hash(context: ItemSemanticGenerationContext) -> str:
    """Hash inputs used for skip-if-unchanged (item_review excluded)."""
    payload = {
        "item_id": context.item_id,
        "item_name": _normalize_text(context.item_name),
        "item_caption": _normalize_text(context.item_caption),
        "item_description": _normalize_text(context.item_description),
        "genre_name": _normalize_text(context.genre_name),
        "attributes": _normalize_list(context.attributes),
        "tags": _normalize_list(context.tags),
        "semantic_config_version_id": context.semantic_config_version_id,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
