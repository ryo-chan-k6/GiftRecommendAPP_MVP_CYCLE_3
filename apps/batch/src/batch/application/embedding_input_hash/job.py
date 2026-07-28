"""BATCH-014 Embedding入力hash算出ジョブ実装.

Phases（仕様書 §8.2）:
plan → claim_or_continue → resolve_config → load_inputs → build_context →
compute_hash → evaluate_skip → record_hash_handoff → update_queue → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.embedding_input_hash.hashing import (
    build_item_text_context,
    compute_embedding_input_hash,
)
from batch.application.embedding_input_hash.models import (
    ConfigResolveHint,
    DigestionPlan,
    EmbeddingHashHandoffRecord,
    EmbeddingInputHashJobResult,
    QueueRow,
)
from batch.application.embedding_input_hash.repositories import (
    DEFAULT_EMBEDDING_MODEL_VERSION,
    DEFAULT_EMBEDDING_SOURCE_VERSION,
    EmbeddingInputHashRepositories,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-014"
EMBEDDING_INPUT_HASH_PHASES: tuple[str, ...] = (
    "plan",
    "claim_or_continue",
    "resolve_config",
    "load_inputs",
    "build_context",
    "compute_hash",
    "evaluate_skip",
    "record_hash_handoff",
    "update_queue",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_QUEUE_BATCH_SIZE = 100


class EmbeddingInputHashError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _is_batch_already_running(tracker: JobRunTracker) -> bool:
    records = getattr(tracker, "records", None)
    if not isinstance(records, list):
        return False
    starts = 0
    completes = 0
    for record in records:
        if getattr(record, "batch_id", None) != BATCH_ID:
            continue
        status = getattr(record, "status", None)
        if status == "running":
            starts += 1
        elif status in {"succeeded", "partially_succeeded", "failed"}:
            completes += 1
    return starts > completes


def resolve_config_version(*, item_id: str) -> ConfigResolveHint:
    """MOD-RECO-003 相当: model_type=embedding / is_current を解決（scaffold 固定）。"""

    _ = item_id
    return ConfigResolveHint(
        model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION,
        embedding_source_version=DEFAULT_EMBEDDING_SOURCE_VERSION,
    )


class EmbeddingInputHashJob:
    def __init__(
        self,
        *,
        repositories: EmbeddingInputHashRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
        force_hash_fail: bool = False,
    ) -> None:
        self._repos = repositories
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()
        self._force_hash_fail = force_hash_fail


    @property
    def repositories(self):
        """Expose repositories for CLI bind_run / observability wiring."""

        return self._repos

    def run(
        self,
        *,
        job_run_id: str,
        max_items: int | None = None,
        source: str | None = None,
        queue_batch_size: int | None = None,
        item_ids: Sequence[str] | None = None,
        queue_ids: Sequence[str] | None = None,
        trace_id: str | None = None,
    ) -> EmbeddingInputHashJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        result = EmbeddingInputHashJobResult(
            batch_id=BATCH_ID, job_run_id=job_run_id, status="failed"
        )

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        try:
            plan = self._phase_plan(
                max_items=max_items,
                source=source,
                queue_batch_size=queue_batch_size,
                item_ids=item_ids,
                queue_ids=queue_ids,
            )
            result.planned_queue_count = len(plan.items)
            result.non_target_skip_count = plan.non_target_skip_count
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")

            if not plan.items:
                if plan.non_target_skip_count > 0 or self._repos.queues:
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    return result
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty digestion plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            run_at = datetime.now(UTC)
            for seed in plan.items:
                try:
                    self._process_one(seed=seed, run_at=run_at, result=result)
                except EmbeddingInputHashError as exc:
                    self._fail_one(seed=seed, code=exc.code, summary=exc.message, result=result)
                except KeyError as exc:
                    self._fail_one(
                        seed=seed, code="GRS-DB-001", summary=str(exc), result=result
                    )
                except Exception as exc:  # noqa: BLE001
                    self._fail_one(
                        seed=seed, code="GRS-BAT-007", summary=str(exc), result=result
                    )

            result.handoff_records = list(self._repos.handoff_records)
            result.item_write_count = self._repos.item_write_count
            result.item_embedding_write_count = self._repos.item_embedding_write_count
            result.queue_insert_count = self._repos.queue_insert_count
            return self._phase_finalize(result)
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _fail_one(
        self,
        *,
        seed: QueueRow,
        code: str,
        summary: str,
        result: EmbeddingInputHashJobResult,
    ) -> None:
        result.failed_queue_ids.append(seed.item_generation_queue_id)
        result.error_codes.append(code)
        result.failed_count += 1
        self._repos.record_error(
            code=code,
            summary=summary,
            item_generation_queue_id=seed.item_generation_queue_id,
            item_id=seed.item_id,
        )
        try:
            self._repos.update_queue_status(
                item_generation_queue_id=seed.item_generation_queue_id,
                queue_status="failed",
                completed_at=datetime.now(UTC),
                error_message=summary,
            )
        except KeyError:
            pass

    def _phase_plan(
        self,
        *,
        max_items: int | None,
        source: str | None,
        queue_batch_size: int | None,
        item_ids: Sequence[str] | None,
        queue_ids: Sequence[str] | None,
    ) -> DigestionPlan:
        resolved_max = DEFAULT_MAX_ITEMS if max_items is None else max(0, int(max_items))
        resolved_source = (source or DEFAULT_SOURCE).strip() or DEFAULT_SOURCE
        resolved_batch = (
            DEFAULT_QUEUE_BATCH_SIZE
            if queue_batch_size is None
            else max(1, int(queue_batch_size))
        )
        ids = tuple(str(c).strip() for c in item_ids if str(c).strip()) if item_ids else None
        qids = tuple(str(c).strip() for c in queue_ids if str(c).strip()) if queue_ids else None
        items, non_target = self._repos.list_target_queues(
            max_items=resolved_max,
            source=resolved_source,
            queue_batch_size=resolved_batch,
            item_ids=ids,
            queue_ids=qids,
        )
        return DigestionPlan(
            items=tuple(items),
            source_filter=resolved_source,
            max_items=resolved_max,
            queue_batch_size=resolved_batch,
            non_target_skip_count=non_target,
        )

    def _process_one(
        self,
        *,
        seed: QueueRow,
        run_at: datetime,
        result: EmbeddingInputHashJobResult,
    ) -> None:
        qid = seed.item_generation_queue_id

        claimed = self._repos.claim_or_continue(
            item_generation_queue_id=qid,
            started_at=run_at,
        )
        if "claim_or_continue" not in result.completed_phases:
            result.completed_phases.append("claim_or_continue")
            self._repos.record_phase(phase="claim_or_continue", status="succeeded")

        if claimed is None:
            result.claim_conflict_skip_count += 1
            result.skipped_queue_ids.append(qid)
            return

        config = resolve_config_version(item_id=seed.item_id)
        if "resolve_config" not in result.completed_phases:
            result.completed_phases.append("resolve_config")
            self._repos.record_phase(phase="resolve_config", status="succeeded")

        item = self._repos.load_item(item_id=seed.item_id)
        if "load_inputs" not in result.completed_phases:
            result.completed_phases.append("load_inputs")
            self._repos.record_phase(phase="load_inputs", status="succeeded")

        if self._force_hash_fail:
            raise EmbeddingInputHashError("GRS-BAT-007", "scaffold forced hash failure")

        context = build_item_text_context(
            item=item,
            embedding_source_type=config.embedding_source_type,
            embedding_source_version=config.embedding_source_version,
        )
        if "build_context" not in result.completed_phases:
            result.completed_phases.append("build_context")
            self._repos.record_phase(phase="build_context", status="succeeded")

        digest = compute_embedding_input_hash(context)
        if len(digest) != 64:
            raise EmbeddingInputHashError("GRS-BAT-007", "invalid hash length")
        if "compute_hash" not in result.completed_phases:
            result.completed_phases.append("compute_hash")
            self._repos.record_phase(phase="compute_hash", status="succeeded")

        skip = self._repos.should_skip_embedding_generation(
            item_id=item.item_id,
            model_version_id=config.model_version_id,
            embedding_input_hash=digest,
        )
        if "evaluate_skip" not in result.completed_phases:
            result.completed_phases.append("evaluate_skip")
            self._repos.record_phase(phase="evaluate_skip", status="succeeded")

        if skip:
            self._repos.update_queue_status(
                item_generation_queue_id=qid,
                queue_status="skipped",
                completed_at=run_at,
            )
            if "update_queue" not in result.completed_phases:
                result.completed_phases.append("update_queue")
                self._repos.record_phase(phase="update_queue", status="succeeded")
            result.skipped_count += 1
            result.skipped_queue_ids.append(qid)
            return

        self._repos.record_hash_handoff(
            EmbeddingHashHandoffRecord(
                item_id=item.item_id,
                item_generation_queue_id=qid,
                model_version_id=config.model_version_id,
                embedding_source_type=config.embedding_source_type,
                embedding_source_version=config.embedding_source_version,
                embedding_input_hash=digest,
                item_text_context=context,
            )
        )
        if "record_hash_handoff" not in result.completed_phases:
            result.completed_phases.append("record_hash_handoff")
            self._repos.record_phase(phase="record_hash_handoff", status="succeeded")
            self._repos.record_phase(phase="embedding_input_hash_computed", status="succeeded")

        self._repos.update_queue_status(
            item_generation_queue_id=qid,
            queue_status="processing",
            keep_processing=True,
        )
        if "update_queue" not in result.completed_phases:
            result.completed_phases.append("update_queue")
            self._repos.record_phase(phase="update_queue", status="succeeded")

        result.hashed_count += 1
        result.succeeded_queue_ids.append(qid)

    def _phase_finalize(
        self, result: EmbeddingInputHashJobResult
    ) -> EmbeddingInputHashJobResult:
        if result.failed_queue_ids and result.succeeded_queue_ids:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_queue_ids and not result.succeeded_queue_ids:
            if result.skipped_queue_ids or result.claim_conflict_skip_count:
                result.status = "partially_succeeded"
                tracker_status = "partially_succeeded"
            else:
                result.status = "failed"
                if "GRS-BAT-001" not in result.error_codes:
                    result.error_codes.append("GRS-BAT-001")
                tracker_status = "failed"
        elif (
            result.succeeded_queue_ids
            or result.skipped_queue_ids
            or result.claim_conflict_skip_count
            or result.non_target_skip_count
        ):
            result.status = "succeeded"
            tracker_status = "succeeded"
        else:
            result.status = "failed"
            tracker_status = "failed"

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        self._repos.record_phase(phase="finalize", status=result.status)
        result.completed_phases.append("finalize")
        return result
