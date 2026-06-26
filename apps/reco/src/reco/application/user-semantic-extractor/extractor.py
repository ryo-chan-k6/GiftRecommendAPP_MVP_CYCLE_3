"""MOD-RECO-004 User Semantic Extractor implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from reco.domain.semantic_extraction import HardFilterCandidate, SemanticExtractionResult
from reco.infrastructure.external_ai.client import ExternalAiClient, ScaffoldExternalAiClient
from reco.infrastructure.logger.logger import RecoLogger, ScaffoldRecoLogger

from .constants import (
    CONFIDENCE_ADOPTION_THRESHOLD,
    DEFAULT_EXTRACTION_METHOD,
    MODULE_ID,
    PHASE_NAME,
)
from .errors import SemanticExtractError
from .llm_classifier import LlmExtractionRequest, extract_with_llm, should_invoke_llm
from .ports import RunValidationPort, SemanticCatalogPort, UserSemanticRepositoryPort
from .rule_engine import (
    apply_rules,
    collect_text_segments,
    dedupe_by_concept_code,
    filter_by_confidence,
    merge_concept_lists,
    with_extraction_method,
)

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )


@dataclass
class UserSemanticExtractor:
    """PipelineModulePort implementation for semantic concept extraction."""

    catalog: SemanticCatalogPort
    run_validation: RunValidationPort
    user_semantic_repository: UserSemanticRepositoryPort
    llm_client: ExternalAiClient = field(default_factory=ScaffoldExternalAiClient)
    logger: RecoLogger = field(default_factory=ScaffoldRecoLogger)
    module_id: str = MODULE_ID
    phase_name: str = PHASE_NAME

    def execute(self, context: ExecutionContext) -> ExecutionContext:
        result = self.extract(context)
        _attach_semantic_extraction_result(context, result)
        context.completed_modules.append(self.module_id)
        return context

    def extract(self, context: ExecutionContext) -> SemanticExtractionResult:
        run_id, semantic_version_id = self._validate_context(context)
        request = context.recommendation_request

        hard_filter_candidates = self._build_hard_filter_candidates(request)
        segments = collect_text_segments(request)

        active_concepts = self.catalog.list_active_concepts(semantic_version_id)
        rules = self.catalog.list_rules(semantic_version_id)
        rule_concepts = apply_rules(
            segments,
            rules=rules,
            active_concepts=active_concepts,
        )

        llm_concepts: list = []
        llm_used = False
        if should_invoke_llm(segments, rule_concepts):
            llm_used = True
            try:
                llm_concepts = extract_with_llm(
                    LlmExtractionRequest(
                        segments=segments,
                        relationship_code=request.relationship.relationship_code,
                        occasion_code=request.occasion.occasion_code,
                    ),
                    client=self.llm_client,
                    active_concepts=active_concepts,
                )
            except Exception as exc:
                raise SemanticExtractError(
                    f"external AI semantic extraction failed: {exc}",
                ) from exc

        adopted = filter_by_confidence(
            merge_concept_lists(rule_concepts, llm_concepts),
            threshold=CONFIDENCE_ADOPTION_THRESHOLD,
        )
        if llm_used and not llm_concepts and segments:
            adopted = filter_by_confidence(rule_concepts, threshold=CONFIDENCE_ADOPTION_THRESHOLD)

        normalized = [
            with_extraction_method(concept, DEFAULT_EXTRACTION_METHOD)
            if concept.extraction_method in {"keyword", "phrase", "pattern"}
            and llm_used
            else concept
            for concept in adopted
        ]
        concepts = dedupe_by_concept_code(normalized)

        extracted_json = {"concepts": [concept.to_json_dict() for concept in concepts]}
        if self.user_semantic_repository.exists_for_run(run_id):
            raise SemanticExtractError(
                f"user_semantic row already exists for run: {run_id}",
            )

        try:
            persisted = self.user_semantic_repository.insert(
                recommendation_run_id=run_id,
                semantic_config_version_id=semantic_version_id,
                extracted_semantic_json=extracted_json,
            )
        except Exception as exc:
            raise SemanticExtractError(
                f"user_semantic insert failed: {exc}",
            ) from exc

        self._log_extraction_summary(
            context,
            concept_count=len(concepts),
            rule_hit_count=len(rule_concepts),
            llm_used=llm_used,
        )

        return SemanticExtractionResult(
            concepts=concepts,
            hard_filter_candidates=hard_filter_candidates,
            user_semantic_id=persisted.user_semantic_id,
            semantic_config_version_id=semantic_version_id,
        )

    def _validate_context(self, context: ExecutionContext) -> tuple[str, str]:
        run_id = context.run_id
        if run_id is None:
            raise SemanticExtractError("run_id is required on execution_context")

        semantic_version_id = context.config_versions.get("semantic_config_version_id")
        if not semantic_version_id:
            raise SemanticExtractError(
                "semantic_config_version_id is required on execution_context.config_versions",
            )

        request = context.recommendation_request
        if request.relationship is None or request.occasion is None:
            raise SemanticExtractError(
                "relationship and occasion are required on recommendation_request",
            )

        run_version_id = self.run_validation.get_semantic_config_version_id(run_id)
        if run_version_id is None:
            raise SemanticExtractError(f"recommendation_run not found: {run_id}")
        if run_version_id != semantic_version_id:
            raise SemanticExtractError(
                "semantic_config_version_id mismatch between run and execution_context",
            )

        return run_id, semantic_version_id

    def _build_hard_filter_candidates(self, request) -> tuple[HardFilterCandidate, ...]:
        ng = request.ng_condition
        if ng is None:
            return ()

        candidates: list[HardFilterCandidate] = []
        for keyword in ng.ng_keywords:
            normalized = keyword.strip()
            if not normalized:
                continue
            candidates.append(
                HardFilterCandidate(
                    filter_type="attribute",
                    filter_value=normalized,
                    evidence_text=normalized,
                    confidence=0.95,
                    source_type="ng_condition",
                )
            )

        for category in ng.ng_categories:
            normalized = category.strip()
            if not normalized:
                continue
            candidates.append(
                HardFilterCandidate(
                    filter_type="category",
                    filter_value=normalized,
                    evidence_text=normalized,
                    confidence=0.95,
                    source_type="ng_condition",
                )
            )

        if ng.ng_text and ng.ng_text.strip():
            candidates.append(
                HardFilterCandidate(
                    filter_type="attribute",
                    filter_value=ng.ng_text.strip(),
                    evidence_text=ng.ng_text.strip(),
                    confidence=0.90,
                    source_type="ng_condition",
                )
            )

        return tuple(candidates)

    def _log_extraction_summary(
        self,
        context: ExecutionContext,
        *,
        concept_count: int,
        rule_hit_count: int,
        llm_used: bool,
    ) -> None:
        self.logger.bind(trace_id=context.trace_id, run_id=context.run_id).info(
            "semantic_extraction_completed",
            concept_count=concept_count,
            rule_hit_count=rule_hit_count,
            llm_used=llm_used,
            module_id=self.module_id,
        )


def _attach_semantic_extraction_result(
    context: ExecutionContext,
    result: SemanticExtractionResult,
) -> None:
    context.semantic_extraction_result = result


def build_default_user_semantic_extractor() -> UserSemanticExtractor:
    from .in_memory_repository import build_default_in_memory_repositories

    catalog, run_validation, user_semantic_repo = build_default_in_memory_repositories()
    return UserSemanticExtractor(
        catalog=catalog,
        run_validation=run_validation,
        user_semantic_repository=user_semantic_repo,
    )
