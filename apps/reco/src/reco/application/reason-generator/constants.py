"""MOD-RECO-023 Reason Generator constants."""

from __future__ import annotations

MODULE_ID = "MOD-RECO-023"
PHASE_NAME = "reason_generated"

BUILDER_ITEMS_VERSION_INFO_KEY = "_builder_items"

# Reason生成定義書 §17.2 / MOD-RECO-001 §10.3
GENERIC_REASON_SUMMARY = (
    "今回の条件に対して、候補商品の中でも比較的バランスの良い商品です。"
)

STRONG_MATCH_THRESHOLD = 0.80
WEAK_MATCH_MIN = 0.60
WEAK_MATCH_MAX = 0.80

RISK_PENALTY_CAUTION_THRESHOLD = 0.40
AVOID_SIMILARITY_CAUTION_THRESHOLD = 0.60
SOCIAL_MATCH_CAUTION_THRESHOLD = 0.60

# Reason生成定義書 §17.1 入力欠損時の汎用ラベル
DEFAULT_RELATIONSHIP_LABEL = "贈り物として"
DEFAULT_OCCASION_LABEL = "今回のギフトとして"

# Reason生成定義書 §16.2
FEATURE_BADGE_MAP: dict[str, str] = {
    "formality": "きちんと感",
    "safety": "外しにくい",
    "brand_appropriateness": "上品",
    "emotion": "気持ちが伝わる",
    "novelty": "特別感",
    "intimacy": "親しい相手向け",
    "symbolic_identity": "相手らしさ",
    "story_richness": "ストーリー性",
}

IMPORTANT_FEATURES_FOR_WEAK_MATCH: frozenset[str] = frozenset(
    {
        "formality",
        "safety",
        "emotion",
        "brand_appropriateness",
    },
)

# Reason生成定義書 §13.1（部分一致検出）
FORBIDDEN_EXPRESSIONS: tuple[str, ...] = (
    "絶対に喜ばれます",
    "必ず外しません",
    "最高の商品です",
    "誰にでも合います",
    "絶対おすすめです",
    "必ず気に入ります",
    "完璧に合っています",
    "これを選べば間違いありません",
)

GENERATION_METHOD_TEMPLATE = "template"
GENERATION_METHOD_INTERNAL_FALLBACK = "reason_module_internal_fallback"

DEFAULT_TEMPLATE_NAME = "reason_summary_default"
DEFAULT_TEMPLATE_VERSION = 1

LLM_REFINEMENT_ENV = "RECO_REASON_LLM_REFINEMENT_ENABLED"
