"""MOD-RECO-012 pre_hard_filter sub-module implementation."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from reco.domain.recommendation.inputs import NgCondition
from reco.domain.semantic_extraction.models import HardFilterCandidate

from reco.application.candidate_retriever.errors import PreHardFilterError
from reco.application.candidate_retriever.models import (
    FilterPredicate,
    MergedFilterConditions,
    PoolRepresentation,
    PreFilteredItemPool,
)
from reco.application.candidate_retriever.ports import ItemRepositoryPort

if TYPE_CHECKING:
    from reco.application.recommendation_orchestrator.execution_context import (
        ExecutionContext,
    )

# request.ng_text の再正規化は api 正本（MOD-RECO-012）。attribute hard_filter のみ暫定抽出を残す。
_NG_SUFFIX_PATTERN = re.compile(
    r"(?:は|が|を|の)?"
    r"(?:NG|ＮＧ|ng|禁止|不可|ダメ|だめ|避けたい|避けて(?:ほしい|下さい|ください)|不要)"
    r"(?:[。．.!！]?)*$",
)
_KNOWN_NG_HINT_TOKENS: tuple[str, ...] = (
    "アルコール",
    "ワイン",
    "ビール",
    "日本酒",
    "お酒",
)


def run_pre_hard_filter(
    context: ExecutionContext,
    *,
    item_repository: ItemRepositoryPort,
) -> PreFilteredItemPool:
    """Execute Pre Hard Filter phase (§5.3 / §8.2)."""
    request = context.recommendation_request
    extraction = context.semantic_extraction_result
    if extraction is None:
        raise PreHardFilterError("semantic_extraction_result is required on execution_context")

    merged = _merge_filter_conditions(
        request.ng_condition,
        extraction.hard_filter_candidates,
    )
    if request.budget is not None:
        merged = MergedFilterConditions(
            budget_min=request.budget.budget_min,
            budget_max=request.budget.budget_max,
            ng_keywords=merged.ng_keywords,
            ng_categories=merged.ng_categories,
            hard_filter_values=merged.hard_filter_values,
        )

    predicate = FilterPredicate(
        merged_filter_conditions=merged,
        active_only=True,
        data_quality_rules={"require_image": True, "require_url": True},
    )

    try:
        total_before = item_repository.count_active_items()
        total_after = item_repository.count_filtered_items(predicate)
    except PreHardFilterError:
        raise
    except Exception as exc:  # noqa: BLE001 — DB 失敗を GRS-REC-008 へ集約
        raise PreHardFilterError(
            f"pre hard filter count failed for run: {context.run_id}",
        ) from exc

    return PreFilteredItemPool(
        representation=PoolRepresentation.PREDICATE,
        total_before_filter=total_before,
        total_after_filter=total_after,
        filter_predicate=predicate,
        applied_conditions=_build_applied_conditions_summary(merged),
    )


def _merge_filter_conditions(
    ng_condition: NgCondition | None,
    hard_filter_candidates: tuple[HardFilterCandidate, ...],
) -> MergedFilterConditions:
    """Merge request.ng_condition (primary) with hard_filter_candidates (§8.3.2)."""
    ng_keywords: list[str] = []
    ng_categories: list[str] = []
    hard_filter_values: list[str] = []

    if ng_condition is not None:
        # api 派生の ng_keywords / ng_categories を正とする（request.ng_text は再抽出しない）
        ng_keywords.extend(_normalize_tokens(ng_condition.ng_keywords))
        ng_categories.extend(_normalize_tokens(ng_condition.ng_categories))

    seen_values: set[str] = set()
    for candidate in hard_filter_candidates:
        value = candidate.filter_value.strip()
        if not value or value in seen_values:
            continue
        seen_values.add(value)
        hard_filter_values.append(value)
        if candidate.filter_type in {"ng_keyword", "keyword"}:
            ng_keywords.append(value)
        elif candidate.filter_type in {"ng_category", "category"}:
            ng_categories.append(value)
        elif candidate.filter_type == "attribute":
            # MOD-RECO-004 は ngText を attribute にする。predicate は ng_keywords 経由で効かせる。
            ng_keywords.extend(_effective_ng_keywords_from_text(value))

    return MergedFilterConditions(
        ng_keywords=tuple(_dedupe_preserve_order(ng_keywords)),
        ng_categories=tuple(_dedupe_preserve_order(ng_categories)),
        hard_filter_values=tuple(hard_filter_values),
    )


def _effective_ng_keywords_from_text(text: str) -> list[str]:
    """ngText / attribute 文から ILIKE に使える短いキーワードを抽出する。

    例: 「アルコールはNG」→「アルコール」。抽出不能時のみ全文を残す（従来互換）。
    """
    raw = text.strip()
    if not raw:
        return []

    keywords: list[str] = []
    stripped = _NG_SUFFIX_PATTERN.sub("", raw).strip(" 　、。．，,・")
    if stripped:
        keywords.append(stripped)
    for token in _KNOWN_NG_HINT_TOKENS:
        if token in raw and token not in keywords:
            keywords.append(token)
    if not keywords:
        keywords.append(raw)
    return _dedupe_preserve_order(keywords)


def _normalize_tokens(tokens: tuple[str, ...]) -> list[str]:
    return [token.strip() for token in tokens if token.strip()]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _build_applied_conditions_summary(
    merged: MergedFilterConditions,
) -> dict[str, object]:
    return {
        "budget_min": merged.budget_min,
        "budget_max": merged.budget_max,
        "ng_keyword_count": len(merged.ng_keywords),
        "ng_category_count": len(merged.ng_categories),
        "hard_filter_candidate_count": len(merged.hard_filter_values),
        "active_only": True,
    }
