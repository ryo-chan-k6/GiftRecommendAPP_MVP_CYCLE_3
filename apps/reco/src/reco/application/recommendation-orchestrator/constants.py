"""MOD-RECO-001 orchestrator constants."""

from __future__ import annotations

# MOD-RECO-001 §8.2.1 物理呼び出し順（003→002 INSERT 後、004〜023）
ORCHESTRATOR_MODULE_ORDER: tuple[str, ...] = (
    "MOD-RECO-003",
    "MOD-RECO-002",
    "MOD-RECO-004",
    "MOD-RECO-005",
    "MOD-RECO-006",
    "MOD-RECO-007",
    "MOD-RECO-008",
    "MOD-RECO-009",
    "MOD-RECO-010",
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

# 性能要件（バックエンド）§5 / MOD-RECO-001 §13.2 / #1748 確定値（案A1）
# 同期外部 AI 込み・本番主経路 soft 6,000ms / hard 8,000ms
# Reco 内部監視用 soft 1,500 / hard 2,000 は docs 上の監視用 SLO（本定数とは役割分離）
PIPELINE_SOFT_TIMEOUT_MS = 6_000
PIPELINE_HARD_TIMEOUT_MS = 8_000
# MOD-RECO-024 SURFACE_ERROR_CODE_TIMEOUT（GRS-REC-101）と整合
PIPELINE_TIMEOUT_ERROR_CODE = "GRS-REC-101"

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
