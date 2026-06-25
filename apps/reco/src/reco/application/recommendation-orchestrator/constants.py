"""MOD-RECO-001 orchestrator constants."""

from __future__ import annotations

# Recoモジュール一覧 §5.2 / モジュール仕様書 §8.2 の呼び出し順序
ORCHESTRATOR_MODULE_ORDER: tuple[str, ...] = (
    "MOD-RECO-002",
    "MOD-RECO-003",
    "MOD-RECO-004",
    "MOD-RECO-005",
    "MOD-RECO-006",
    "MOD-RECO-007",
    "MOD-RECO-008",
    "MOD-RECO-009",
    "MOD-RECO-010",
    "MOD-RECO-011",
    "MOD-RECO-012",
    "MOD-RECO-013",
    "MOD-RECO-014",
    "MOD-RECO-015",
    "MOD-RECO-016",
    "MOD-RECO-017",
    "MOD-RECO-018",
    "MOD-RECO-019",
    "MOD-RECO-020",
    "MOD-RECO-021",
    "MOD-RECO-022",
    "MOD-RECO-023",
)

# Reason生成定義書 §17.2 汎用 Reason 文（モジュール仕様書 §10.3）
GENERIC_REASON_SUMMARY = (
    "今回の条件に対して、候補商品の中でも比較的バランスの良い商品です。"
)

# 性能要件（バックエンド）§5 / モジュール仕様書 §13.2 暫定値（PoC 後更新）
PIPELINE_SOFT_TIMEOUT_MS = 2_000
PIPELINE_HARD_TIMEOUT_MS = 4_000

MODULE_ERROR_CODES: dict[str, str] = {
    "MOD-RECO-002": "GRS-REC-002",
    "MOD-RECO-003": "GRS-REC-003",
    "MOD-RECO-004": "GRS-REC-004",
    "MOD-RECO-005": "GRS-REC-005",
    "MOD-RECO-006": "GRS-REC-005",
    "MOD-RECO-007": "GRS-REC-005",
    "MOD-RECO-008": "GRS-REC-006",
    "MOD-RECO-009": "GRS-REC-005",
    "MOD-RECO-010": "GRS-REC-007",
    "MOD-RECO-011": "GRS-REC-008",
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
