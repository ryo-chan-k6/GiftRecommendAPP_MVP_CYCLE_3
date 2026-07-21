"""BATCH-008 conflict resolution (§9.1 / §9.3 / BATCH-004 §18.1.1)."""

from __future__ import annotations

from collections.abc import Sequence

from batch.application.item_active_status.models import (
    ActiveStatusValue,
    CandidateRow,
    ResolveDecision,
    StatusProposal,
)

RESTRICTION_RANK: dict[ActiveStatusValue, int] = {
    "active": 0,
    "inactive": 1,
    "unavailable": 2,
    "excluded": 3,
}

# 復帰明示（テーブル定義書 §6.1）
REACTIVATION_DETECTION_BASIS = "api_success"
REACTIVATION_REASON_CODE = "available"


def candidate_allows_reactivation(row: CandidateRow) -> bool:
    """Return True when candidate explicitly says fetch success + sellable."""

    return (
        row.candidate_active_status == "active"
        and row.detection_basis == REACTIVATION_DETECTION_BASIS
        and row.reason_code == REACTIVATION_REASON_CODE
    )


def proposal_from_candidate(row: CandidateRow) -> StatusProposal:
    return StatusProposal(
        source_kind="candidate",
        active_status=row.candidate_active_status,
        event_at=row.detected_at,
        candidate_id=row.candidate_id,
        allows_reactivation=candidate_allows_reactivation(row),
    )


def pick_winning_proposal(proposals: Sequence[StatusProposal]) -> StatusProposal | None:
    """Pick strongest restriction; tie-break by newer event_at."""

    if not proposals:
        return None
    return max(
        proposals,
        key=lambda p: (RESTRICTION_RANK[p.active_status], p.event_at),
    )


def resolve_for_item(
    *,
    source: str,
    external_item_code: str,
    current_status: ActiveStatusValue,
    proposals: Sequence[StatusProposal],
    candidate_ids_for_item: Sequence[str],
) -> ResolveDecision:
    """Resolve A∪B proposals for one item.

    Reactivation to active is allowed only when a winning (or sole active)
    candidate explicitly allows reactivation. Diff never reactivates alone.
    """

    if not proposals:
        return ResolveDecision(
            source=source,
            external_item_code=external_item_code,
            adopted_status=None,
            adopt=False,
            skip_item_update=True,
            discarded_candidate_ids=tuple(candidate_ids_for_item),
            reason="no_proposals",
        )

    winner = pick_winning_proposal(proposals)
    assert winner is not None

    adopted = winner.active_status
    reactivation = False

    # 復帰ガード: 提案が active のとき、候補の明示復帰のみ許可
    if adopted == "active":
        reactivation_ok = any(
            p.allows_reactivation and p.active_status == "active" for p in proposals
        )
        # より制限の強い提案が無い場合のみ active を採用
        stronger = [
            p
            for p in proposals
            if RESTRICTION_RANK[p.active_status] > RESTRICTION_RANK["active"]
        ]
        if stronger:
            winner = pick_winning_proposal(stronger)
            assert winner is not None
            adopted = winner.active_status
            reactivation = False
        elif not reactivation_ok and current_status != "active":
            # Diff 等の active 以外しかなく、明示復帰候補が無い → 復帰しない
            # active 提案があるが allows_reactivation=False（通常ありえない for candidate）
            # Diff 経路は active を提案しない（§9.2）。ここは候補非明示を拒否。
            return ResolveDecision(
                source=source,
                external_item_code=external_item_code,
                adopted_status=None,
                adopt=False,
                skip_item_update=True,
                discarded_candidate_ids=tuple(candidate_ids_for_item),
                reason="reactivation_blocked",
            )
        else:
            reactivation = reactivation_ok and current_status != "active"

    winning_candidate_id = winner.candidate_id if winner.source_kind == "candidate" else None
    superseded: list[str] = []
    discarded: list[str] = []
    for cid in candidate_ids_for_item:
        if winning_candidate_id and cid == winning_candidate_id:
            continue
        # 採用が候補以外（Diff）または別候補に負けた
        if winning_candidate_id is None:
            # Diff が勝った場合、全候補は superseded（制限側採用）
            superseded.append(cid)
        else:
            superseded.append(cid)

    skip = adopted == current_status
    return ResolveDecision(
        source=source,
        external_item_code=external_item_code,
        adopted_status=adopted,
        adopt=True,
        skip_item_update=skip,
        winning_candidate_id=winning_candidate_id,
        superseded_candidate_ids=tuple(superseded),
        discarded_candidate_ids=tuple(discarded),
        reactivation=reactivation,
        reason="adopted" if not skip else "already_same",
    )
