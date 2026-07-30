"""BATCH-013 Feature正規化ジョブ実装.

Phases（仕様書 §8.2）:
plan → claim_or_continue → resolve_config → load_features →
evaluate_skip → normalize_feature → project_meaning → persist → update_queue → finalize
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from batch.application.current_versions import (
    CurrentVersionResolveError,
    CurrentVersionResolver,
)
from batch.application.feature_normalization.adapter import (
    DEFAULT_CENTER_FEATURE,
    DEFAULT_K_FEATURE,
    DEFAULT_NORMALIZATION_VERSION,
    MVP_FEATURE_CODES,
    FeatureNormalizerPort,
    is_valid_feature_input_hash,
    project_item_meaning,
)
from batch.application.feature_normalization.models import (
    ConfigResolveHint,
    DigestionPlan,
    FeatureNormalizationJobResult,
    ItemFeatureNormalizedUpdateRow,
    ItemMeaningUpsertRow,
    NormalizationParams,
    NormalizeContext,
    QueueRow,
    RawFeatureAxis,
)
from batch.application.feature_normalization.repositories import (
    FeatureNormalizationRepositories,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-013"
FEATURE_NORMALIZATION_PHASES: tuple[str, ...] = (
    "plan",
    "claim_or_continue",
    "resolve_config",
    "load_features",
    "evaluate_skip",
    "normalize_feature",
    "project_meaning",
    "persist",
    "update_queue",
    "finalize",
)

DEFAULT_MAX_ITEMS = 1000
DEFAULT_SOURCE = "rakuten"
DEFAULT_QUEUE_BATCH_SIZE = 100


class FeatureNormalizationError(Exception):
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


def resolve_normalization_params(
    *, feature_normalization_version_id: str
) -> NormalizationParams:
    """feature_normalization_version.parameter_json 相当（MVP 固定 sigmoid）。"""

    _ = feature_normalization_version_id
    return NormalizationParams(
        normalization_method="sigmoid",
        center_feature=DEFAULT_CENTER_FEATURE,
        k_feature=DEFAULT_K_FEATURE,
    )


class FeatureNormalizationJob:
    def __init__(
        self,
        *,
        repositories: FeatureNormalizationRepositories,
        normalizer: FeatureNormalizerPort,
        version_resolver: CurrentVersionResolver | None = None,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._repos = repositories
        self._normalizer = normalizer
        self._version_resolver = version_resolver or (
            CurrentVersionResolver(repositories.db_reader)
            if repositories.db_reader is not None
            else None
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
    ) -> FeatureNormalizationJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        result = FeatureNormalizationJobResult(
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
                    self._process_one(
                        seed=seed,
                        run_at=run_at,
                        result=result,
                        trace_id=trace_id or job_run_id,
                    )
                except FeatureNormalizationError as exc:
                    self._fail_queue(seed, result, exc.code, exc.message, run_at)
                except Exception as exc:  # noqa: BLE001
                    self._fail_queue(seed, result, "GRS-BAT-008", str(exc), datetime.now(UTC))

            result.item_feature_normalized_update_count = (
                self._repos.item_feature_normalized_update_count
            )
            result.item_meaning_upsert_count = self._repos.item_meaning_upsert_count
            result.item_feature_raw_write_count = self._repos.item_feature_raw_write_count
            result.item_semantic_write_count = self._repos.item_semantic_write_count
            result.queue_insert_count = self._repos.queue_insert_count
            result.normalization_distribution_metric_write_count = (
                self._repos.normalization_distribution_metric_write_count
            )
            return self._phase_finalize(result)
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _fail_queue(
        self,
        seed: QueueRow,
        result: FeatureNormalizationJobResult,
        code: str,
        message: str,
        at: datetime,
    ) -> None:
        result.failed_queue_ids.append(seed.item_generation_queue_id)
        result.error_codes.append(code)
        result.failed_count += 1
        self._repos.record_error(
            code=code,
            summary=message,
            item_generation_queue_id=seed.item_generation_queue_id,
            item_id=seed.item_id,
        )
        try:
            self._repos.update_queue_status(
                item_generation_queue_id=seed.item_generation_queue_id,
                queue_status="failed",
                completed_at=at,
                error_message=message,
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
        result: FeatureNormalizationJobResult,
        trace_id: str,
    ) -> None:
        qid = seed.item_generation_queue_id

        claimed = self._repos.claim_or_continue(item_generation_queue_id=qid, started_at=run_at)
        self._mark_phase(result, "claim_or_continue")
        if claimed is None:
            result.claim_conflict_skip_count += 1
            result.skipped_queue_ids.append(qid)
            return

        try:
            semantic_config_version_id = (
                self._version_resolver.resolve_semantic()
                if self._version_resolver is not None
                else self._repos.resolve_semantic_config_version(item_id=seed.item_id)
            )
        except CurrentVersionResolveError as exc:
            raise FeatureNormalizationError(exc.code, exc.message) from exc
        if not semantic_config_version_id:
            raise FeatureNormalizationError(
                "GRS-CFG-001", "semantic_config_version_id not resolved"
            )
        _ = self._repos.load_item(item_id=seed.item_id)
        self._mark_phase(result, "resolve_config")

        raw_axes = self._repos.load_raw_features(
            item_id=seed.item_id,
            semantic_config_version_id=semantic_config_version_id,
        )
        feature_input_hash, raw_version = self._validate_raw_axes(raw_axes)
        self._mark_phase(result, "load_features")

        try:
            current_normalization_version_id = (
                self._version_resolver.resolve_normalization(
                    semantic_config_version_id=semantic_config_version_id
                )
                if self._version_resolver is not None
                else raw_version
            )
        except CurrentVersionResolveError as exc:
            raise FeatureNormalizationError(exc.code, exc.message) from exc
        if raw_version != current_normalization_version_id:
            raise FeatureNormalizationError(
                "GRS-CFG-001",
                "raw features do not use the current bound normalization version",
            )
        config = resolve_config_version(
            item_id=seed.item_id,
            semantic_config_version_id=semantic_config_version_id,
            normalization_version_id=current_normalization_version_id,
        )

        skip = self._repos.should_skip_normalization(
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

        params = resolve_normalization_params(
            feature_normalization_version_id=config.feature_normalization_version_id
        )
        context = NormalizeContext(
            item_id=seed.item_id,
            semantic_config_version_id=config.semantic_config_version_id,
            feature_input_hash=feature_input_hash,
            feature_normalization_version_id=config.feature_normalization_version_id,
            params=params,
            raw_axes=raw_axes,
            trace_id=trace_id,
        )
        norm = self._normalizer.normalize_features(context)
        self._mark_phase(result, "normalize_feature")

        if norm.status == "failed":
            raise FeatureNormalizationError(
                norm.error_code or "GRS-BAT-008",
                norm.error_message or "feature normalization failed",
            )

        if norm.status == "skipped":
            self._repos.update_queue_status(
                item_generation_queue_id=qid,
                queue_status="skipped",
                completed_at=run_at,
            )
            self._mark_phase(result, "update_queue")
            result.skipped_count += 1
            result.skipped_queue_ids.append(qid)
            return

        normalized_by_code = {
            axis.feature_code: axis.normalized_feature_value for axis in norm.normalized
        }
        meaning = project_item_meaning(normalized_by_code)
        self._mark_phase(result, "project_meaning")

        normalized_rows = tuple(
            ItemFeatureNormalizedUpdateRow(
                item_id=seed.item_id,
                semantic_config_version_id=config.semantic_config_version_id,
                feature_code=axis.feature_code,
                feature_input_hash=feature_input_hash,
                feature_normalization_version_id=config.feature_normalization_version_id,
                normalized_feature_value=axis.normalized_feature_value,
            )
            for axis in norm.normalized
        )
        item_meaning_row = (
            ItemMeaningUpsertRow(
                item_id=seed.item_id,
                semantic_config_version_id=config.semantic_config_version_id,
                feature_normalization_version_id=config.feature_normalization_version_id,
                item_social=meaning.item_social,
                item_symbolic=meaning.item_symbolic,
                generated_at=run_at,
            )
            if meaning is not None
            else None
        )
        self._repos.persist_normalized_and_meaning(
            normalized_rows=normalized_rows,
            item_meaning_row=item_meaning_row,
        )
        result.saturate_count += norm.saturate_count
        self._mark_phase(result, "persist")

        self._repos.update_queue_status(
            item_generation_queue_id=qid,
            queue_status="processing",
            keep_processing=True,
        )
        self._mark_phase(result, "update_queue")

        result.normalized_count += 1
        result.succeeded_queue_ids.append(qid)

    @staticmethod
    def _validate_raw_axes(
        raw_axes: tuple[RawFeatureAxis, ...],
    ) -> tuple[str, str]:
        """raw 8 軸の存在・hash/version 一貫性を検証し、(feature_input_hash, version) を返す。"""

        by_code = {axis.feature_code: axis for axis in raw_axes}
        for code in MVP_FEATURE_CODES:
            if code not in by_code:
                raise FeatureNormalizationError(
                    "GRS-VAL-001", f"raw feature missing for axis: {code}"
                )
        hashes = {axis.feature_input_hash for axis in raw_axes}
        versions = {axis.feature_normalization_version_id for axis in raw_axes}
        if len(hashes) != 1:
            raise FeatureNormalizationError(
                "GRS-VAL-002", "raw features have inconsistent feature_input_hash"
            )
        if len(versions) != 1:
            raise FeatureNormalizationError(
                "GRS-VAL-002", "raw features have inconsistent feature_normalization_version_id"
            )
        feature_input_hash = next(iter(hashes))
        version = next(iter(versions))
        if not is_valid_feature_input_hash(feature_input_hash):
            raise FeatureNormalizationError(
                "GRS-VAL-002", "feature_input_hash must be 64 hex"
            )
        if not version.strip():
            raise FeatureNormalizationError(
                "GRS-CFG-001", "feature_normalization_version_id missing on raw features"
            )
        return feature_input_hash, version

    def _mark_phase(self, result: FeatureNormalizationJobResult, phase: str) -> None:
        if phase not in result.completed_phases:
            result.completed_phases.append(phase)
            self._repos.record_phase(phase=phase, status="succeeded")

    def _phase_finalize(
        self, result: FeatureNormalizationJobResult
    ) -> FeatureNormalizationJobResult:
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
