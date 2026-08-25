"""Load concept_feature_rule from DB into signed ConceptFeatureRule dict.

DB stores feature_delta as magnitude (0.0–1.0) and polarity separately (#476).
ScaffoldItemFeatureAdapter expects signed deltas (raw += delta * weight * confidence).
"""

from __future__ import annotations

from batch.application.item_feature.adapter import ConceptFeatureRule
from batch.infrastructure.db import DbReader


def apply_polarity(feature_delta: float, polarity: str) -> float:
    """Convert DB |delta| + polarity into a signed delta (MOD-RECO-027 同型)."""

    magnitude = abs(float(feature_delta))
    normalized = (polarity or "positive").strip().lower()
    if normalized == "negative":
        return -magnitude
    # positive / mixed / unknown → +magnitude（MVP seed に mixed は無い）
    return magnitude


def load_concept_feature_rules(
    db_reader: DbReader,
    *,
    semantic_config_version_id: str,
) -> ConceptFeatureRule:
    """Return {concept_code: {feature_code: signed_delta}} for an active version."""

    version = semantic_config_version_id.strip()
    if not version:
        return {}

    concept_rows = db_reader.fetch_rows(
        "semantic_concept",
        columns=("semantic_concept_id", "concept_code"),
        equals=(
            ("semantic_config_version_id", version),
            ("is_active", True),
        ),
        limit=500,
    )
    id_to_code: dict[str, str] = {}
    for row in concept_rows.rows:
        cid = row.get("semantic_concept_id")
        code = row.get("concept_code")
        if cid is None or not code:
            continue
        id_to_code[str(cid)] = str(code).strip()

    rule_rows = db_reader.fetch_rows(
        "concept_feature_rule",
        columns=(
            "semantic_concept_id",
            "feature_code",
            "feature_delta",
            "polarity",
        ),
        equals=(
            ("semantic_config_version_id", version),
            ("is_active", True),
        ),
        limit=5000,
    )

    rules: ConceptFeatureRule = {}
    for row in rule_rows.rows:
        concept_code = id_to_code.get(str(row.get("semantic_concept_id") or ""))
        feature_code = str(row.get("feature_code") or "").strip()
        if not concept_code or not feature_code:
            continue
        try:
            delta = apply_polarity(
                float(row.get("feature_delta") or 0.0),
                str(row.get("polarity") or "positive"),
            )
        except (TypeError, ValueError):
            continue
        axis = rules.setdefault(concept_code, {})
        axis[feature_code] = delta
    return rules
