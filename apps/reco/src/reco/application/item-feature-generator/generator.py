"""MOD-RECO-027 Item Feature Generator implementation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .shared_logic_bridge import clip_feature_vector, integrate_feature_deltas
from reco.domain.gift_meaning.features import MVP_FEATURE_CODES
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import FEATURE_INPUT_HASH_LENGTH, MODULE_ID, NEUTRAL_BASE
from .errors import ItemFeatureGeneratorError
from .models import (
    GenerationStatus,
    ItemFeatureGenerationContext,
    ItemFeatureGenerationResult,
    ItemFeatureUpsertRow,
)
from .ports import (
    ConceptFeatureRuleRepositoryPort,
    FeatureDefinitionRepositoryPort,
    ItemFeatureRepositoryPort,
    ItemValidationPort,
    NormalizationRuleRepositoryPort,
)
from .rule_engine import (
    aggregate_item_feature_deltas,
    assert_finite_feature_vector,
    build_rules_by_concept,
    count_raw_clip_applied,
    neutral_feature_base,
    parse_concepts_from_semantic_json,
)

_HEX_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class ItemFeatureGenerator:
    """Batch port implementation for Item Feature raw generation."""

    concept_feature_rules: ConceptFeatureRuleRepositoryPort
    normalization_rules: NormalizationRuleRepositoryPort
    feature_definitions: FeatureDefinitionRepositoryPort
    item_validation: ItemValidationPort
    item_feature_repository: ItemFeatureRepositoryPort
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID

    def generate_item_features(
        self,
        context: ItemFeatureGenerationContext,
    ) -> ItemFeatureGenerationResult:
        self._validate_context(context)
        normalization_binding = self._resolve_normalization_binding(
            context.semantic_config_version_id,
        )
        feature_normalization_version_id = (
            normalization_binding.feature_normalization_version_id
        )

        if context.skip_if_unchanged and self._should_skip(
            context,
            feature_normalization_version_id=feature_normalization_version_id,
        ):
            existing = self.item_feature_repository.find_by_idempotent_key(
                item_id=context.item_id,
                semantic_config_version_id=context.semantic_config_version_id,
                feature_input_hash=context.feature_input_hash,
                feature_normalization_version_id=feature_normalization_version_id,
            )
            existing_by_code = {row.feature_code: row for row in existing}
            features = {
                code: float(existing_by_code[code].raw_feature_value)
                for code in MVP_FEATURE_CODES
                if code in existing_by_code
                and existing_by_code[code].raw_feature_value is not None
            }
            self._log_generation_summary(
                context,
                concept_count=self._concept_count(context),
                rule_hit_count=0,
                raw_clip_count=0,
                status=GenerationStatus.SKIPPED,
            )
            return ItemFeatureGenerationResult(
                status=GenerationStatus.SKIPPED,
                features=features,
                feature_codes=MVP_FEATURE_CODES,
                feature_input_hash=context.feature_input_hash,
                feature_normalization_version_id=feature_normalization_version_id,
                item_feature_ids=tuple(
                    existing_by_code[code].item_feature_id for code in MVP_FEATURE_CODES
                ),
                skip_reason="feature_input_hash_unchanged",
            )

        active_rules = self.concept_feature_rules.list_active_rules(
            context.semantic_config_version_id,
        )
        rules_by_concept = build_rules_by_concept(active_rules)
        concepts = parse_concepts_from_semantic_json(context.item_semantic.semantic_json)
        deltas, rule_hit_count = aggregate_item_feature_deltas(
            concepts,
            rules_by_concept=rules_by_concept,
        )

        integrated = integrate_feature_deltas(neutral_feature_base(), deltas)
        assert_finite_feature_vector(integrated)
        clipped = clip_feature_vector(integrated)
        raw_clip_count = count_raw_clip_applied(integrated, clipped)

        self._validate_feature_definition_coverage(context.semantic_config_version_id)

        upsert_rows = tuple(
            ItemFeatureUpsertRow(
                item_id=context.item_id,
                semantic_config_version_id=context.semantic_config_version_id,
                feature_code=feature_code,
                feature_input_hash=context.feature_input_hash,
                feature_normalization_version_id=feature_normalization_version_id,
                raw_feature_value=clipped[feature_code],
            )
            for feature_code in MVP_FEATURE_CODES
        )

        try:
            persisted = self.item_feature_repository.upsert(upsert_rows)
        except Exception as exc:
            raise ItemFeatureGeneratorError(
                f"item_feature upsert failed: {exc}",
            ) from exc

        self._log_generation_summary(
            context,
            concept_count=len(concepts),
            rule_hit_count=rule_hit_count,
            raw_clip_count=raw_clip_count,
            status=GenerationStatus.GENERATED,
        )

        return ItemFeatureGenerationResult(
            status=GenerationStatus.GENERATED,
            features={code: clipped[code] for code in MVP_FEATURE_CODES},
            feature_codes=MVP_FEATURE_CODES,
            feature_input_hash=context.feature_input_hash,
            feature_normalization_version_id=feature_normalization_version_id,
            item_feature_ids=tuple(row.item_feature_id for row in persisted),
        )

    def _validate_context(self, context: ItemFeatureGenerationContext) -> None:
        if not context.trace_id.strip():
            raise ItemFeatureGeneratorError("trace_id is required")
        if not context.batch_run_id.strip():
            raise ItemFeatureGeneratorError("batch_run_id is required")
        if not context.item_generation_queue_id.strip():
            raise ItemFeatureGeneratorError("item_generation_queue_id is required")
        if not context.item_id.strip():
            raise ItemFeatureGeneratorError("item_id is required")
        if not context.semantic_config_version_id.strip():
            raise ItemFeatureGeneratorError("semantic_config_version_id is required")
        if not self._is_valid_feature_input_hash(context.feature_input_hash):
            raise ItemFeatureGeneratorError(
                "feature_input_hash must be 64-char hex string",
            )

        if not self.item_validation.item_exists(context.item_id):
            raise ItemFeatureGeneratorError(f"item not found: {context.item_id}")

        if context.item_semantic is None:
            raise ItemFeatureGeneratorError("item_semantic is required")
        if context.item_semantic.item_id != context.item_id:
            raise ItemFeatureGeneratorError(
                "item_semantic.item_id does not match context.item_id",
            )
        if (
            context.item_semantic.semantic_config_version_id
            != context.semantic_config_version_id
        ):
            raise ItemFeatureGeneratorError(
                "item_semantic.semantic_config_version_id does not match context",
            )

    def _is_valid_feature_input_hash(self, feature_input_hash: str) -> bool:
        return (
            len(feature_input_hash) == FEATURE_INPUT_HASH_LENGTH
            and _HEX_HASH_PATTERN.fullmatch(feature_input_hash) is not None
        )

    def _resolve_normalization_binding(self, semantic_config_version_id: str):
        try:
            binding = self.normalization_rules.get_active_normalization_binding(
                semantic_config_version_id,
            )
        except Exception as exc:
            raise ItemFeatureGeneratorError(
                f"normalization_rule lookup failed: {exc}",
                internal_error_code="GRS-CFG-006",
            ) from exc

        if binding is None:
            raise ItemFeatureGeneratorError(
                f"normalization_rule binding not found: {semantic_config_version_id}",
                internal_error_code="GRS-CFG-006",
            )
        return binding

    def _validate_feature_definition_coverage(
        self,
        semantic_config_version_id: str,
    ) -> None:
        active_codes = self.feature_definitions.list_active_feature_codes(
            semantic_config_version_id,
        )
        missing = [code for code in MVP_FEATURE_CODES if code not in active_codes]
        if missing:
            raise ItemFeatureGeneratorError(
                f"feature_definition missing axes: {', '.join(missing)}",
                internal_error_code="GRS-CFG-001",
            )

    def _should_skip(
        self,
        context: ItemFeatureGenerationContext,
        *,
        feature_normalization_version_id: str,
    ) -> bool:
        existing = self.item_feature_repository.find_by_idempotent_key(
            item_id=context.item_id,
            semantic_config_version_id=context.semantic_config_version_id,
            feature_input_hash=context.feature_input_hash,
            feature_normalization_version_id=feature_normalization_version_id,
        )
        if len(existing) != len(MVP_FEATURE_CODES):
            return False
        return all(row.raw_feature_value is not None for row in existing)

    def _concept_count(self, context: ItemFeatureGenerationContext) -> int:
        concepts = context.item_semantic.semantic_json.get("concepts")
        if isinstance(concepts, list):
            return len(concepts)
        return 0

    def _log_generation_summary(
        self,
        context: ItemFeatureGenerationContext,
        *,
        concept_count: int,
        rule_hit_count: int,
        raw_clip_count: int,
        status: GenerationStatus,
    ) -> None:
        self.logger.bind(
            trace_id=context.trace_id,
            batch_run_id=context.batch_run_id,
            item_id=context.item_id,
        ).info(
            "item_feature_generation_completed",
            concept_count=concept_count,
            rule_hit_count=rule_hit_count,
            raw_clip_count=raw_clip_count,
            status=status.value,
            module_id=self.module_id,
        )


def build_default_item_feature_generator() -> ItemFeatureGenerator:
    from .in_memory_repository import build_default_in_memory_repositories

    concept_rules, normalization_rules, feature_definitions, item_validation, item_feature_repo = (
        build_default_in_memory_repositories()
    )
    return ItemFeatureGenerator(
        concept_feature_rules=concept_rules,
        normalization_rules=normalization_rules,
        feature_definitions=feature_definitions,
        item_validation=item_validation,
        item_feature_repository=item_feature_repo,
    )
