"""BATCH-012 Item Feature生成ジョブ実装.

Phases（仕様書 §8.2）:
plan → claim_or_continue → resolve_config → load_context → validate_handoff →
evaluate_skip → generate_feature → update_queue → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.item_feature.adapter import (
    DEFAULT_NORMALIZATION_VERSION,
    ItemFeatureGeneratorPort,
    is_valid_feature_input_hash,
)
from batch.application.item_feature.models import (
    ConfigResolveHint,
    DigestionPlan,
    FeatureGenerationContext,
    ItemFeatureJobResult,
    ItemFeatureUpsertRow,
    QueueRow,
)
from batch.application.item_feature.repositories import ItemFeatureRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-012"
ITEM_FEATURE_PHASES: tuple[str, ...] = (
    "plan",
    "claim_or_continue",
    "resolve_config",
    "load_context",
    "validate_handoff",
    "evaluate_skip",
    "generate_feature",
    "update_queue",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_QUEUE_BATCH_SIZE = 100


class ItemFeatureError(Exception):
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


def resolve_config_version(
    *,
    item_id: str,
    semantic_config_version_id: str,
    normalization_version_id: str = DEFAULT_NORMALIZATION_VERSION,
) -> ConfigResolveHint:
    _ = item_id
    return ConfigResolveHint(
        semantic_config_version_id=semantic_config_version_id,
        feature_normalization_version_id=normalization_version_id,
    )


class ItemFeatureJob:
    def __init__(
        self,
        *,
        repositories: ItemFeatureRepositories,
        generator: ItemFeatureGeneratorPort,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._generator = generator
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
    ) -> ItemFeatureJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        result = ItemFeatureJobResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

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
                    self._process_one(
                        seed=seed,
                        run_at=run_at,
                        result=result,
                        trace_id=trace_id or job_run_id,
                    )
                except ItemFeatureError as exc:
                    result.failed_queue_ids.append(seed.item_generation_queue_id)
                    result.error_codes.append(exc.code)
                    result.failed_count += 1
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        item_generation_queue_id=seed.item_generation_queue_id,
                        item_id=seed.item_id,
                    )
                    try:
                        self._repos.update_queue_status(
                            item_generation_queue_id=seed.item_generation_queue_id,
                            queue_status="failed",
                            completed_at=run_at,
                            error_message=exc.message,
                        )
                    except KeyError:
                        pass
                except Exception as exc:  # noqa: BLE001
                    result.failed_queue_ids.append(seed.item_generation_queue_id)
                    result.error_codes.append("GRS-BAT-008")
                    result.failed_count += 1
                    self._repos.record_error(
                        code="GRS-BAT-008",
                        summary=str(exc),
                        item_generation_queue_id=seed.item_generation_queue_id,
                        item_id=seed.item_id,
                    )
                    try:
                        self._repos.update_queue_status(
                            item_generation_queue_id=seed.item_generation_queue_id,
                            queue_status="failed",
                            completed_at=datetime.now(UTC),
                            error_message=str(exc),
                        )
                    except KeyError:
                        pass

            result.item_feature_write_count = self._repos.item_feature_write_count
            result.item_semantic_write_count = self._repos.item_semantic_write_count
            result.queue_insert_count = self._repos.queue_insert_count
            return self._phase_finalize(result)
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

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
        result: ItemFeatureJobResult,
        trace_id: str,
    ) -> None:
        qid = seed.item_generation_queue_id

        claimed = self._repos.claim_or_continue(item_generation_queue_id=qid, started_at=run_at)
        self._mark_phase(result, "claim_or_continue")
        if claimed is None:
            result.claim_conflict_skip_count += 1
            result.skipped_queue_ids.append(qid)
            return

        semantic = self._repos.load_item_semantic(item_id=seed.item_id)
        config = resolve_config_version(
            item_id=seed.item_id,
            semantic_config_version_id=semantic.semantic_config_version_id,
            normalization_version_id=self._repos.current_normalization_version_id,
        )
        self._mark_phase(result, "resolve_config")

        _ = self._repos.load_item(item_id=seed.item_id)
        concepts = self._repos.extract_concepts(semantic.semantic_json)
        self._mark_phase(result, "load_context")

        handoff = self._repos.load_hash_handoff(
            item_id=seed.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
        )
        if handoff is None or not is_valid_feature_input_hash(handoff.feature_input_hash):
            raise ItemFeatureError("GRS-BAT-008", "feature_input_hash handoff missing/invalid")
        if handoff.semantic_config_version_id != config.semantic_config_version_id:
            raise ItemFeatureError("GRS-BAT-008", "feature_input_hash version mismatch")
        feature_input_hash = handoff.feature_input_hash
        self._mark_phase(result, "validate_handoff")

        skip = self._repos.should_skip_feature_generation(
            item_id=seed.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
            feature_input_hash=feature_input_hash,
            feature_normalization_version_id=config.feature_normalization_version_id,
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

        context = FeatureGenerationContext(
            item_id=seed.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
            feature_input_hash=feature_input_hash,
            feature_normalization_version_id=config.feature_normalization_version_id,
            concepts=concepts,
            trace_id=trace_id,
        )
        gen = self._generator.generate_item_feature(context)
        self._mark_phase(result, "generate_feature")

        if gen.status == "failed":
            raise ItemFeatureError(
                gen.error_code or "GRS-BAT-008",
                gen.error_message or "item feature generation failed",
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

        rows = tuple(
            ItemFeatureUpsertRow(
                item_id=seed.item_id,
                semantic_config_version_id=config.semantic_config_version_id,
                feature_code=axis.feature_code,
                feature_input_hash=feature_input_hash,
                feature_normalization_version_id=config.feature_normalization_version_id,
                raw_feature_value=axis.raw_feature_value,
                generated_at=run_at,
            )
            for axis in gen.features
        )
        self._repos.upsert_item_feature(rows)
        result.raw_clip_count += gen.raw_clip_count

        self._repos.update_queue_status(
            item_generation_queue_id=qid,
            queue_status="processing",
            keep_processing=True,
        )
        self._mark_phase(result, "update_queue")

        result.generated_count += 1
        result.succeeded_queue_ids.append(qid)

    def _mark_phase(self, result: ItemFeatureJobResult, phase: str) -> None:
        if phase not in result.completed_phases:
            result.completed_phases.append(phase)
            self._repos.record_phase(phase=phase, status="succeeded")

    def _phase_finalize(self, result: ItemFeatureJobResult) -> ItemFeatureJobResult:
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
