"""BATCH-015 Item Embedding生成ジョブ実装.

Phases（仕様書 §8.2）:
plan → claim_or_continue → resolve_config → validate_handoff →
evaluate_skip → generate_embedding → upsert_embedding → update_queue → finalize

IF 境界:
- IF-EXT-005: Embedding 生成（scaffold-first）
- IF-VEC-BATCH-001: item_embedding Upsert
- IF-DB-BATCH-015: handoff 消費のみ（再算出禁止）
- IF-DB-BATCH-016: 触らない

Queue 終端 succeeded は本 Batch（semantic 一連 / embedding 経路）。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.item_embedding.adapter import (
    ItemEmbeddingGeneratorPort,
    build_scaffold_adapter,
    is_valid_embedding_input_hash,
    serialize_embedding_input,
)
from batch.application.item_embedding.models import (
    ConfigResolveHint,
    DigestionPlan,
    EmbeddingGenerationContext,
    ItemEmbeddingJobResult,
    ItemEmbeddingUpsertRow,
    QueueRow,
)
from batch.application.item_embedding.repositories import (
    DEFAULT_EMBEDDING_MODEL_VERSION,
    ItemEmbeddingRepositories,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-015"
ITEM_EMBEDDING_PHASES: tuple[str, ...] = (
    "plan",
    "claim_or_continue",
    "resolve_config",
    "validate_handoff",
    "evaluate_skip",
    "generate_embedding",
    "upsert_embedding",
    "update_queue",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_QUEUE_BATCH_SIZE = 100


class ItemEmbeddingError(Exception):
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
    """MOD-RECO-003 相当: model_type=embedding / is_current（scaffold 固定）."""

    _ = item_id
    return ConfigResolveHint(model_version_id=DEFAULT_EMBEDDING_MODEL_VERSION)


class ItemEmbeddingJob:
    def __init__(
        self,
        *,
        repositories: ItemEmbeddingRepositories,
        generator: ItemEmbeddingGeneratorPort | None = None,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._generator = generator or build_scaffold_adapter()
        self._tracker = job_run_tracker or ScaffoldJobRunTracker()
        self._logger = logger or ScaffoldBatchLogger()


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
    ) -> ItemEmbeddingJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        result = ItemEmbeddingJobResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            bound_logger.error("item_embedding.already_running", batch_id=BATCH_ID)
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
            bound_logger.info(
                "item_embedding.plan",
                processable=len(plan.items),
                non_target_skip=plan.non_target_skip_count,
            )

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
                    self._process_one(
                        seed=seed,
                        run_at=run_at,
                        result=result,
                        trace_id=trace_id or job_run_id,
                    )
                except ItemEmbeddingError as exc:
                    self._fail_one(seed=seed, code=exc.code, summary=exc.message, result=result)
                except KeyError as exc:
                    self._fail_one(
                        seed=seed, code="GRS-DB-001", summary=str(exc), result=result
                    )
                except Exception as exc:  # noqa: BLE001
                    self._fail_one(
                        seed=seed, code="GRS-BAT-008", summary=str(exc), result=result
                    )

            result.item_embedding_write_count = self._repos.item_embedding_write_count
            result.item_write_count = self._repos.item_write_count
            result.queue_insert_count = self._repos.queue_insert_count
            result.hash_recompute_count = self._repos.hash_recompute_count
            result.distribution_metric_write_count = self._repos.distribution_metric_write_count
            result.api_call_count = len(self._repos.api_call_logs)
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
        result: ItemEmbeddingJobResult,
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
        result: ItemEmbeddingJobResult,
        trace_id: str,
    ) -> None:
        qid = seed.item_generation_queue_id

        claimed = self._repos.claim_or_continue(
            item_generation_queue_id=qid,
            started_at=run_at,
        )
        self._mark_phase(result, "claim_or_continue")
        if claimed is None:
            result.claim_conflict_skip_count += 1
            result.skipped_queue_ids.append(qid)
            return

        result.claimed_count += 1

        config = resolve_config_version(item_id=seed.item_id)
        self._mark_phase(result, "resolve_config")

        _ = self._repos.load_item(item_id=seed.item_id)

        handoff = self._repos.load_hash_handoff(item_id=seed.item_id)
        if handoff is None:
            raise ItemEmbeddingError("GRS-BAT-008", "embedding hash handoff missing")
        if not is_valid_embedding_input_hash(handoff.embedding_input_hash):
            raise ItemEmbeddingError("GRS-BAT-008", "embedding_input_hash invalid format")
        if handoff.model_version_id != config.model_version_id:
            raise ItemEmbeddingError("GRS-BAT-008", "handoff model_version_id mismatch")
        if handoff.embedding_source_type != config.embedding_source_type:
            raise ItemEmbeddingError("GRS-BAT-008", "handoff embedding_source_type mismatch")
        if not isinstance(handoff.item_text_context, dict) or not handoff.item_text_context:
            raise ItemEmbeddingError("GRS-BAT-008", "item_text_context handoff missing/invalid")
        # IF-DB-BATCH-015 消費: 再算出禁止（hash_recompute_count は常に 0 のまま）
        embedding_input_hash = handoff.embedding_input_hash
        self._mark_phase(result, "validate_handoff")

        skip = self._repos.should_skip_embedding_generation(
            item_id=seed.item_id,
            model_version_id=config.model_version_id,
            embedding_input_hash=embedding_input_hash,
        )
        self._mark_phase(result, "evaluate_skip")

        if skip:
            self._repos.update_queue_status(
                item_generation_queue_id=qid,
                queue_status="skipped",
                completed_at=run_at,
            )
            self._mark_phase(result, "update_queue")
            result.skipped_count += 1
            result.skipped_queue_ids.append(qid)
            return

        input_text = serialize_embedding_input(handoff.item_text_context)
        context = EmbeddingGenerationContext(
            item_id=seed.item_id,
            item_generation_queue_id=qid,
            model_version_id=config.model_version_id,
            model_name=config.model_name,
            embedding_input_hash=embedding_input_hash,
            item_text_context=dict(handoff.item_text_context),
            embedding_input_text=input_text,
            embedding_source_type=config.embedding_source_type,
            trace_id=trace_id,
            dimension=config.embedding_dimension,
        )
        gen = self._generator.generate_item_embedding(context)
        self._mark_phase(result, "generate_embedding")
        self._repos.record_phase(phase="item_embedding_generated", status=gen.status)
        self._repos.record_api_call(
            status=gen.status,
            model=gen.model_name or config.model_name,
            latency_ms=gen.latency_ms,
        )

        if gen.status == "failed":
            raise ItemEmbeddingError(
                gen.error_code or "GRS-BAT-008",
                gen.error_message or "embedding generation failed",
            )

        if gen.status == "skipped":
            self._repos.update_queue_status(
                item_generation_queue_id=qid,
                queue_status="skipped",
                completed_at=run_at,
            )
            self._mark_phase(result, "update_queue")
            result.skipped_count += 1
            result.skipped_queue_ids.append(qid)
            return

        assert gen.embedding_vector is not None
        self._repos.upsert_item_embedding(
            ItemEmbeddingUpsertRow(
                item_id=seed.item_id,
                model_version_id=config.model_version_id,
                embedding_source_type=config.embedding_source_type,
                embedding_input_hash=embedding_input_hash,
                embedding_vector=gen.embedding_vector,
                generated_at=run_at,
            )
        )
        self._mark_phase(result, "upsert_embedding")

        # Queue 終端 succeeded（semantic 一連 / embedding 経路）
        self._repos.update_queue_status(
            item_generation_queue_id=qid,
            queue_status="succeeded",
            completed_at=run_at,
        )
        self._mark_phase(result, "update_queue")

        result.generated_count += 1
        result.succeeded_queue_ids.append(qid)

    def _mark_phase(self, result: ItemEmbeddingJobResult, phase: str) -> None:
        if phase not in result.completed_phases:
            result.completed_phases.append(phase)
            self._repos.record_phase(phase=phase, status="succeeded")

    def _phase_finalize(self, result: ItemEmbeddingJobResult) -> ItemEmbeddingJobResult:
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


def build_default_scaffold_job(
    repositories: ItemEmbeddingRepositories,
    *,
    job_run_tracker: JobRunTracker | None = None,
) -> ItemEmbeddingJob:
    return ItemEmbeddingJob(
        repositories=repositories,
        generator=build_scaffold_adapter(),
        job_run_tracker=job_run_tracker,
    )
