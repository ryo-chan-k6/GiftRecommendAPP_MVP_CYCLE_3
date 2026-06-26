"""MOD-RECO-003 input / output models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class GenerationType(StrEnum):
    SEMANTIC = "semantic"
    FEATURE = "feature"
    EMBEDDING = "embedding"


@dataclass(frozen=True)
class SemanticConfigRecord:
    semantic_config_id: str
    config_name: str
    is_active: bool


@dataclass(frozen=True)
class SemanticConfigVersionRecord:
    semantic_config_version_id: str
    semantic_config_id: str
    version_label: str
    is_current: bool


@dataclass(frozen=True)
class ModelVersionRecord:
    model_version_id: str
    model_type: str
    is_current: bool


@dataclass(frozen=True)
class RankingConfigRecord:
    ranking_config_id: str
    config_name: str
    is_current: bool


@dataclass(frozen=True)
class ReasonTemplateRecord:
    reason_template_id: str
    template_type: str
    is_active: bool


@dataclass(frozen=True)
class ResolutionMetadata:
    """Audit metadata for config resolution (no secrets)."""

    semantic_config_name: str | None = None
    version_label: str | None = None
    resolution_path: str | None = None

    def to_dict(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.semantic_config_name is not None:
            payload["semantic_config_name"] = self.semantic_config_name
        if self.version_label is not None:
            payload["version_label"] = self.version_label
        if self.resolution_path is not None:
            payload["resolution_path"] = self.resolution_path
        return payload


@dataclass(frozen=True)
class ResolvedConfigVersions:
    """Resolved Config / Version IDs for pipeline propagation."""

    semantic_config_version_id: str
    model_versions: dict[str, str]
    ranking_config_id: str | None = None
    reason_template_catalog_ok: bool | None = None
    resolution_metadata: ResolutionMetadata = field(default_factory=ResolutionMetadata)

    def to_context_dict(self) -> dict[str, str]:
        """Flatten into ExecutionContext.config_versions (dict[str, str])."""
        result: dict[str, str] = {
            "semantic_config_version_id": self.semantic_config_version_id,
        }
        for model_type, version_id in self.model_versions.items():
            result[f"model_versions.{model_type}"] = version_id
        if self.ranking_config_id is not None:
            result["ranking_config_id"] = self.ranking_config_id
        if self.reason_template_catalog_ok is not None:
            result["reason_template_catalog_ok"] = (
                "true" if self.reason_template_catalog_ok else "false"
            )
        for key, value in self.resolution_metadata.to_dict().items():
            result[f"resolution_metadata.{key}"] = value
        return result


@dataclass(frozen=True)
class BatchResolveContext:
    """Batch pipeline input for MOD-RECO-003 (module spec §6.2)."""

    item_generation_queue_id: str
    item_id: str
    generation_type: GenerationType
    mode: str = "batch"
    semantic_config_version_id: str | None = None
    embedding_model_version_id: str | None = None
