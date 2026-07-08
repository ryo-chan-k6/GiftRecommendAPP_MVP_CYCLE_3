"""Feature / Meaning 関連の型定義。"""

from dataclasses import dataclass
from typing import Mapping

FeatureVector = Mapping[str, float]


@dataclass(frozen=True, slots=True)
class MeaningCoordinates:
    """Gift Meaning Space 上の 2 軸座標。"""

    social: float
    symbolic: float


@dataclass(frozen=True, slots=True)
class ProjectionWeights:
    """semantic_config_version 内の射影重み（MVP 骨格）。"""

    formality: float = 1.0
    safety: float = 1.0
    brand_appropriateness: float = 1.0
    emotion: float = 1.0
    novelty: float = 1.0
    intimacy: float = 1.0
    symbolic_identity: float = 1.0
    story_richness: float = 1.0

    def as_mapping(self) -> dict[str, float]:
        return {
            "formality": self.formality,
            "safety": self.safety,
            "brand_appropriateness": self.brand_appropriateness,
            "emotion": self.emotion,
            "novelty": self.novelty,
            "intimacy": self.intimacy,
            "symbolic_identity": self.symbolic_identity,
            "story_richness": self.story_richness,
        }
