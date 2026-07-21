"""BATCH-017 Import Summary Aggregator（MOD-BATCH-047 内包）.

仕様書 §6 / §9:
- fetched_count = api_call_log.item_count 合計（正本）
- item_count 全件 0 のときのみ staging_item 行数で補完可
- item_ranking / genre_search は diff 系 0 固定
- Feature / Embedding は同一 Run 完了時のみ非ゼロ
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from batch.application.import_summary.models import (
    AggregatedCounts,
    ApiCallLogRow,
    FeatureEmbeddingProgress,
    ImportSummaryInsertRow,
    ProductDiffRow,
    SkipFailCounts,
    SourceApi,
    StagingItemRow,
)

VALID_SOURCE_APIS: frozenset[str] = frozenset(
    {"item_search", "item_ranking", "genre_search", "attribute_search"}
)
ZERO_DIFF_SOURCE_APIS: frozenset[str] = frozenset({"item_ranking", "genre_search"})
DEFAULT_SOURCE = "rakuten"


def resolve_source_api(raw: str | None) -> SourceApi:
    """source_api を enum 検証して返す。"""

    value = (raw or "").strip()
    if value not in VALID_SOURCE_APIS:
        raise ValueError(f"invalid source_api: {raw!r}")
    return value  # type: ignore[return-value]


def aggregate_fetched_count(
    *,
    api_calls: Sequence[ApiCallLogRow],
    staging_items: Sequence[StagingItemRow],
    batch_run_id: str,
    source_api: SourceApi,
) -> int:
    """fetched_count を算出する（api_call_log 正本 / staging 補完）。"""

    matched = [
        row
        for row in api_calls
        if row.batch_run_id == batch_run_id and row.source_api == source_api
    ]
    if not matched:
        return 0

    total = sum(int(row.item_count) for row in matched)
    if total > 0:
        return total

    # 全 item_count=0 のときのみ staging_item 行数で補完
    if all(row.item_count == 0 for row in matched):
        return sum(
            1
            for row in staging_items
            if row.batch_run_id == batch_run_id and row.source_api == source_api
        )
    return 0


def aggregate_diff_counts(
    *,
    diffs: Sequence[ProductDiffRow],
    batch_run_id: str,
    source_api: SourceApi,
) -> tuple[int, int, int, int]:
    """new/updated/unchanged/unavailable を返す。ranking/genre は 0 固定。"""

    if source_api in ZERO_DIFF_SOURCE_APIS:
        return 0, 0, 0, 0

    new_count = 0
    updated_count = 0
    unchanged_count = 0
    unavailable_count = 0
    for row in diffs:
        if row.batch_run_id != batch_run_id or row.source_api != source_api:
            continue
        if row.diff_status == "new":
            new_count += 1
        elif row.diff_status == "updated":
            updated_count += 1
        elif row.diff_status == "unchanged":
            unchanged_count += 1
        elif row.diff_status == "unavailable":
            unavailable_count += 1
    return new_count, updated_count, unchanged_count, unavailable_count


def aggregate_feature_embedding_counts(
    progress: FeatureEmbeddingProgress,
) -> tuple[int, int]:
    """同一 Run 完了時のみ件数、未完了は 0。"""

    feature_count = (
        int(progress.feature_generated_count) if progress.feature_completed else 0
    )
    embedding_count = (
        int(progress.embedding_generated_count) if progress.embedding_completed else 0
    )
    return feature_count, embedding_count


def build_aggregated_counts(
    *,
    api_calls: Sequence[ApiCallLogRow],
    diffs: Sequence[ProductDiffRow],
    staging_items: Sequence[StagingItemRow],
    skip_fail: SkipFailCounts,
    progress: FeatureEmbeddingProgress,
    batch_run_id: str,
    source_api: SourceApi,
) -> AggregatedCounts:
    """全件数列を集計する。"""

    fetched = aggregate_fetched_count(
        api_calls=api_calls,
        staging_items=staging_items,
        batch_run_id=batch_run_id,
        source_api=source_api,
    )
    new_c, upd_c, unc_c, una_c = aggregate_diff_counts(
        diffs=diffs,
        batch_run_id=batch_run_id,
        source_api=source_api,
    )
    feature_c, embedding_c = aggregate_feature_embedding_counts(progress)
    return AggregatedCounts(
        fetched_count=fetched,
        new_count=new_c,
        updated_count=upd_c,
        unchanged_count=unc_c,
        unavailable_count=una_c,
        skipped_count=max(0, int(skip_fail.skipped_count)),
        failed_count=max(0, int(skip_fail.failed_count)),
        feature_generated_count=feature_c,
        embedding_generated_count=embedding_c,
    )


def build_insert_row(
    *,
    counts: AggregatedCounts,
    batch_run_id: str,
    source_api: SourceApi,
    summarized_at: datetime,
    source: str = DEFAULT_SOURCE,
) -> ImportSummaryInsertRow:
    """IF-DB-BATCH-017 用 INSERT 行を構築する。"""

    return ImportSummaryInsertRow(
        batch_run_id=batch_run_id,
        source=source,
        source_api=source_api,
        fetched_count=counts.fetched_count,
        new_count=counts.new_count,
        updated_count=counts.updated_count,
        unchanged_count=counts.unchanged_count,
        unavailable_count=counts.unavailable_count,
        skipped_count=counts.skipped_count,
        failed_count=counts.failed_count,
        feature_generated_count=counts.feature_generated_count,
        embedding_generated_count=counts.embedding_generated_count,
        summarized_at=summarized_at,
    )
