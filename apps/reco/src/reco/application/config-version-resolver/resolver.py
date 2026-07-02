"""MOD-RECO-003 Config Version Resolver implementation."""

from __future__ import annotations

from dataclasses import dataclass

from reco.application.recommendation_orchestrator.execution_context import ExecutionContext
from reco.domain.recommendation.inputs import ExecutionMode

from .constants import (
    DEFAULT_SEMANTIC_CONFIG_NAME,
    MODULE_ID,
    REASON_TEMPLATE_TYPES,
    REQUIRED_MODEL_TYPES,
    SOCIAL_FEATURE_WEIGHT_KEYS,
    SYMBOLIC_FEATURE_WEIGHT_KEYS,
)
from .errors import ConfigResolveError
from .in_memory_repository import build_default_in_memory_repository
from .models import (
    BatchResolveContext,
    GenerationType,
    MatchingConfigRecord,
    ResolutionMetadata,
    ResolvedConfigVersions,
    SemanticConfigRecord,
)
from .ports import ConfigRepositoryPort


@dataclass
class ConfigVersionResolver:
    """Resolves Config / Version IDs from DB catalog (read-only)."""

    repository: ConfigRepositoryPort
    module_id: str = MODULE_ID

    def resolve(self, context: ExecutionContext) -> ExecutionContext:
        """Orchestrator port entry: populate execution_context.config_versions."""
        resolved = self.resolve_online(
            mode=context.execution_mode,
            execution=context.recommendation_request.execution,
        )
        context.config_versions = resolved.to_context_dict()
        context.completed_modules.append(self.module_id)
        return context

    def resolve_batch(self, batch_context: BatchResolveContext) -> ResolvedConfigVersions:
        """Batch pipeline entry (MOD-RECO-026 / 027, BATCH-010〜015)."""
        if batch_context.mode != "batch":
            raise ConfigResolveError(
                "GRS-CFG-999",
                f"invalid batch mode: {batch_context.mode}",
            )

        semantic_version_id, metadata = self._resolve_semantic_version_for_batch(
            batch_context
        )
        self._assert_feature_definitions(semantic_version_id)

        model_versions = self._resolve_model_versions_for_batch(
            batch_context,
            semantic_version_id=semantic_version_id,
        )

        return ResolvedConfigVersions(
            semantic_config_version_id=semantic_version_id,
            model_versions=model_versions,
            ranking_config_id=None,
            reason_template_catalog_ok=None,
            resolution_metadata=metadata,
        )

    def resolve_online(
        self,
        *,
        mode: ExecutionMode,
        execution,
    ) -> ResolvedConfigVersions:
        semantic_version_id, metadata = self._resolve_semantic_version_online(
            mode=mode,
            execution=execution,
        )
        self._assert_feature_definitions(semantic_version_id)

        embedding_override = None
        if execution is not None and execution.model_version_id:
            embedding_override = execution.model_version_id

        model_versions = self._resolve_required_model_versions(
            embedding_override_id=embedding_override,
            required_types=REQUIRED_MODEL_TYPES,
        )

        ranking_config_id = None
        matching_config_id = None
        social_feature_weights = None
        symbolic_feature_weights = None
        reason_catalog_ok = None
        if mode != ExecutionMode.BATCH:
            ranking = self._resolve_ranking_config()
            ranking_config_id = ranking.ranking_config_id
            matching = self._resolve_matching_config()
            matching_config_id = matching.matching_config_id
            social_feature_weights, symbolic_feature_weights = (
                self._extract_matching_feature_weights(matching)
            )
            reason_catalog_ok = self._validate_reason_template_catalog()

        return ResolvedConfigVersions(
            semantic_config_version_id=semantic_version_id,
            model_versions=model_versions,
            ranking_config_id=ranking_config_id,
            matching_config_id=matching_config_id,
            social_feature_weights=social_feature_weights,
            symbolic_feature_weights=symbolic_feature_weights,
            reason_template_catalog_ok=reason_catalog_ok,
            resolution_metadata=metadata,
        )

    def _resolve_semantic_version_online(
        self,
        *,
        mode: ExecutionMode,
        execution,
    ) -> tuple[str, ResolutionMetadata]:
        if execution is None:
            return self._resolve_default_semantic_version(
                resolution_path="default_series_current",
            )

        if execution.semantic_config_version_id:
            return self._resolve_explicit_semantic_version(
                execution.semantic_config_version_id,
                resolution_path="explicit_semantic_config_version_id",
            )

        if execution.config_name and execution.version_label:
            return self._resolve_composite_semantic_version(
                execution.config_name,
                execution.version_label,
                resolution_path="composite_config_name_version_label",
            )

        if execution.config_name:
            return self._resolve_config_name_current(
                execution.config_name,
                resolution_path="config_name_current",
            )

        return self._resolve_default_semantic_version(
            resolution_path="default_series_current",
        )

    def _resolve_semantic_version_for_batch(
        self, batch_context: BatchResolveContext
    ) -> tuple[str, ResolutionMetadata]:
        if batch_context.semantic_config_version_id:
            return self._resolve_explicit_semantic_version(
                batch_context.semantic_config_version_id,
                resolution_path="batch_explicit_semantic_config_version_id",
            )
        return self._resolve_default_semantic_version(
            resolution_path="batch_default_series_current",
        )

    def _resolve_explicit_semantic_version(
        self,
        semantic_config_version_id: str,
        *,
        resolution_path: str,
    ) -> tuple[str, ResolutionMetadata]:
        version = self.repository.get_semantic_config_version_by_id(
            semantic_config_version_id
        )
        if version is None:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"semantic config version not found: {semantic_config_version_id}",
            )

        parent = self.repository.get_semantic_config_by_id(version.semantic_config_id)
        if parent is None or not parent.is_active:
            raise ConfigResolveError(
                "GRS-CFG-002",
                "semantic config version parent series is inactive or missing",
            )

        return version.semantic_config_version_id, ResolutionMetadata(
            semantic_config_name=parent.config_name,
            version_label=version.version_label,
            resolution_path=resolution_path,
        )

    def _resolve_composite_semantic_version(
        self,
        config_name: str,
        version_label: str,
        *,
        resolution_path: str,
    ) -> tuple[str, ResolutionMetadata]:
        config = self.repository.get_semantic_config_by_name(config_name)
        if config is None or not config.is_active:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"semantic config series not found or inactive: {config_name}",
            )

        version = self.repository.get_semantic_config_version_by_composite(
            config_name=config_name,
            version_label=version_label,
        )
        if version is None:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"semantic config version not found for composite: "
                f"{config_name}/{version_label}",
            )

        return version.semantic_config_version_id, ResolutionMetadata(
            semantic_config_name=config_name,
            version_label=version_label,
            resolution_path=resolution_path,
        )

    def _resolve_config_name_current(
        self,
        config_name: str,
        *,
        resolution_path: str,
    ) -> tuple[str, ResolutionMetadata]:
        config = self.repository.get_semantic_config_by_name(config_name)
        if config is None or not config.is_active:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"semantic config series not found or inactive: {config_name}",
            )
        return self._resolve_current_in_series(config, resolution_path=resolution_path)

    def _resolve_default_semantic_version(
        self,
        *,
        resolution_path: str,
    ) -> tuple[str, ResolutionMetadata]:
        config = self.repository.get_semantic_config_by_name(DEFAULT_SEMANTIC_CONFIG_NAME)
        if config is None or not config.is_active:
            raise ConfigResolveError(
                "GRS-CFG-001",
                f"default semantic config series missing: {DEFAULT_SEMANTIC_CONFIG_NAME}",
            )
        return self._resolve_current_in_series(config, resolution_path=resolution_path)

    def _resolve_current_in_series(
        self,
        config: SemanticConfigRecord,
        *,
        resolution_path: str,
    ) -> tuple[str, ResolutionMetadata]:
        current_count = self.repository.count_current_semantic_config_versions(
            config.semantic_config_id
        )
        if current_count == 0:
            raise ConfigResolveError(
                "GRS-CFG-001",
                f"no current semantic config version for series: {config.config_name}",
            )
        if current_count > 1:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"ambiguous current semantic config version for series: {config.config_name}",
            )

        version = self.repository.get_current_semantic_config_version(
            config.semantic_config_id
        )
        if version is None:
            raise ConfigResolveError(
                "GRS-CFG-002",
                f"semantic config version resolve failed for series: {config.config_name}",
            )

        return version.semantic_config_version_id, ResolutionMetadata(
            semantic_config_name=config.config_name,
            version_label=version.version_label,
            resolution_path=resolution_path,
        )

    def _resolve_required_model_versions(
        self,
        *,
        embedding_override_id: str | None,
        required_types: tuple[str, ...],
    ) -> dict[str, str]:
        resolved: dict[str, str] = {}
        for model_type in required_types:
            if model_type == "embedding" and embedding_override_id:
                record = self.repository.get_model_version_by_id(embedding_override_id)
                if record is None:
                    raise ConfigResolveError(
                        "GRS-CFG-003",
                        f"model version not found: {embedding_override_id}",
                    )
                if record.model_type != "embedding":
                    raise ConfigResolveError(
                        "GRS-CFG-003",
                        "model_version_id override must be embedding model_type",
                    )
                resolved[model_type] = record.model_version_id
                continue

            record = self.repository.get_current_model_version(model_type)
            if record is None:
                raise ConfigResolveError(
                    "GRS-CFG-003",
                    f"current model version missing for model_type: {model_type}",
                )
            resolved[model_type] = record.model_version_id
        return resolved

    def _resolve_model_versions_for_batch(
        self,
        batch_context: BatchResolveContext,
        *,
        semantic_version_id: str,
    ) -> dict[str, str]:
        generation_type = batch_context.generation_type

        if generation_type == GenerationType.SEMANTIC:
            return self._resolve_required_model_versions(
                embedding_override_id=batch_context.embedding_model_version_id,
                required_types=("embedding", "llm"),
            )

        if generation_type == GenerationType.FEATURE:
            return self._resolve_required_model_versions(
                embedding_override_id=None,
                required_types=("embedding",),
            )

        if generation_type == GenerationType.EMBEDDING:
            return self._resolve_required_model_versions(
                embedding_override_id=batch_context.embedding_model_version_id,
                required_types=("embedding",),
            )

        raise ConfigResolveError(
            "GRS-CFG-999",
            f"unsupported generation_type: {generation_type}",
        )

    def _resolve_ranking_config(self):
        ranking = self.repository.get_current_ranking_config()
        if ranking is None:
            raise ConfigResolveError("GRS-CFG-004", "ranking config resolve failed")
        return ranking

    def _resolve_matching_config(self) -> MatchingConfigRecord:
        matching = self.repository.get_current_matching_config()
        if matching is None:
            raise ConfigResolveError("GRS-CFG-007", "matching config resolve failed")
        return matching

    def _extract_matching_feature_weights(
        self,
        matching: MatchingConfigRecord,
    ) -> tuple[dict[str, float], dict[str, float]]:
        parameter_json = matching.parameter_json
        social_raw = parameter_json.get("social_feature_weights")
        symbolic_raw = parameter_json.get("symbolic_feature_weights")
        if not isinstance(social_raw, dict) or not isinstance(symbolic_raw, dict):
            raise ConfigResolveError(
                "GRS-CFG-007",
                "matching config parameter_json missing feature weight maps",
            )

        social_weights = self._parse_feature_weight_map(
            social_raw,
            required_keys=SOCIAL_FEATURE_WEIGHT_KEYS,
            map_name="social_feature_weights",
        )
        symbolic_weights = self._parse_feature_weight_map(
            symbolic_raw,
            required_keys=SYMBOLIC_FEATURE_WEIGHT_KEYS,
            map_name="symbolic_feature_weights",
        )
        return social_weights, symbolic_weights

    def _parse_feature_weight_map(
        self,
        raw_map: dict[str, object],
        *,
        required_keys: tuple[str, ...],
        map_name: str,
    ) -> dict[str, float]:
        parsed: dict[str, float] = {}
        for feature_code in required_keys:
            value = raw_map.get(feature_code)
            if not isinstance(value, (int, float)):
                raise ConfigResolveError(
                    "GRS-CFG-007",
                    f"matching config {map_name}.{feature_code} is missing or invalid",
                )
            parsed[feature_code] = float(value)
        return parsed

    def _assert_feature_definitions(self, semantic_config_version_id: str) -> None:
        if self.repository.count_feature_definitions(semantic_config_version_id) < 1:
            raise ConfigResolveError(
                "GRS-CFG-006",
                "feature_definition missing for resolved semantic_config_version_id",
            )

    def _validate_reason_template_catalog(self) -> bool:
        for template_type in REASON_TEMPLATE_TYPES:
            if self.repository.count_active_reason_templates_by_type(template_type) < 1:
                raise ConfigResolveError(
                    "GRS-CFG-006",
                    f"active reason_template missing for template_type: {template_type}",
                )
        return True


def build_default_config_resolver() -> ConfigVersionResolver:
    """Factory with in-memory catalog (scaffold / unit tests)."""
    return ConfigVersionResolver(repository=build_default_in_memory_repository())
