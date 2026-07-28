"""BATCH-008 商品有効状態更新ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → read_diff → read_candidate → resolve → apply_item → apply_candidate → finalize
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone

from batch.application.item_active_status.models import (
    ApplyPlan,
    CandidateRow,
    DiffSuggestion,
    ItemActiveStatusResult,
    StatusProposal,
)
from batch.application.item_active_status.repositories import ItemActiveStatusRepositories
from batch.application.item_active_status.resolve import (
    proposal_from_candidate,
    resolve_for_item,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-008"
ITEM_ACTIVE_STATUS_PHASES: tuple[str, ...] = (
    "plan",
    "read_diff",
    "read_candidate",
    "resolve",
    "apply_item",
    "apply_candidate",
    "finalize",
)

SOURCE_RAKUTEN = "rakuten"
DEFAULT_SOURCE = SOURCE_RAKUTEN
DEFAULT_MAX_ITEMS = 1000


def diff_to_proposal(row: DiffSuggestion) -> StatusProposal | None:
    """§9.2: Diff 経路の制限提案。

    MVP 本番想定は `unavailable` → `unavailable`。
    UT で制限度比較を検証するため、`proposed_active_status` が明示されていればそれを用いる。
    """

    if row.proposed_active_status is not None:
        proposed = row.proposed_active_status
    elif row.diff_status == "unavailable":
        proposed = "unavailable"
    else:
        return None
    return StatusProposal(
        source_kind="diff",
        active_status=proposed,
        event_at=row.judged_at,
        diff_id=row.product_diff_result_id,
        allows_reactivation=False,
    )


class ItemActiveStatusJob:
    """Orchestrates BATCH-008 active status apply phases."""

    def __init__(
        self,
        *,
        repositories: ItemActiveStatusRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
        fail_item_codes: Sequence[str] | None = None,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()
        self._fail_item_codes = set(fail_item_codes or ())


    @property
    def repositories(self):
        """Expose repositories for CLI bind_run / observability wiring."""

        return self._repos

    def run(
        self,
        *,
        job_run_id: str,
        source: str = SOURCE_RAKUTEN,
        batch_run_id: str | None = None,
        external_item_codes: Sequence[str] | None = None,
        max_items: int | None = None,
        trace_id: str | None = None,
    ) -> ItemActiveStatusResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = ItemActiveStatusResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        try:
            plan = ApplyPlan(
                source=source,
                batch_run_id=batch_run_id,
                external_item_codes=tuple(external_item_codes or ()),
                max_items=max_items,
            )
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")

            diffs = self._repos.list_diff_suggestions(
                source=plan.source,
                batch_run_id=plan.batch_run_id,
                external_item_codes=plan.external_item_codes or None,
            )
            result.diff_input_count = len(diffs)
            result.completed_phases.append("read_diff")
            self._repos.record_phase(phase="read_diff", status="succeeded")

            candidates = self._repos.list_detected_candidates(
                source=plan.source,
                batch_run_id=plan.batch_run_id,
                external_item_codes=plan.external_item_codes or None,
            )
            result.candidate_input_count = len(candidates)
            result.completed_phases.append("read_candidate")
            self._repos.record_phase(phase="read_candidate", status="succeeded")

            if plan.max_items is not None:
                # Item キー単位で上限
                keys: list[tuple[str, str]] = []
                seen: set[tuple[str, str]] = set()
                for row in candidates:
                    key = (row.source, row.external_item_code)
                    if key not in seen:
                        seen.add(key)
                        keys.append(key)
                for row in diffs:
                    key = (row.source, row.external_item_code)
                    if key not in seen:
                        seen.add(key)
                        keys.append(key)
                allowed = set(keys[: plan.max_items])
                candidates = [c for c in candidates if (c.source, c.external_item_code) in allowed]
                diffs = [d for d in diffs if (d.source, d.external_item_code) in allowed]

            by_item_candidates: dict[tuple[str, str], list[CandidateRow]] = defaultdict(list)
            for row in candidates:
                by_item_candidates[(row.source, row.external_item_code)].append(row)

            by_item_diffs: dict[tuple[str, str], list[DiffSuggestion]] = defaultdict(list)
            for row in diffs:
                by_item_diffs[(row.source, row.external_item_code)].append(row)

            item_keys = sorted(set(by_item_candidates) | set(by_item_diffs))
            bound_logger.info(
                "item_active_status.plan",
                item_count=len(item_keys),
                candidate_count=len(candidates),
                diff_count=len(diffs),
            )

            decisions = []
            for key in item_keys:
                src, code = key
                item = self._repos.get_item(source=src, external_item_code=code)
                if item is None:
                    # Item 未解決は候補を discarded
                    for cand in by_item_candidates.get(key, []):
                        self._repos.mark_candidate_discarded(cand.candidate_id)
                        result.candidate_discarded_count += 1
                    result.failed_item_codes.append(code)
                    result.error_codes.append("GRS-DB-001")
                    self._repos.record_error(
                        code="GRS-DB-001",
                        summary="item not found for active_status apply",
                        item_code=code,
                    )
                    continue

                proposals: list[StatusProposal] = []
                for d in by_item_diffs.get(key, []):
                    p = diff_to_proposal(d)
                    if p is not None:
                        proposals.append(p)
                for c in by_item_candidates.get(key, []):
                    proposals.append(proposal_from_candidate(c))

                cand_ids = [c.candidate_id for c in by_item_candidates.get(key, [])]
                decision = resolve_for_item(
                    source=src,
                    external_item_code=code,
                    current_status=item.active_status,
                    proposals=proposals,
                    candidate_ids_for_item=cand_ids,
                )
                decisions.append(decision)

            result.completed_phases.append("resolve")
            self._repos.record_phase(phase="resolve", status="succeeded")

            # apply_item + apply_candidate（仕様上は同一 Run 推奨）
            for decision in decisions:
                code = decision.external_item_code
                try:
                    if decision.adopt and decision.adopted_status is not None and not decision.skip_item_update:
                        ok = self._repos.update_item_active_status(
                            source=decision.source,
                            external_item_code=code,
                            active_status=decision.adopted_status,
                            fail=code in self._fail_item_codes,
                        )
                        if not ok:
                            result.failed_item_codes.append(code)
                            result.error_codes.append("GRS-DB-002")
                            self._repos.record_error(
                                code="GRS-DB-002",
                                summary="item active_status update failed",
                                item_code=code,
                            )
                            # 失敗時は候補を detected のまま残す（再実行）
                            continue
                        result.item_status_updated_count += 1
                        if decision.reactivation:
                            result.reactivation_count += 1

                    elif decision.adopt and decision.skip_item_update:
                        # 同一値でも処理済みとして候補遷移へ進む
                        pass
                    elif not decision.adopt:
                        for cid in decision.discarded_candidate_ids:
                            self._repos.mark_candidate_discarded(cid)
                            result.candidate_discarded_count += 1
                        result.succeeded_item_codes.append(code)
                        continue

                    # 候補 status 更新
                    if decision.winning_candidate_id:
                        self._repos.mark_candidate_applied(decision.winning_candidate_id)
                        result.candidate_applied_count += 1
                    for cid in decision.superseded_candidate_ids:
                        self._repos.mark_candidate_superseded(cid)
                        result.candidate_superseded_count += 1
                    for cid in decision.discarded_candidate_ids:
                        self._repos.mark_candidate_discarded(cid)
                        result.candidate_discarded_count += 1

                    # Diff 勝ちで候補が superseded のみの場合も Item 更新済みなら成功
                    if code not in result.failed_item_codes:
                        result.succeeded_item_codes.append(code)
                except Exception as exc:  # noqa: BLE001 — 単件失敗継続
                    result.failed_item_codes.append(code)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        item_code=code,
                    )

            result.completed_phases.append("apply_item")
            result.completed_phases.append("apply_candidate")
            self._repos.record_phase(phase="apply_item", status="succeeded")
            self._repos.record_phase(phase="apply_candidate", status="succeeded")

            return self._phase_finalize(result)
        except Exception as exc:  # noqa: BLE001
            result.error_codes.append("GRS-BAT-001")
            self._repos.record_error(code="GRS-BAT-001", summary=str(exc))
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            self._repos.record_phase(phase="finalize", status="failed")
            return result

    def _phase_finalize(self, result: ItemActiveStatusResult) -> ItemActiveStatusResult:
        if result.failed_item_codes and result.succeeded_item_codes:
            result.status = "partially_succeeded"
        elif result.failed_item_codes and not result.succeeded_item_codes:
            result.status = "failed"
        else:
            result.status = "succeeded"

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=result.status,
        )
        self._repos.record_phase(phase="finalize", status=result.status)
        result.completed_phases.append("finalize")
        return result


# typing re-export convenience for tests
__all__ = [
    "BATCH_ID",
    "ITEM_ACTIVE_STATUS_PHASES",
    "ItemActiveStatusJob",
    "diff_to_proposal",
]
