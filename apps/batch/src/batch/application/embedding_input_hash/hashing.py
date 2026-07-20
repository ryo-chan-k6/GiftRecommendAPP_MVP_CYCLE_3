"""item_text_context builder / canonicalize / SHA-256 for BATCH-014 (§9).

MVP は embedding_source_type = item_text_context 固定で Semantic Concept を
文脈に含めない（item_embedding_テーブル定義書 §5.5 / §11.1）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from batch.application.embedding_input_hash.models import ItemRow


def _norm_text(value: str | None) -> str:
    return "" if value is None else value.strip()


def _norm_list(values: tuple[str, ...] | list[str]) -> list[str]:
    return sorted(v.strip() for v in values if str(v).strip())


def build_item_text_context(
    *,
    item: ItemRow,
    embedding_source_type: str,
    embedding_source_version: str,
) -> dict[str, Any]:
    """Build item_text_context per 仕様書 §9.2（price/review 等は含めない・Semantic Concept 非包含）。

    embedding_source_type / embedding_source_version を含めることで、
    入力構築ルール変更時に hash が変わり再生成が起動する（item_embedding §8.4）。
    """

    return {
        "item_id": item.item_id,
        "item_name": _norm_text(item.item_name),
        "catchcopy": _norm_text(item.catchcopy),
        "item_caption": _norm_text(item.item_caption),
        "genre_id": _norm_text(item.genre_id),
        "genre_name": _norm_text(item.genre_name),
        "attributes": _norm_list(item.attributes),
        "tags": _norm_list(item.tags),
        "embedding_source_type": _norm_text(embedding_source_type),
        "embedding_source_version": _norm_text(embedding_source_version),
    }


def canonicalize_context(context: dict[str, Any]) -> str:
    """Stable JSON for hashing: sorted keys, compact separators."""

    return json.dumps(context, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_embedding_input_hash(context: dict[str, Any]) -> str:
    """SHA-256 lowercase hex (64 chars)."""

    canonical = canonicalize_context(context)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
