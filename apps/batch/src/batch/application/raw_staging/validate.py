"""Staging Validator (仕様書 §8.2 validate)."""

from __future__ import annotations

from batch.application.raw_staging.models import ItemTransformBundle, RawTransformResult


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


def validate_transform_result(result: RawTransformResult) -> tuple[ItemTransformBundle, ...]:
    """Validate all items in a Raw; reject duplicate itemCodes within the same Raw."""

    if result.skipped:
        return ()

    seen: set[str] = set()
    accepted: list[ItemTransformBundle] = []
    for bundle in result.items:
        code = bundle.item.external_item_code
        if code in seen:
            raise StagingValidationError(
                code="GRS-VAL-006",
                message=f"duplicate itemCode in raw: {code}",
            )
        seen.add(code)
        validate_item_bundle(bundle)
        accepted.append(bundle)
    return tuple(accepted)
