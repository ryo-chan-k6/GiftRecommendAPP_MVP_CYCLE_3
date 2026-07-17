"""Registration evaluation: meaning_input_diff / generation_type (§9.2 / §9.3)."""

from __future__ import annotations

from batch.application.item_generation_queue.models import (
    ItemRow,
    MeaningSnapshot,
    ProductDiffRow,
    RegistrationDecision,
)


def meaning_input_diff(
    *,
    current: MeaningSnapshot,
    previous: MeaningSnapshot | None,
) -> bool:
    """Batch 内非永続 concept: True when any meaning-affecting column changed."""

    if previous is None:
        return False
    return current != previous


def non_meaning_only_change(*, item: ItemRow, diff: ProductDiffRow) -> bool:
    """True when only price / url / review / availability changed (§9.2)."""

    if diff.previous_price is None and diff.previous_item_url is None:
        return False

    meaning_changed = meaning_input_diff(
        current=item.meaning_snapshot(),
        previous=diff.previous_meaning,
    )
    if meaning_changed:
        return False

    non_meaning_changed = False
    if diff.previous_price is not None and item.price != diff.previous_price:
        non_meaning_changed = True
    if diff.previous_item_url is not None and item.item_url != diff.previous_item_url:
        non_meaning_changed = True
    if diff.previous_review_average is not None and item.review_average != diff.previous_review_average:
        non_meaning_changed = True
    if diff.previous_review_count is not None and item.review_count != diff.previous_review_count:
        non_meaning_changed = True
    if diff.previous_availability is not None and item.availability != diff.previous_availability:
        non_meaning_changed = True
    return non_meaning_changed


def resolve_generation_type(
    *,
    diff: ProductDiffRow,
    meaning_changed: bool,
    hash_changed: bool,
) -> str | None:
    """§9.3 generation_type 選定. Returns None when MVP import should skip."""

    if diff.feature_input_hash_only or diff.embedding_only:
        return None

    if diff.diff_status == "new":
        return "semantic"

    if meaning_changed or (hash_changed and not diff.config_version_only):
        return "semantic"

    if diff.config_version_only and not meaning_changed:
        return "feature"

    if hash_changed:
        return "semantic"

    return None


def evaluate_registration(*, item: ItemRow, diff: ProductDiffRow) -> RegistrationDecision:
    """§9.2 登録条件評価."""

    if diff.diff_status == "unchanged":
        return RegistrationDecision(should_register=False, skip_reason="unchanged")

    if diff.diff_status == "unavailable":
        return RegistrationDecision(should_register=False, skip_reason="unavailable")

    if diff.diff_status == "new":
        return RegistrationDecision(
            should_register=True,
            generation_type="semantic",
            meaning_input_diff=True,
        )

    meaning_changed = meaning_input_diff(
        current=item.meaning_snapshot(),
        previous=diff.previous_meaning,
    )
    hash_changed = (
        diff.old_hash is not None
        and diff.new_hash is not None
        and diff.old_hash != diff.new_hash
    )

    if diff.feature_input_hash_only or diff.embedding_only:
        return RegistrationDecision(
            should_register=False,
            skip_reason="mvp_partial_regen_not_supported",
            meaning_input_diff=meaning_changed,
        )

    if non_meaning_only_change(item=item, diff=diff):
        return RegistrationDecision(
            should_register=False,
            skip_reason="non_meaning_only",
            meaning_input_diff=False,
            non_meaning_only=True,
        )

    generation_type = resolve_generation_type(
        diff=diff,
        meaning_changed=meaning_changed,
        hash_changed=hash_changed,
    )
    if generation_type is None:
        return RegistrationDecision(
            should_register=False,
            skip_reason="no_registration_trigger",
            meaning_input_diff=meaning_changed,
        )

    return RegistrationDecision(
        should_register=True,
        generation_type=generation_type,  # type: ignore[arg-type]
        meaning_input_diff=meaning_changed,
    )
