"""Repositories for BATCH-013 Feature正規化.

``list_target_queues`` / ``load_item`` / ``load_raw_features`` /
``resolve_semantic_config_version``（seed 空時）は ``DbReader`` 経由（Wave E）。

queue OR は equals 二重 fetch + in-process。config version は JOIN せず
item_semantic → item_feature の順で equals 導出（コードコメント参照）。

書込（#1635 Wave 2 / #1688 / IF-DB-BATCH-014、#1695 hardening）:
- ``claim_or_continue``: semantic+processing は DB no-op。feature+queued は ``update_rows``
- ``update_queue_status``: keep_processing は DB no-op。終端は ``update_rows``
- ``persist_normalized_and_meaning``: ``item_feature`` normalized ``update_rows`` +
  ``item_meaning`` ``upsert_rows`` を ``DbWriter.transaction()`` で同一 tx 実行
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.feature_normalization.adapter import (
    DEFAULT_NORMALIZATION_VERSION,
    MVP_FEATURE_CODES,
)
from batch.application.feature_normalization.models import (
    ItemFeatureNormalizedUpdateRow,
    ItemMeaningUpsertRow,
    ItemRow,
    QueueRow,
    RawFeatureAxis,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"

_QUEUE_COLUMNS = (
    "item_generation_queue_id",
    "item_id",
    "generation_type",
    "queue_status",
    "retry_count",
    "queued_at",
    "started_at",
    "completed_at",
    "error_message",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "active_status",
    "is_active",
)
_SEMANTIC_COLUMNS = (
    "item_semantic_id",
    "item_id",
    "semantic_config_version_id",
)
_FEATURE_COLUMNS = (
    "item_id",
    "semantic_config_version_id",
    "feature_code",
    "feature_input_hash",
    "feature_normalization_version_id",
    "raw_feature_value",
    "normalized_feature_value",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass(frozen=True)
class ExistingNormalizedAxis:
    """skip 判定用の既存 normalized 軸（読取のみ）。"""

    feature_code: str
    feature_input_hash: str
    feature_normalization_version_id: str
    has_normalized_value: bool = True


@dataclass
class FeatureNormalizationRepositories:
    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    # (item_id, semantic_config_version_id) -> raw 8 axes（BATCH-012 生成物）
    seed_raw_features: dict[tuple[str, str], list[RawFeatureAxis]] = field(default_factory=dict)
    # (item_id, semantic_config_version_id) -> existing normalized axes
    seed_normalized: dict[tuple[str, str], list[ExistingNormalizedAxis]] = field(
        default_factory=dict
    )
    # item_id -> semantic_config_version_id（Config Resolver の scaffold hint）
    seed_config_versions: dict[str, str] = field(default_factory=dict)
    current_normalization_version_id: str = DEFAULT_NORMALIZATION_VERSION

    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    raw_features: dict[tuple[str, str], list[RawFeatureAxis]] = field(default_factory=dict)
    normalized: dict[tuple[str, str], list[ExistingNormalizedAxis]] = field(default_factory=dict)
    config_versions: dict[str, str] = field(default_factory=dict)

    item_feature_normalized_update_count: int = 0
    item_meaning_upsert_count: int = 0
    item_feature_raw_write_count: int = 0
    item_semantic_write_count: int = 0
    queue_insert_count: int = 0
    normalization_distribution_metric_write_count: int = 0
    normalized_update_rows: list[ItemFeatureNormalizedUpdateRow] = field(default_factory=list)
    item_meaning_rows: list[ItemMeaningUpsertRow] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind ``batch_run_id`` (= job_run_id UUID) for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def __post_init__(self) -> None:
        for seed in self.seed_queues:
            self.queues.setdefault(
                seed.item_generation_queue_id,
                {
                    "item_generation_queue_id": seed.item_generation_queue_id,
                    "item_id": seed.item_id,
                    "generation_type": seed.generation_type,
                    "queue_status": seed.queue_status,
                    "retry_count": seed.retry_count,
                    "queued_at": seed.queued_at,
                    "started_at": seed.started_at,
                    "completed_at": seed.completed_at,
                    "error_message": seed.error_message,
                },
            )
        for item in self.seed_items:
            self.items.setdefault(
                item.item_id,
                {
                    "item_id": item.item_id,
                    "source": item.source,
                    "external_item_code": item.external_item_code,
                    "active_status": item.active_status,
                    "is_active": item.is_active,
                },
            )
        for key, axes in self.seed_raw_features.items():
            self.raw_features[key] = list(axes)
        for key, axes in self.seed_normalized.items():
            self.normalized[key] = list(axes)
        self.config_versions.update(self.seed_config_versions)

    def list_target_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: semantic+processing 主経路 / feature+queued 副経路。embedding 除外."""

        if self.db_reader is not None:
            return self._list_target_queues_from_db(
                max_items=max_items,
                source=source,
                queue_batch_size=queue_batch_size,
                item_ids=item_ids,
                queue_ids=queue_ids,
            )

        item_set = set(item_ids) if item_ids else None
        queue_set = set(queue_ids) if queue_ids else None
        limit = max_items if queue_batch_size is None else min(max_items, queue_batch_size)
        targets: list[QueueRow] = []
        non_target = 0

        rows = sorted(self.queues.values(), key=lambda r: str(r["item_generation_queue_id"]))
        for row in rows:
            q = self._row_to_queue(row)
            if queue_set is not None and q.item_generation_queue_id not in queue_set:
                continue
            if item_set is not None and q.item_id not in item_set:
                continue

            item = self.items.get(q.item_id)
            if item is not None and str(item.get("source") or DEFAULT_SOURCE) != source:
                continue

            if q.generation_type == "embedding":
                if q.queue_status in {"queued", "processing"}:
                    non_target += 1
                continue

            is_primary = q.generation_type == "semantic" and q.queue_status == "processing"
            is_secondary = q.generation_type == "feature" and q.queue_status == "queued"
            if not (is_primary or is_secondary):
                continue

            targets.append(q)
            if len(targets) >= max(0, limit):
                break

        return targets, non_target

    def _list_target_queues_from_db(
        self,
        *,
        max_items: int,
        source: str,
        queue_batch_size: int | None,
        item_ids: tuple[str, ...] | None,
        queue_ids: tuple[str, ...] | None,
    ) -> tuple[list[QueueRow], int]:
        reader = self.db_reader
        if reader is None:
            return [], 0

        limit = max_items if queue_batch_size is None else min(max_items, queue_batch_size)
        candidate_rows: list[dict[str, object]] = []
        count_non_target = False

        if queue_ids:
            count_non_target = True
            for queue_id in queue_ids:
                if not queue_id:
                    continue
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=(("item_generation_queue_id", queue_id),),
                    limit=1,
                )
                candidate_rows.extend(result.rows)
        elif item_ids:
            count_non_target = True
            for item_id in item_ids:
                if not item_id:
                    continue
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=(("item_id", item_id),),
                    order_by=("item_generation_queue_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        else:
            fetch_cap = max(0, limit)
            if fetch_cap == 0:
                return [], 0
            fetch_limit = min(max(fetch_cap * 5, fetch_cap), 5000)
            primary = reader.fetch_rows(
                "item_generation_queue",
                columns=_QUEUE_COLUMNS,
                equals=(
                    ("generation_type", "semantic"),
                    ("queue_status", "processing"),
                ),
                order_by=("item_generation_queue_id",),
                limit=fetch_limit,
            )
            secondary = reader.fetch_rows(
                "item_generation_queue",
                columns=_QUEUE_COLUMNS,
                equals=(
                    ("generation_type", "feature"),
                    ("queue_status", "queued"),
                ),
                order_by=("item_generation_queue_id",),
                limit=fetch_limit,
            )
            candidate_rows.extend(primary.rows)
            candidate_rows.extend(secondary.rows)

        targets: list[QueueRow] = []
        non_target = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["item_generation_queue_id"])):
            q = self._cache_queue_row(row)
            if q.item_generation_queue_id in seen_ids:
                continue
            seen_ids.add(q.item_generation_queue_id)

            if count_non_target and q.generation_type == "embedding":
                if q.queue_status in {"queued", "processing"}:
                    non_target += 1
                continue

            is_primary = q.generation_type == "semantic" and q.queue_status == "processing"
            is_secondary = q.generation_type == "feature" and q.queue_status == "queued"
            if not (is_primary or is_secondary):
                continue

            item_row = self.items.get(q.item_id)
            if item_row is None:
                item_row = self._fetch_and_cache_item(q.item_id)
            if item_row is not None and str(item_row.get("source") or DEFAULT_SOURCE) != source:
                continue

            targets.append(q)
            if len(targets) >= max(0, limit):
                break

        return targets, non_target

    def claim_or_continue(
        self,
        *,
        item_generation_queue_id: str,
        started_at: datetime | None = None,
    ) -> QueueRow | None:
        """主経路 continue（DB no-op）/ 副経路 claim（条件付き UPDATE）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            return None
        status = row.get("queue_status")
        gen = row.get("generation_type")
        ts = started_at or datetime.now(UTC)

        if gen == "semantic" and status == "processing":
            # 既に processing。追加 UPDATE 不要（偽 op=continue_processing 廃止）。
            return self._row_to_queue(row)

        if gen == "feature" and status == "queued":
            result = self.db_writer.update_rows(
                "item_generation_queue",
                set_values={"queue_status": "processing", "started_at": ts},
                equals=(
                    ("item_generation_queue_id", item_generation_queue_id),
                    ("queue_status", "queued"),
                    ("generation_type", "feature"),
                ),
            )
            if result.rows_affected == 0:
                return None
            row["queue_status"] = "processing"
            row["started_at"] = ts
            return self._row_to_queue(row)

        return None

    def load_item(self, *, item_id: str) -> ItemRow:
        row = self.items.get(item_id)
        if row is None and self.db_reader is not None:
            row = self._fetch_and_cache_item(item_id)
        if row is None:
            raise KeyError(f"item not found: {item_id}")
        return ItemRow(
            item_id=str(row["item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row.get("external_item_code") or ""),
            active_status=str(row.get("active_status") or "active"),
            is_active=bool(row.get("is_active", True)),
        )

    def resolve_semantic_config_version(self, *, item_id: str) -> str | None:
        """Config Resolver: item_id -> semantic_config_version_id.

        Seed map を優先。空で reader がある場合は JOIN せず:
        1) ``item_semantic`` の equals(item_id) から version を取る（意味連鎖の正本）
        2) 無ければ ``item_feature`` の equals(item_id) から導出
        """

        if item_id in self.config_versions:
            return self.config_versions.get(item_id)

        if self.db_reader is None:
            return None

        semantic = self.db_reader.fetch_rows(
            "item_semantic",
            columns=_SEMANTIC_COLUMNS,
            equals=(("item_id", item_id),),
            order_by=("item_semantic_id",),
            limit=1,
        )
        if semantic.rows:
            version = str(semantic.rows[0]["semantic_config_version_id"])
            self.config_versions[item_id] = version
            return version

        feature = self.db_reader.fetch_rows(
            "item_feature",
            columns=("item_id", "semantic_config_version_id"),
            equals=(("item_id", item_id),),
            order_by=("semantic_config_version_id",),
            limit=1,
        )
        if feature.rows:
            version = str(feature.rows[0]["semantic_config_version_id"])
            self.config_versions[item_id] = version
            return version
        return None

    def load_raw_features(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
    ) -> tuple[RawFeatureAxis, ...]:
        """BATCH-012（IF-DB-BATCH-013）が生成した raw 8 軸を読取（変更しない）。"""

        key = (item_id, semantic_config_version_id)
        cached = self.raw_features.get(key)
        if cached is not None:
            return tuple(cached)
        if self.db_reader is None:
            return ()
        result = self.db_reader.fetch_rows(
            "item_feature",
            columns=_FEATURE_COLUMNS,
            equals=(
                ("item_id", item_id),
                ("semantic_config_version_id", semantic_config_version_id),
            ),
            order_by=("feature_code",),
            limit=50,
        )
        axes = [
            RawFeatureAxis(
                feature_code=str(row["feature_code"]),
                feature_input_hash=str(row.get("feature_input_hash") or ""),
                feature_normalization_version_id=str(
                    row.get("feature_normalization_version_id") or ""
                ),
                raw_feature_value=(
                    float(row["raw_feature_value"])
                    if row.get("raw_feature_value") is not None
                    else 0.0
                ),
            )
            for row in result.rows
            if row.get("raw_feature_value") is not None
        ]
        self.raw_features[key] = axes
        return tuple(axes)

    def should_skip_normalization(
        self,
        *,
        item_id: str,
        semantic_config_version_id: str,
        feature_input_hash: str,
        feature_normalization_version_id: str,
    ) -> bool:
        """§9.3: normalized 8 軸すべてが同一 hash + 現行 version で存在すれば skip."""

        key = (item_id, semantic_config_version_id)
        axes = self.normalized.get(key, [])
        if not axes and self.db_reader is not None:
            axes = self._fetch_and_cache_normalized(item_id, semantic_config_version_id)
        by_code = {a.feature_code: a for a in axes}
        if len(by_code) < len(MVP_FEATURE_CODES):
            return False
        for code in MVP_FEATURE_CODES:
            axis = by_code.get(code)
            if axis is None:
                return False
            if axis.feature_input_hash != feature_input_hash:
                return False
            if axis.feature_normalization_version_id != feature_normalization_version_id:
                return False
            if not axis.has_normalized_value:
                return False
        return True

    def persist_normalized_and_meaning(
        self,
        *,
        normalized_rows: tuple[ItemFeatureNormalizedUpdateRow, ...],
        item_meaning_row: ItemMeaningUpsertRow | None,
    ) -> None:
        """IF-DB-BATCH-014: normalized UPDATE + item_meaning UPSERT 本配線。

        各軸は ``update_rows``（``normalized_feature_value`` のみ）。
        ``raw_feature_value`` / 偽 ``op`` は payload に含めない（BATCH-012 責務）。
        ``item_meaning_row`` が None の場合は normalized 更新のみ（8 軸欠損等）。

        複数 DML は ``DbWriter.transaction()`` で同一 connection / 同一 tx にまとめる（#1695）。
        """

        if not normalized_rows:
            return

        self.normalized_update_rows.extend(normalized_rows)
        self.item_feature_normalized_update_count += len(normalized_rows)
        if item_meaning_row is not None:
            self.item_meaning_rows.append(item_meaning_row)
            self.item_meaning_upsert_count += 1

        with self.db_writer.transaction():
            for r in normalized_rows:
                self.db_writer.update_rows(
                    "item_feature",
                    set_values={"normalized_feature_value": r.normalized_feature_value},
                    equals=(
                        ("item_id", r.item_id),
                        ("semantic_config_version_id", r.semantic_config_version_id),
                        ("feature_code", r.feature_code),
                        ("feature_input_hash", r.feature_input_hash),
                        (
                            "feature_normalization_version_id",
                            r.feature_normalization_version_id,
                        ),
                    ),
                )

            if item_meaning_row is not None:
                self.db_writer.upsert_rows(
                    "item_meaning",
                    (
                        {
                            "item_id": item_meaning_row.item_id,
                            "semantic_config_version_id": (
                                item_meaning_row.semantic_config_version_id
                            ),
                            "feature_normalization_version_id": (
                                item_meaning_row.feature_normalization_version_id
                            ),
                            "item_social": item_meaning_row.item_social,
                            "item_symbolic": item_meaning_row.item_symbolic,
                            "generated_at": item_meaning_row.generated_at,
                        },
                    ),
                    conflict_columns=("item_id", "semantic_config_version_id"),
                    update_columns=(
                        "feature_normalization_version_id",
                        "item_social",
                        "item_symbolic",
                        "generated_at",
                    ),
                )

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
        keep_processing: bool = False,
    ) -> None:
        """Queue status 更新。正規化成功時は processing 維持（DB no-op）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")
        if keep_processing:
            # 成功時: status は processing のまま。完了時刻は付けない（後続 Batch 継続）。
            # 偽 op=normalize_success_keep_processing 廃止。
            return

        set_values: dict[str, object] = {"queue_status": queue_status}
        if completed_at is not None:
            set_values["completed_at"] = completed_at
            row["completed_at"] = completed_at
        if error_message is not None:
            set_values["error_message"] = error_message
            row["error_message"] = error_message
        row["queue_status"] = queue_status
        self.db_writer.update_rows(
            "item_generation_queue",
            set_values=set_values,
            equals=(("item_generation_queue_id", item_generation_queue_id),),
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        emit_phase(
            phase_logs=self.phase_logs,
            phase_log_writer=self.phase_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            phase=phase,
            status=status,
        )

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        item_generation_queue_id: str | None = None,
        item_id: str | None = None,
    ) -> None:
        detail: dict[str, object] = {}
        if item_generation_queue_id is not None:
            detail["item_generation_queue_id"] = item_generation_queue_id
        if item_id is not None:
            detail["item_id"] = item_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"item_generation_queue_id": item_generation_queue_id, "item_id": item_id},
            detail=detail or None,
        )

    def _ensure_queue_hydrated(self, item_generation_queue_id: str) -> dict[str, object] | None:
        row = self.queues.get(item_generation_queue_id)
        if row is not None:
            return row
        if self.db_reader is None:
            return None
        result = self.db_reader.fetch_rows(
            "item_generation_queue",
            columns=_QUEUE_COLUMNS,
            equals=(("item_generation_queue_id", item_generation_queue_id),),
            limit=1,
        )
        if not result.rows:
            return None
        self._cache_queue_row(result.rows[0])
        return self.queues.get(item_generation_queue_id)

    def _fetch_and_cache_item(self, item_id: str) -> dict[str, object] | None:
        reader = self.db_reader
        if reader is None:
            return None
        result = reader.fetch_rows(
            "item",
            columns=_ITEM_COLUMNS,
            equals=(("item_id", item_id),),
            limit=1,
        )
        if not result.rows:
            return None
        return self._cache_item_row(result.rows[0])

    def _fetch_and_cache_normalized(
        self,
        item_id: str,
        semantic_config_version_id: str,
    ) -> list[ExistingNormalizedAxis]:
        reader = self.db_reader
        if reader is None:
            return []
        result = reader.fetch_rows(
            "item_feature",
            columns=_FEATURE_COLUMNS,
            equals=(
                ("item_id", item_id),
                ("semantic_config_version_id", semantic_config_version_id),
            ),
            order_by=("feature_code",),
            limit=50,
        )
        axes = [
            ExistingNormalizedAxis(
                feature_code=str(row["feature_code"]),
                feature_input_hash=str(row.get("feature_input_hash") or ""),
                feature_normalization_version_id=str(
                    row.get("feature_normalization_version_id") or ""
                ),
                has_normalized_value=row.get("normalized_feature_value") is not None,
            )
            for row in result.rows
        ]
        self.normalized[(item_id, semantic_config_version_id)] = axes
        return axes

    def _cache_queue_row(self, row: dict[str, object]) -> QueueRow:
        payload = dict(row)
        qid = str(payload["item_generation_queue_id"])
        self.queues[qid] = payload
        return self._row_to_queue(payload)

    def _cache_item_row(self, row: dict[str, object]) -> dict[str, object]:
        payload = {
            "item_id": str(row["item_id"]),
            "source": str(row.get("source") or DEFAULT_SOURCE),
            "external_item_code": str(row.get("external_item_code") or ""),
            "active_status": str(row.get("active_status") or "active"),
            "is_active": bool(row.get("is_active", True)),
        }
        self.items[str(payload["item_id"])] = payload
        return payload

    @staticmethod
    def _row_to_queue(row: dict[str, object]) -> QueueRow:
        return QueueRow(
            item_generation_queue_id=str(row["item_generation_queue_id"]),
            item_id=str(row["item_id"]),
            generation_type=row["generation_type"],  # type: ignore[arg-type]
            queue_status=row["queue_status"],  # type: ignore[arg-type]
            retry_count=int(row.get("retry_count") or 0),
            queued_at=row.get("queued_at"),  # type: ignore[arg-type]
            started_at=row.get("started_at"),  # type: ignore[arg-type]
            completed_at=row.get("completed_at"),  # type: ignore[arg-type]
            error_message=str(row["error_message"]) if row.get("error_message") else None,
        )
