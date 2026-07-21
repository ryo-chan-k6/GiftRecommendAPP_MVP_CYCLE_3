"""MOD-RECO-026 Item Semantic Generator implementation."""

from __future__ import annotations

from dataclasses import dataclass, field

from reco.domain.semantic_extraction import ExtractedSemanticConcept
from reco.infrastructure.external_ai.client import ExternalAiClient, ScaffoldExternalAiClient
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import (
    CONFIDENCE_ADOPTION_THRESHOLD,
    DEFAULT_EXTRACTION_METHOD,
    MODULE_ID,
)
from .errors import ItemSemanticGeneratorError
from .input_hash import compute_semantic_input_hash
from .llm_classifier import LlmExtractionRequest, extract_with_llm, should_invoke_llm
from .models import (
    GenerationStatus,
    ItemSemanticGenerationContext,
    ItemSemanticGenerationResult,
)
from .ports import (
    ItemSemanticRepositoryPort,
    ItemValidationPort,
    SemanticCatalogPort,
    SemanticConfigVersionPort,
)
from .rule_engine import (
    apply_rules,
    apply_source_type_confidence_adjustment,
    collect_text_segments,
    dedupe_by_concept_code,
    filter_by_confidence,
    merge_concept_lists,
    with_extraction_method,
)


@dataclass
class ItemSemanticGenerator:
    """Batch port implementation for Item Semantic Concept extraction."""

    catalog: SemanticCatalogPort
    item_validation: ItemValidationPort
    semantic_config_version: SemanticConfigVersionPort
    item_semantic_repository: ItemSemanticRepositoryPort
    llm_client: ExternalAiClient = field(default_factory=ScaffoldExternalAiClient)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID

    def generate_item_semantic(
        self,
        context: ItemSemanticGenerationContext,
    ) -> ItemSemanticGenerationResult:
        self._validate_context(context)
        input_hash = compute_semantic_input_hash(context)

        if context.skip_if_unchanged:
            existing = self.item_semantic_repository.find_by_item_and_version(
                item_id=context.item_id,
                semantic_config_version_id=context.semantic_config_version_id,
            )
            if existing is not None and existing.semantic_input_hash == input_hash:
                return ItemSemanticGenerationResult(
                    status=GenerationStatus.SKIPPED,
                    semantic_json=existing.semantic_json,
                    item_semantic_id=existing.item_semantic_id,
                    skip_reason="semantic_input_unchanged",
                )

        segments = collect_text_segments(context)
        active_concepts = self.catalog.list_active_concepts(context.semantic_config_version_id)
        rules = self.catalog.list_rules(context.semantic_config_version_id)
        rule_concepts = apply_rules(
            segments,
            rules=rules,
            active_concepts=active_concepts,
        )
        rule_concepts = apply_source_type_confidence_adjustment(rule_concepts)

        llm_concepts: list[ExtractedSemanticConcept] = []
        llm_used = False
        if should_invoke_llm(context, segments, rule_concepts):
            llm_used = True
            try:
                llm_concepts = extract_with_llm(
                    LlmExtractionRequest(
                        segments=segments,
                        item_id=context.item_id,
                    ),
                    client=self.llm_client,
                    active_concepts=active_concepts,
                )
                llm_concepts = apply_source_type_confidence_adjustment(llm_concepts)
            except Exception as exc:
                raise ItemSemanticGeneratorError(
                    f"external AI item semantic extraction failed: {exc}",
                    internal_error_code="GRS-LLM-100",
                ) from exc

        adopted = filter_by_confidence(
            merge_concept_lists(rule_concepts, llm_concepts),
            threshold=CONFIDENCE_ADOPTION_THRESHOLD,
        )
        normalized = [
            with_extraction_method(concept, DEFAULT_EXTRACTION_METHOD)
            if concept.extraction_method in {"keyword", "phrase", "pattern"} and llm_used
            else concept
            for concept in adopted
        ]
        concepts = dedupe_by_concept_code(normalized)
        semantic_json: dict[str, object] = {
            "concepts": [concept.to_json_dict() for concept in concepts],
        }

        try:
            persisted = self.item_semantic_repository.upsert(
                item_id=context.item_id,
                semantic_config_version_id=context.semantic_config_version_id,
                semantic_json=semantic_json,
                semantic_input_hash=input_hash,
            )
        except Exception as exc:
            raise ItemSemanticGeneratorError(
                f"item_semantic upsert failed: {exc}",
            ) from exc

        self._log_generation_summary(
            context,
            concept_count=len(concepts),
            rule_hit_count=len(rule_concepts),
            llm_used=llm_used,
            status=GenerationStatus.GENERATED,
        )

        return ItemSemanticGenerationResult(
            status=GenerationStatus.GENERATED,
            semantic_json=semantic_json,
            item_semantic_id=persisted.item_semantic_id,
        )

    def _validate_context(self, context: ItemSemanticGenerationContext) -> None:
        if not context.trace_id.strip():
            raise ItemSemanticGeneratorError("trace_id is required")
        if not context.batch_run_id.strip():
            raise ItemSemanticGeneratorError("batch_run_id is required")
        if not context.item_generation_queue_id.strip():
            raise ItemSemanticGeneratorError("item_generation_queue_id is required")
        if not context.item_id.strip():
            raise ItemSemanticGeneratorError("item_id is required")
        if not context.semantic_config_version_id.strip():
            raise ItemSemanticGeneratorError("semantic_config_version_id is required")

        if not self.item_validation.item_exists(context.item_id):
            raise ItemSemanticGeneratorError(
                f"item not found: {context.item_id}",
            )

        if not self.semantic_config_version.is_valid_version(context.semantic_config_version_id):
            raise ItemSemanticGeneratorError(
                f"invalid semantic_config_version_id: {context.semantic_config_version_id}",
                internal_error_code="GRS-CFG-001",
            )

    def _log_generation_summary(
        self,
        context: ItemSemanticGenerationContext,
        *,
        concept_count: int,
        rule_hit_count: int,
        llm_used: bool,
        status: GenerationStatus,
    ) -> None:
        self.logger.bind(
            trace_id=context.trace_id,
            batch_run_id=context.batch_run_id,
            item_id=context.item_id,
        ).info(
            "item_semantic_generation_completed",
            concept_count=concept_count,
            rule_hit_count=rule_hit_count,
            llm_used=llm_used,
            status=status.value,
            module_id=self.module_id,
        )


def build_default_item_semantic_generator() -> ItemSemanticGenerator:
    from .in_memory_repository import build_default_in_memory_repositories

    catalog, item_validation, version_validation, item_semantic_repo = (
        build_default_in_memory_repositories()
    )
    return ItemSemanticGenerator(
        catalog=catalog,
        item_validation=item_validation,
        semantic_config_version=version_validation,
        item_semantic_repository=item_semantic_repo,
    )
