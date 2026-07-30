"""BATCH-010 Item Semantic 生成ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → claim_queue → resolve_config → load_item_context → generate_semantic →
upsert_item_semantic → update_queue → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.current_versions import (
    CurrentVersionResolveError,
    CurrentVersionResolver,
)
from batch.application.item_semantic.adapter import (
    ItemSemanticGeneratorPort,
    ScaffoldItemSemanticAdapter,
    build_scaffold_adapter,
)
from batch.application.item_semantic.models import (
    ConfigResolveHint,
    DigestionPlan,
    ItemSemanticJobResult,
    QueueRow,
    SemanticGenerationContext,
)
from batch.application.item_semantic.repositories import ItemSemanticRepositories
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-010"
ITEM_SEMANTIC_PHASES: tuple[str, ...] = (
    "plan",
    "claim_queue",
    "resolve_config",
    "load_item_context",
    "generate_semantic",
    "upsert_item_semantic",
    "update_queue",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_QUEUE_BATCH_SIZE = 100


class ItemSemanticError(Exception):
    """Per-queue-row failure with batch error code."""

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
    """MVP scaffold stub — Config Version Resolver (§8.2 resolve_config)."""

    _ = item_id
    return ConfigResolveHint(semantic_config_version_id="scaffold-semantic-config-v1")


class ItemSemanticJob:
    """Orchestrates BATCH-010 Item Semantic generation phases."""

    def __init__(
        self,
        *,
        repositories: ItemSemanticRepositories,
        generator: ItemSemanticGeneratorPort | None = None,
        version_resolver: CurrentVersionResolver | None = None,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._version_resolver = version_resolver or (
            CurrentVersionResolver(repositories.db_reader)
            if repositories.db_reader is not None
            else None
        )
        self._generator = generator or build_scaffold_adapter(
            find_existing=lambda item_id, version_id: repositories.find_item_semantic(
                item_id=item_id,
                semantic_config_version_id=version_id,
            )
        )
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
    ) -> ItemSemanticJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        result = ItemSemanticJobResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            bound_logger.error("item_semantic.already_running", batch_id=BATCH_ID)
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
            result.non_semantic_skip_count = plan.non_semantic_skip_count
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")
            bound_logger.info(
                "item_semantic.plan",
                processable=len(plan.items),
                non_semantic_skip=plan.non_semantic_skip_count,
            )

            if not plan.items:
                if plan.non_semantic_skip_count > 0 or self._repos.queues:
                    result.status = "succeeded"
                    self._tracker.complete(
                        batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                    )
                    self._repos.record_phase(phase="finalize", status="succeeded")
                    result.completed_phases.append("finalize")
                    bound_logger.info("item_semantic.plan_empty_noop")
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
                        job_run_id=job_run_id,
                        trace_id=trace_id or job_run_id,
                        result=result,
                    )
                except ItemSemanticError as exc:
                    result.failed_queue_ids.append(seed.item_generation_queue_id)
                    result.error_codes.append(exc.code)
                    result.semantic_failed_count += 1
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
                    bound_logger.error(
                        "item_semantic.row_failed",
                        item_generation_queue_id=seed.item_generation_queue_id,
                        error_code=exc.code,
                    )
                except KeyError as exc:
                    result.failed_queue_ids.append(seed.item_generation_queue_id)
                    result.error_codes.append("GRS-DB-001")
                    result.semantic_failed_count += 1
                    self._repos.record_error(
                        code="GRS-DB-001",
                        summary=str(exc),
                        item_generation_queue_id=seed.item_generation_queue_id,
                        item_id=seed.item_id,
                    )
                    try:
                        self._repos.update_queue_status(
                            item_generation_queue_id=seed.item_generation_queue_id,
                            queue_status="failed",
                            completed_at=run_at,
                            error_message=str(exc),
                        )
                    except KeyError:
                        pass
                except Exception as exc:  # noqa: BLE001 — per-row failure continues
                    result.failed_queue_ids.append(seed.item_generation_queue_id)
                    result.error_codes.append("GRS-BAT-008")
                    result.semantic_failed_count += 1
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

            result.written_item_semantic_rows = list(self._repos.written_item_semantic_rows)
            result.item_write_count = self._repos.item_write_count
            result.queue_insert_count = self._repos.queue_insert_count

            result = self._phase_finalize(result)
            bound_logger.info(
                "item_semantic.finalize",
                status=result.status,
                claimed=result.claimed_count,
                generated=result.semantic_generated_count,
                skipped=result.semantic_skipped_count,
                failed=result.semantic_failed_count,
            )
            return result
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
        ids = (
            tuple(str(c).strip() for c in item_ids if str(c).strip()) if item_ids else None
        )
        qids = (
            tuple(str(c).strip() for c in queue_ids if str(c).strip()) if queue_ids else None
        )
        items, non_semantic_skip = self._repos.list_claimable_queues(
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
            non_semantic_skip_count=non_semantic_skip,
        )

    def _process_one(
        self,
        *,
        seed: QueueRow,
        run_at: datetime,
        job_run_id: str,
        trace_id: str,
        result: ItemSemanticJobResult,
    ) -> None:
        qid = seed.item_generation_queue_id

        # claim_queue
        claimed = self._repos.claim_queue(
            item_generation_queue_id=qid,
            started_at=run_at,
        )
        if "claim_queue" not in result.completed_phases:
            result.completed_phases.append("claim_queue")
            self._repos.record_phase(phase="claim_queue", status="succeeded")

        if claimed is None:
            result.claim_conflict_skip_count += 1
            result.skipped_queue_ids.append(qid)
            return

        result.claimed_count += 1

        # resolve_config
        try:
            config = (
                ConfigResolveHint(
                    semantic_config_version_id=self._version_resolver.resolve_semantic()
                )
                if self._version_resolver is not None
                else resolve_config_version(item_id=seed.item_id)
            )
        except CurrentVersionResolveError as exc:
            raise ItemSemanticError(exc.code, exc.message) from exc
        if "resolve_config" not in result.completed_phases:
            result.completed_phases.append("resolve_config")
            self._repos.record_phase(phase="resolve_config", status="succeeded")

        # load_item_context
        item = self._repos.load_item(item_id=seed.item_id)
        if "load_item_context" not in result.completed_phases:
            result.completed_phases.append("load_item_context")
            self._repos.record_phase(phase="load_item_context", status="succeeded")

        context = SemanticGenerationContext(
            trace_id=trace_id,
            batch_run_id=job_run_id,
            item_generation_queue_id=qid,
            item_id=item.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
            item_name=item.item_name,
            item_caption=item.item_caption,
            item_description=item.item_description,
            genre_name=item.genre_name,
            attributes=item.attributes,
            tags=item.tags,
            review_texts=item.review_texts,
            brand_name=item.brand_name,
            skip_if_unchanged=True,
        )

        # generate_semantic (IF-SHARED-001)
        gen = self._generator.generate_item_semantic(context)
        if "generate_semantic" not in result.completed_phases:
            result.completed_phases.append("generate_semantic")
            self._repos.record_phase(phase="generate_semantic", status="succeeded")
            self._repos.record_phase(phase="item_semantic_generated", status=gen.status)

        if gen.status == "failed":
            raise ItemSemanticError(
                gen.error_code or "GRS-BAT-008",
                gen.error_message or "semantic generation failed",
            )

        if gen.status == "skipped":
            self._repos.update_queue_status(
                item_generation_queue_id=qid,
                queue_status="skipped",
                completed_at=run_at,
            )
            if "update_queue" not in result.completed_phases:
                result.completed_phases.append("update_queue")
                self._repos.record_phase(phase="update_queue", status="succeeded")
            # skip 時は Upsert しない（§9.2）
            result.semantic_skipped_count += 1
            result.skipped_queue_ids.append(qid)
            return

        # upsert_item_semantic (IF-DB-BATCH-011) — generated のみ
        assert gen.semantic_json is not None
        persisted = self._repos.upsert_item_semantic(
            item_id=item.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
            semantic_json=gen.semantic_json,
            semantic_input_hash=gen.semantic_input_hash,
            generated_at=run_at,
        )
        if "upsert_item_semantic" not in result.completed_phases:
            result.completed_phases.append("upsert_item_semantic")
            self._repos.record_phase(phase="upsert_item_semantic", status="succeeded")

        # update_queue: semantic 成功時は processing 維持（§10.2 / §12.1）
        self._repos.update_queue_status(
            item_generation_queue_id=qid,
            queue_status="processing",
            keep_processing=True,
        )
        if "update_queue" not in result.completed_phases:
            result.completed_phases.append("update_queue")
            self._repos.record_phase(phase="update_queue", status="succeeded")

        result.semantic_generated_count += 1
        result.succeeded_queue_ids.append(qid)
        _ = persisted

    def _phase_finalize(self, result: ItemSemanticJobResult) -> ItemSemanticJobResult:
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
            or result.non_semantic_skip_count
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
    repositories: ItemSemanticRepositories,
    *,
    job_run_tracker: JobRunTracker | None = None,
) -> ItemSemanticJob:
    adapter: ScaffoldItemSemanticAdapter = build_scaffold_adapter(
        find_existing=lambda item_id, version_id: repositories.find_item_semantic(
            item_id=item_id,
            semantic_config_version_id=version_id,
        )
    )
    return ItemSemanticJob(
        repositories=repositories,
        generator=adapter,
        job_run_tracker=job_run_tracker,
    )
