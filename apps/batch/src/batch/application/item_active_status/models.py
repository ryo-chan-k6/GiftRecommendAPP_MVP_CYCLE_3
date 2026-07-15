"""BATCH-008 Item Active Status — domain models and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ItemActiveStatusRunStatus = Literal["succeeded", "partially_succeeded", "failed"]
ProposalSource = Literal["diff", "candidate"]
ActiveStatusValue = Literal["active", "inactive", "unavailable", "excluded"]
CandidateStatusValue = Literal["detected", "applied", "superseded", "discarded"]


@dataclass(frozen=True)
class ApplyPlan:
    """Resolved apply scope for BATCH-008 (plan phase output)."""

    source: str = "rakuten"
    batch_run_id: str | None = None
    external_item_codes: tuple[str, ...] = ()
    max_items: int | None = None


@dataclass(frozen=True)
class ItemRow:
    """In-memory item row for active_status application."""

    source: str
    external_item_code: str
    active_status: ActiveStatusValue
    item_id: str | None = None
    is_active: bool = True

    @property
    def idempotency_key(self) -> tuple[str, str]:
        return (self.source, self.external_item_code)


@dataclass(frozen=True)
class CandidateRow:
    """item_active_status_candidate row (Reader / Applier input)."""

    candidate_id: str
    batch_run_id: str
    source: str
    external_item_code: str
    candidate_active_status: ActiveStatusValue
    candidate_status: CandidateStatusValue
    detected_at: datetime
    detection_basis: str | None = None
    reason_code: str | None = None
    item_id: str | None = None
    applied_at: datetime | None = None


@dataclass(frozen=True)
class DiffSuggestion:
    """product_diff_result derived restriction proposal (§9.2)."""

    product_diff_result_id: str
    batch_run_id: str
    source: str
    external_item_code: str
    diff_status: str
    proposed_active_status: ActiveStatusValue | None
    judged_at: datetime


@dataclass(frozen=True)
class StatusProposal:
    """Normalized proposal for conflict resolution."""

    source_kind: ProposalSource
    active_status: ActiveStatusValue
    event_at: datetime
    candidate_id: str | None = None
    diff_id: str | None = None
    allows_reactivation: bool = False


@dataclass(frozen=True)
class ResolveDecision:
    """Per-item resolve outcome."""

    source: str
    external_item_code: str
    adopted_status: ActiveStatusValue | None
    adopt: bool
    skip_item_update: bool
    winning_candidate_id: str | None = None
    superseded_candidate_ids: tuple[str, ...] = ()
    discarded_candidate_ids: tuple[str, ...] = ()
    reactivation: bool = False
    reason: str = ""


@dataclass
class ItemActiveStatusResult:
    """Finalize-phase summary for BATCH-008."""

    batch_id: str
    job_run_id: str
    status: ItemActiveStatusRunStatus
    completed_phases: list[str] = field(default_factory=list)
    failed_item_codes: list[str] = field(default_factory=list)
    succeeded_item_codes: list[str] = field(default_factory=list)
    error_codes: list[str] = field(default_factory=list)
    diff_input_count: int = 0
    candidate_input_count: int = 0
    item_status_updated_count: int = 0
    candidate_applied_count: int = 0
    candidate_superseded_count: int = 0
    candidate_discarded_count: int = 0
    reactivation_count: int = 0
