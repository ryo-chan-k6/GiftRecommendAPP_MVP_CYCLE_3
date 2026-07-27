"""Staging Validator (仕様書 §8.2 validate)."""

from __future__ import annotations

from batch.application.raw_staging.models import (
    ItemTransformBundle,
    RawTransformResult,
    StagingGenreRow,
    StagingRankingSignalRow,
)


class StagingValidationError(Exception):
    """Raised when validation rejects candidates (GRS-VAL-*)."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def validate_item_bundle(bundle: ItemTransformBundle) -> None:
    """Validate one staging_item (+ images) candidate."""

    item = bundle.item
    if not item.external_item_code:
        raise StagingValidationError(code="GRS-VAL-001", message="external_item_code required")
    if not item.item_name:
        raise StagingValidationError(code="GRS-VAL-001", message="item_name required")
    if not item.item_url:
        raise StagingValidationError(code="GRS-VAL-001", message="item_url required")
    if item.price is None or item.price < 0:
        raise StagingValidationError(code="GRS-VAL-002", message="price must be >= 0")
    if not item.normalized_hash or len(item.normalized_hash) != 64:
        raise StagingValidationError(code="GRS-VAL-003", message="normalized_hash invalid")
    if item.diff_status is not None:
        raise StagingValidationError(
            code="GRS-VAL-004",
            message="diff_status must remain NULL in BATCH-005",
        )

    primary_count = sum(1 for img in bundle.images if img.is_primary_candidate)
    if primary_count > 1:
        raise StagingValidationError(
            code="GRS-VAL-005",
            message="is_primary_candidate must be at most one per item",
        )
    for img in bundle.images:
        if not img.image_url:
            raise StagingValidationError(code="GRS-VAL-001", message="image_url required")
        if img.image_size_type not in {"small", "medium"}:
            raise StagingValidationError(code="GRS-VAL-002", message="invalid image_size_type")
        if img.display_order < 0:
            raise StagingValidationError(code="GRS-VAL-002", message="display_order must be >= 0")


def validate_ranking_row(row: StagingRankingSignalRow) -> None:
    """Validate one staging_ranking_signal candidate."""

    if not row.external_item_code:
        raise StagingValidationError(code="GRS-VAL-001", message="external_item_code required")
    if row.rank < 1:
        raise StagingValidationError(code="GRS-VAL-002", message="rank must be >= 1")
    if row.external_genre_id < 0:
        raise StagingValidationError(code="GRS-VAL-002", message="external_genre_id must be >= 0")
    if not row.period or len(row.period) > 32:
        raise StagingValidationError(code="GRS-VAL-002", message="period invalid")
    if row.last_build_date is None:
        raise StagingValidationError(code="GRS-VAL-001", message="last_build_date required")


def validate_genre_row(row: StagingGenreRow) -> None:
    """Validate one staging_genre candidate."""

    if not row.source:
        raise StagingValidationError(code="GRS-VAL-001", message="source required")
    if row.external_genre_id < 0:
        raise StagingValidationError(code="GRS-VAL-002", message="external_genre_id must be >= 0")
    if not row.genre_name:
        raise StagingValidationError(code="GRS-VAL-001", message="genre_name required")
    if row.genre_level < 0 or row.genre_level > 5:
        raise StagingValidationError(code="GRS-VAL-002", message="genre_level out of range")
    if (
        row.parent_external_genre_id is not None
        and row.parent_external_genre_id == row.external_genre_id
    ):
        raise StagingValidationError(
            code="GRS-VAL-002",
            message="parent_external_genre_id must not equal external_genre_id",
        )


def validate_transform_result(result: RawTransformResult) -> RawTransformResult:
    """Validate all staging candidates in a Raw.

    items が空でも ranking_rows / genre_rows があれば受理する。
    """

    if result.skipped:
        return result

    seen_item_codes: set[str] = set()
    for bundle in result.items:
        code = bundle.item.external_item_code
        if code in seen_item_codes:
            raise StagingValidationError(
                code="GRS-VAL-006",
                message=f"duplicate itemCode in raw: {code}",
            )
        seen_item_codes.add(code)
        validate_item_bundle(bundle)

    seen_ranks: set[int] = set()
    for row in result.ranking_rows:
        if row.rank in seen_ranks:
            raise StagingValidationError(
                code="GRS-VAL-006",
                message=f"duplicate rank in raw: {row.rank}",
            )
        seen_ranks.add(row.rank)
        validate_ranking_row(row)

    seen_genre_ids: set[int] = set()
    for row in result.genre_rows:
        if row.external_genre_id in seen_genre_ids:
            raise StagingValidationError(
                code="GRS-VAL-006",
                message=f"duplicate external_genre_id in raw: {row.external_genre_id}",
            )
        seen_genre_ids.add(row.external_genre_id)
        validate_genre_row(row)

    if not result.items and not result.ranking_rows and not result.genre_rows:
        raise StagingValidationError(
            code="GRS-VAL-001",
            message="no valid staging rows in raw",
        )
    return result
