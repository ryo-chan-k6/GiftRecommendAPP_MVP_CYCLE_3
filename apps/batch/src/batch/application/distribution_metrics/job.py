"""BATCH-016 分布メトリクス集計ジョブ実装.

Phases（仕様書 §8.2）:
open_run → resolve_scope → aggregate_feature → aggregate_meaning →
aggregate_normalization → persist_metrics → record_phase → finalize

モジュール主参照: **MOD-BATCH-038**（Normalization Statistics Manager）。
Feature / Meaning / Normalization Aggregator 論理名は docs 上維持し、
初版は **追加採番せず MOD-BATCH-038 に内包**する（仕様書 §18.1 No.11 / §18.2 No.3）。

物理書込 IF = IF-DB-BATCH-016 のみ。
phase_log 物理名は `feature_distribution_metric_recorded` 1 フェーズ代表
（meaning_ / normalization_ 専用 phase enum は追加しない）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from batch.application.current_versions import (
    CurrentVersionResolveError,
    CurrentVersionResolver,
)
from batch.application.distribution_metrics.aggregator import (
    FeatureMetricAggregationError,
    aggregate_feature_metrics,
    aggregate_meaning_metrics,
    aggregate_normalization_metrics,
)
from batch.application.distribution_metrics.models import (
    AggregationScope,
    DistributionMetricsJobResult,
    MetricUpsertRow,
    ScopeResolve,
    TriggerMode,
)
from batch.application.distribution_metrics.repositories import (
    DistributionMetricsRepositories,
)
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger

BATCH_ID = "BATCH-016"
DISTRIBUTION_METRICS_PHASES: tuple[str, ...] = (
    "open_run",
    "resolve_scope",
    "aggregate_feature",
    "aggregate_meaning",
    "aggregate_normalization",
    "persist_metrics",
    "record_phase",
    "finalize",
)

DEFAULT_SEMANTIC_CONFIG_VERSION = "scaffold-semantic-config-v1"
PHASE_FEATURE_DISTRIBUTION_RECORDED = "feature_distribution_metric_recorded"
VALID_TRIGGER_MODES: frozenset[str] = frozenset({"dispatch", "chain", "schedule"})
VALID_AGGREGATION_SCOPES: frozenset[str] = frozenset(
    {"batch_run", "daily", "semantic_config_version"}
)


class DistributionMetricsError(Exception):
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


def resolve_scope(
    *,
    trigger_mode: str,
    job_run_id: str,
    semantic_config_version_id: str | None = None,
    aggregation_scope_override: str | None = None,
    now: datetime | None = None,
) -> ScopeResolve:
    """trigger_mode / env override から aggregation_scope を解決する.

    - dispatch / chain → batch_run（aggregation_key=None）
    - schedule → daily（aggregation_key=YYYY-MM-DD UTC）
    - BATCH_DISTRIBUTION_METRICS_AGGREGATION_SCOPE 明示時は override
    """

    _ = job_run_id
    mode = (trigger_mode or "dispatch").strip().lower()
    if mode not in VALID_TRIGGER_MODES:
        raise DistributionMetricsError(
            "GRS-VAL-001",
            f"trigger_mode must be one of {sorted(VALID_TRIGGER_MODES)}, got {trigger_mode!r}",
        )
    typed_mode: TriggerMode = mode  # type: ignore[assignment]

    override = (aggregation_scope_override or "").strip() or None
    if override is not None:
        if override not in VALID_AGGREGATION_SCOPES:
            raise DistributionMetricsError(
                "GRS-CFG-001",
                f"invalid aggregation_scope override: {override!r}",
            )
        scope: AggregationScope = override  # type: ignore[assignment]
    elif typed_mode in {"dispatch", "chain"}:
        scope = "batch_run"
    else:
        scope = "daily"

    ts = now or datetime.now(UTC)
    if scope == "batch_run":
        aggregation_key: str | None = None
    elif scope == "daily":
        aggregation_key = ts.strftime("%Y-%m-%d")
    else:
        aggregation_key = None

    # 後方互換フォールバック。live CLI（__main__）は CurrentVersionResolver 注入で
    # 未指定時にここへ落とさず、解決失敗時は例外にする（scaffold 文字列フォールバック禁止）。
    version = (semantic_config_version_id or "").strip() or DEFAULT_SEMANTIC_CONFIG_VERSION
    return ScopeResolve(
        aggregation_scope=scope,
        aggregation_key=aggregation_key,
        semantic_config_version_id=version,
        trigger_mode=typed_mode,
    )


class DistributionMetricsJob:
    """MOD-BATCH-038 内包の分布メトリクス集計オーケストレータ."""

    def __init__(
        self,
        *,
        repositories: DistributionMetricsRepositories,
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
        trigger_mode: str = "dispatch",
        semantic_config_version_id: str | None = None,
        aggregation_scope: str | None = None,
        include_item_embedding: bool = False,
        include_user_meaning: bool = False,
        trace_id: str | None = None,
        now: datetime | None = None,
    ) -> DistributionMetricsJobResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        _ = bound_logger
        result = DistributionMetricsJobResult(
            batch_id=BATCH_ID,
            job_run_id=job_run_id,
            status="failed",
            include_item_embedding=include_item_embedding,
            include_user_meaning=include_user_meaning,
        )

        if _is_batch_already_running(self._tracker):
            result.error_codes.append("GRS-BAT-003")
            self._repos.record_error(code="GRS-BAT-003", summary="batch already running")
            return result

        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)
        result.completed_phases.append("open_run")

        try:
            resolved_version = (semantic_config_version_id or "").strip() or None
            if resolved_version is None and self._version_resolver is not None:
                try:
                    resolved_version = self._version_resolver.resolve_semantic()
                except CurrentVersionResolveError as exc:
                    raise DistributionMetricsError(exc.code, exc.message) from exc
            scope = resolve_scope(
                trigger_mode=trigger_mode,
                job_run_id=job_run_id,
                semantic_config_version_id=resolved_version,
                aggregation_scope_override=aggregation_scope,
                now=now,
            )
            result.aggregation_scope = scope.aggregation_scope
            result.aggregation_key = scope.aggregation_key
            result.semantic_config_version_id = scope.semantic_config_version_id
            result.completed_phases.append("resolve_scope")

            # 入力は現行正規化 version + item 単位の最新冪等キー組に限定する
            # （BATCH-016 §6.2.1 / item_feature §12.4）。混在全行読取は禁止。
            normalization_version_id: str | None = None
            if self._version_resolver is not None:
                try:
                    normalization_version_id = self._version_resolver.resolve_normalization(
                        semantic_config_version_id=scope.semantic_config_version_id
                    )
                except CurrentVersionResolveError as exc:
                    raise DistributionMetricsError(exc.code, exc.message) from exc

            features = self._repos.load_item_features(
                semantic_config_version_id=scope.semantic_config_version_id,
                feature_normalization_version_id=normalization_version_id,
            )
            item_meanings = self._repos.load_item_meanings(
                semantic_config_version_id=scope.semantic_config_version_id,
                feature_normalization_version_id=normalization_version_id,
            )
            if not features:
                raise DistributionMetricsError("GRS-VAL-001", "item_feature input missing")
            if not item_meanings:
                raise DistributionMetricsError("GRS-VAL-001", "item_meaning input missing")

            if include_item_embedding:
                embeddings = self._repos.load_item_embeddings()
                result.item_embedding_read_count = len(embeddings)
            else:
                result.item_embedding_read_count = 0

            try:
                feature_rows = aggregate_feature_metrics(
                    features=features,
                    scope=scope,
                    batch_run_id=job_run_id,
                )
            except FeatureMetricAggregationError as exc:
                # 入力不整合は他の検証と同じ GRS-VAL-001 経路（error_log / failed）へ寄せる。
                raise DistributionMetricsError("GRS-VAL-001", str(exc)) from exc
            result.completed_phases.append("aggregate_feature")

            user_meanings = (
                self._repos.load_user_meanings(
                    semantic_config_version_id=scope.semantic_config_version_id
                )
                if include_user_meaning
                else ()
            )
            meaning_rows = aggregate_meaning_metrics(
                item_meanings=item_meanings,
                user_meanings=user_meanings,
                scope=scope,
                batch_run_id=job_run_id,
                include_user_meaning=include_user_meaning,
            )
            result.user_meaning_aggregated = include_user_meaning and any(
                r.entity_type == "user" for r in meaning_rows
            )
            result.completed_phases.append("aggregate_meaning")

            normalization_rows = aggregate_normalization_metrics(
                features=features,
                scope=scope,
                batch_run_id=job_run_id,
            )
            result.completed_phases.append("aggregate_normalization")

            self._repos.persist_metrics(
                feature_rows=tuple(feature_rows),
                meaning_rows=tuple(meaning_rows),
                normalization_rows=tuple(normalization_rows),
            )
            result.completed_phases.append("persist_metrics")

            result.feature_metric_upsert_count = self._repos.feature_metric_upsert_count
            result.meaning_metric_upsert_count = self._repos.meaning_metric_upsert_count
            result.normalization_metric_upsert_count = (
                self._repos.normalization_metric_upsert_count
            )
            result.item_feature_write_count = self._repos.item_feature_write_count
            result.item_meaning_write_count = self._repos.item_meaning_write_count
            result.item_embedding_write_count = self._repos.item_embedding_write_count
            result.embedding_hash_write_count = self._repos.embedding_hash_write_count

            # phase_log は finalize 後の最終 status と揃える（部分成功を succeeded と誤記しない）
            return self._phase_finalize(result, feature_rows, meaning_rows, normalization_rows)
        except DistributionMetricsError as exc:
            result.error_codes.append(exc.code)
            self._repos.record_error(code=exc.code, summary=exc.message)
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            result.completed_phases.append("finalize")
            result.status = "failed"
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_finalize(
        self,
        result: DistributionMetricsJobResult,
        feature_rows: list[MetricUpsertRow],
        meaning_rows: list[MetricUpsertRow],
        normalization_rows: list[MetricUpsertRow],
    ) -> DistributionMetricsJobResult:
        if feature_rows and meaning_rows and normalization_rows:
            result.status = "succeeded"
            tracker_status = "succeeded"
        elif feature_rows or meaning_rows or normalization_rows:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        else:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"

        # 物理 phase_log は 1 フェーズ代表のみ。status は job 最終結果に合わせる。
        self._repos.record_phase(
            phase=PHASE_FEATURE_DISTRIBUTION_RECORDED,
            status=tracker_status,
        )
        result.completed_phases.append("record_phase")

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        result.completed_phases.append("finalize")
        return result
