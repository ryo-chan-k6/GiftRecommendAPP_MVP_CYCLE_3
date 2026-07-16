"""Product Diff Detector — hash 比較のみ（再算出禁止）.

判定順序（仕様書 §9.2 / §18.1 No.9）:
1. normalized_hash NULL / 不正長 → 当該行失敗（判定行を書かない）
2. unavailable 条件 → unavailable（hash 比較より優先）
3. item 未存在 → new
4. old_hash <> new_hash → updated
5. 同一 → unchanged
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from batch.application.product_diff.models import DiffJudgment, DiffStatus, ItemSeed, StagingItemSeed

# BATCH-005 が確定する SHA-256 hex（64 桁）
EXPECTED_HASH_LENGTH = 64

# Staging 必須項目（欠落再検知 → unavailable、§18.1 No.9 (a)）
_REQUIRED_STAGING_FIELDS: tuple[str, ...] = (
    "external_item_code",
    "item_name",
    "item_url",
    "price",
)


class ProductDiffCompareError(Exception):
    """compare 失敗（判定行を書かない）."""

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class _UnavailableCheck:
    reason: str


def is_valid_normalized_hash(value: str | None) -> bool:
    """Return True when hash is a non-empty SHA-256 hex string."""

    if value is None:
        return False
    if len(value) != EXPECTED_HASH_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _check_unavailable(staging: StagingItemSeed) -> _UnavailableCheck | None:
    """§18.1 No.9: (a) 必須欠落 (b) availability=0 (c) Validator/取得不能フラグ."""

    if staging.validation_failed or staging.fetch_unavailable:
        return _UnavailableCheck(reason="validation_or_fetch_unavailable")

    if staging.availability == 0:
        return _UnavailableCheck(reason="availability_zero")

    for field_name in _REQUIRED_STAGING_FIELDS:
        value = getattr(staging, field_name, None)
        if value is None:
            return _UnavailableCheck(reason=f"missing_{field_name}")
        if isinstance(value, str) and value.strip() == "":
            return _UnavailableCheck(reason=f"missing_{field_name}")

    return None


def compare_staging_to_item(
    *,
    staging: StagingItemSeed,
    item: ItemSeed | None,
    judged_at: datetime | None = None,
) -> DiffJudgment:
    """Compare existing hashes only. Never recalculates normalized_hash."""

    if not is_valid_normalized_hash(staging.normalized_hash):
        raise ProductDiffCompareError(
            code="GRS-BAT-007",
            message="normalized_hash is NULL or invalid; re-run BATCH-005",
        )

    new_hash = str(staging.normalized_hash)
    at = judged_at or datetime.now(UTC)

    unavailable = _check_unavailable(staging)
    if unavailable is not None:
        old_hash = item.normalized_hash if item is not None else None
        return DiffJudgment(
            staging_item_id=staging.staging_item_id,
            external_item_code=staging.external_item_code,
            diff_status="unavailable",
            old_hash=old_hash,
            new_hash=new_hash,
            judged_at=at,
        )

    if item is None:
        return DiffJudgment(
            staging_item_id=staging.staging_item_id,
            external_item_code=staging.external_item_code,
            diff_status="new",
            old_hash=None,
            new_hash=new_hash,
            judged_at=at,
        )

    old_hash = item.normalized_hash
    status: DiffStatus
    if old_hash is None or old_hash != new_hash:
        status = "updated"
    else:
        status = "unchanged"

    return DiffJudgment(
        staging_item_id=staging.staging_item_id,
        external_item_code=staging.external_item_code,
        diff_status=status,
        old_hash=old_hash,
        new_hash=new_hash,
        judged_at=at,
    )
