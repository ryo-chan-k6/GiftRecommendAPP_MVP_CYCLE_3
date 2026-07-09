"""MOD-RECO-024 Reco Error Handler constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-024"
SERVICE_NAME = "reco"

SURFACE_ERROR_CODE_UNKNOWN = "GRS-REC-999"
SURFACE_ERROR_CODE_TIMEOUT = "GRS-REC-101"
SURFACE_ERROR_CODE_RUN_CONFLICT = "GRS-REC-201"
SURFACE_ERROR_CODE_CONFIG = "GRS-REC-003"
SURFACE_ERROR_CODE_RETRIEVAL = "GRS-REC-009"

# MOD-RECO-024 §8.3.2 — surface mapping canonical source (migrated from Orchestrator).
MODULE_SURFACE_ERROR_CODES: dict[str, str] = {
    "MOD-RECO-002": "GRS-REC-002",
    "MOD-RECO-003": "GRS-REC-003",
    "MOD-RECO-004": "GRS-REC-004",
    "MOD-RECO-005": "GRS-REC-005",
    "MOD-RECO-006": "GRS-REC-005",
    "MOD-RECO-007": "GRS-REC-005",
    "MOD-RECO-008": "GRS-REC-006",
    "MOD-RECO-009": "GRS-REC-005",
    "MOD-RECO-010": "GRS-REC-007",
    "MOD-RECO-012": "GRS-REC-009",
    "MOD-RECO-013": "GRS-REC-010",
    "MOD-RECO-014": "GRS-REC-011",
    "MOD-RECO-015": "GRS-REC-011",
    "MOD-RECO-016": "GRS-REC-011",
    "MOD-RECO-017": "GRS-REC-012",
    "MOD-RECO-018": "GRS-REC-012",
    "MOD-RECO-019": "GRS-REC-012",
    "MOD-RECO-020": "GRS-REC-012",
    "MOD-RECO-021": "GRS-REC-012",
    "MOD-RECO-022": "GRS-REC-012",
    "MOD-RECO-023": "GRS-REC-013",
}

USER_MEANING_MODULE_IDS: frozenset[str] = frozenset(
    {
        "MOD-RECO-004",
        "MOD-RECO-005",
        "MOD-RECO-006",
        "MOD-RECO-007",
        "MOD-RECO-008",
        "MOD-RECO-009",
        "MOD-RECO-010",
    },
)

LLM_MODULE_SURFACE_CODES: dict[str, str] = {
    "MOD-RECO-004": "GRS-REC-004",
    "MOD-RECO-005": "GRS-REC-005",
    "MOD-RECO-006": "GRS-REC-005",
    "MOD-RECO-007": "GRS-REC-005",
    "MOD-RECO-008": "GRS-REC-006",
    "MOD-RECO-009": "GRS-REC-005",
    "MOD-RECO-010": "GRS-REC-007",
}

# error_code 定義書に基づく surface code メタデータ（参照のみ）。
SURFACE_CODE_METADATA: dict[str, dict[str, object]] = {
    "GRS-REC-101": {"severity": "error", "retryable": True},
    "GRS-REC-201": {"severity": "error", "retryable": True},
    "GRS-REC-999": {"severity": "critical", "retryable": False},
}

DEFAULT_SEVERITY = "error"
DEFAULT_RETRYABLE = True
