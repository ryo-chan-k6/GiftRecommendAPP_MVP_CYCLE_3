"""Repositories for BATCH-016 分布メトリクス集計.

``load_item_features`` / ``load_item_meanings``（および任意の
``load_user_meanings`` / ``load_item_embeddings``）は ``DbReader`` 経由（Wave G）。

Metric UPSERT は IF-DB-BATCH-016 として ``DbWriter.upsert_rows``（本番 SQL）で本配線する。
- ``aggregation_scope == batch_run``: conflict = ``uq_*_snapshot_key``（WHERE なし）
- それ以外: conflict = ``uq_*_non_batch_snapshot`` 列 +
  ``conflict_where=(("aggregation_scope", "<>", "batch_run"),)``（#1695）

- item_feature / item_meaning READ ONLY（必須入力）
- item_embedding / user_meaning READ ONLY（任意・フラグ OFF 既定）
- 3 Metric テーブル UPSERT（IF-DB-BATCH-016）のみ書込
- IF-DB-BATCH-014 / IF-DB-BATCH-015 / IF-VEC-BATCH-001 非書込
  （item_feature / item_meaning / item_embedding / embedding_hash write=0）
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.distribution_metrics.models import (
    ItemEmbeddingRow,
    ItemFeatureRow,
    ItemMeaningRow,
    MetricUpsertRow,
    UserMeaningRow,
)
from batch.infrastructure.db import ConflictWhere, DbReader, DbWriter

_ITEM_FEATURE_COLUMNS = (
    "item_id",
    "semantic_config_version_id",
    "feature_code",
    "raw_feature_value",
    "normalized_feature_value",
    "feature_normalization_version_id",
    "feature_input_hash",
    "generated_at",
)

_DATETIME_MIN = datetime.min.replace(tzinfo=UTC)


def _as_utc_datetime(value: object) -> datetime:
    """Normalize DB / seed timestamps for generation comparison."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return _DATETIME_MIN
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return _DATETIME_MIN


def select_current_generation_item_feature_rows(
    rows: Sequence[dict[str, object]],
) -> list[dict[str, object]]:
    """item 単位で最新 generated_at の冪等キー組を選ぶ（item_feature §12.4 / BATCH-016 §6.2.1）。

    同一 ``item_id`` + ``semantic_config_version_id`` 配下に複数
    ``feature_input_hash`` / ``feature_normalization_version_id`` 世代が同居し得る。
    各 item について ``generated_at`` 最大の冪等キー組の行だけを返す。

    ``generated_at`` / ``feature_input_hash`` がどちらも欠ける seed 行は、後方互換のため
    選定せずそのまま返す（単体テストの従来 fixture）。
    """

    candidates = [dict(row) for row in rows]
    if not candidates:
        return []

    has_generation_keys = any(
        row.get("generated_at") is not None or row.get("feature_input_hash")
        for row in candidates
    )
    if not has_generation_keys:
        return candidates

    by_item: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in candidates:
        item_key = (
            str(row.get("item_id") or ""),
            str(row.get("semantic_config_version_id") or ""),
        )
        by_item.setdefault(item_key, []).append(row)

    selected: list[dict[str, object]] = []
    for item_rows in by_item.values():
        groups: dict[tuple[str, str], list[dict[str, object]]] = {}
        for row in item_rows:
            key = (
                str(row.get("feature_input_hash") or ""),
                str(row.get("feature_normalization_version_id") or ""),
            )
            groups.setdefault(key, []).append(row)

        def _group_generated_at(group_rows: list[dict[str, object]]) -> datetime:
            return max(
                (_as_utc_datetime(r.get("generated_at")) for r in group_rows),
                default=_DATETIME_MIN,
            )

        best_key = max(groups.keys(), key=lambda key: _group_generated_at(groups[key]))
        selected.extend(groups[best_key])

    selected.sort(
        key=lambda row: (
            str(row.get("item_id") or ""),
            str(row.get("feature_code") or ""),
        )
    )
    return selected
_ITEM_MEANING_COLUMNS = (
    "item_id",
    "semantic_config_version_id",
    "item_social",
    "item_symbolic",
    "feature_normalization_version_id",
)
_ITEM_EMBEDDING_COLUMNS = (
    "item_id",
    "model_version_id",
    "embedding_input_hash",
)

_FEATURE_CONFLICT_COLUMNS = (
    "batch_run_id",
    "semantic_config_version_id",
    "feature_code",
    "value_layer",
    "aggregation_scope",
    "aggregation_key",
)
_FEATURE_PARTIAL_CONFLICT_COLUMNS = (
    "aggregation_scope",
    "aggregation_key",
    "semantic_config_version_id",
    "feature_code",
    "value_layer",
)
_MEANING_CONFLICT_COLUMNS = (
    "batch_run_id",
    "semantic_config_version_id",
    "entity_type",
    "value_layer",
    "feature_normalization_version_id",
    "aggregation_scope",
    "aggregation_key",
)
_MEANING_PARTIAL_CONFLICT_COLUMNS = (
    "aggregation_scope",
    "aggregation_key",
    "semantic_config_version_id",
    "entity_type",
    "value_layer",
    "feature_normalization_version_id",
)
_NORMALIZATION_CONFLICT_COLUMNS = (
    "batch_run_id",
    "semantic_config_version_id",
    "feature_code",
    "value_layer",
    "feature_normalization_version_id",
    "aggregation_scope",
    "aggregation_key",
)
_NORMALIZATION_PARTIAL_CONFLICT_COLUMNS = (
    "aggregation_scope",
    "aggregation_key",
    "semantic_config_version_id",
    "feature_code",
    "value_layer",
    "feature_normalization_version_id",
)

_NON_BATCH_CONFLICT_WHERE: tuple[tuple[str, str, object], ...] = (
    ("aggregation_scope", "<>", "batch_run"),
)

_FEATURE_UPDATE_COLUMNS = (
    "sample_count",
    "mean",
    "stddev",
    "min_value",
    "max_value",
    "calculated_at",
    "updated_at",
)
_MEANING_UPDATE_COLUMNS = _FEATURE_UPDATE_COLUMNS
_NORMALIZATION_UPDATE_COLUMNS = (
    "sample_count",
    "mean",
    "stddev",
    "min_value",
    "max_value",
    "sigma_zero_count",
    "calculated_at",
    "updated_at",
)


_NON_BATCH_CONFLICT_WHERE: ConflictWhere = (("aggregation_scope", "<>", "batch_run"),)


def _metric_conflict_target(
    *,
    aggregation_scope: str,
    batch_run_columns: tuple[str, ...],
    partial_columns: tuple[str, ...],
) -> tuple[tuple[str, ...], ConflictWhere | None]:
    """batch_run → snapshot_key UNIQUE / それ以外 → partial UNIQUE + WHERE."""

    if aggregation_scope == "batch_run":
        return batch_run_columns, None
    return partial_columns, _NON_BATCH_CONFLICT_WHERE


def _feature_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """feature_distribution_metric UNIQUE / 部分 UNIQUE キー.

    batch_run: (batch_run_id, semantic_config_version_id, feature_code, value_layer,
                aggregation_scope, aggregation_key)
    非 batch_run（部分 UNIQUE）: batch_run_id を除く
    """

    base = (
        row.semantic_config_version_id,
        row.feature_code,
        row.value_layer,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _meaning_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """meaning_distribution_metric UNIQUE / 部分 UNIQUE キー."""

    base = (
        row.semantic_config_version_id,
        row.entity_type,
        row.value_layer,
        row.feature_normalization_version_id,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _normalization_upsert_key(row: MetricUpsertRow) -> tuple[object, ...]:
    """normalization_distribution_metric UNIQUE / 部分 UNIQUE キー."""

    base = (
        row.semantic_config_version_id,
        row.feature_code,
        row.value_layer,
        row.feature_normalization_version_id,
        row.aggregation_scope,
        row.aggregation_key,
    )
    if row.aggregation_scope == "batch_run":
        return (row.batch_run_id, *base)
    return base


def _upsert_rows(
    existing: list[MetricUpsertRow],
    incoming: tuple[MetricUpsertRow, ...],
    key_fn,
) -> int:
    """同一キーは上書き。戻り値は UPSERT 操作件数（incoming 件数）。"""

    index_by_key: dict[tuple[object, ...], int] = {
        key_fn(row): i for i, row in enumerate(existing)
    }
    for row in incoming:
        key = key_fn(row)
        if key in index_by_key:
            existing[index_by_key[key]] = row
        else:
            index_by_key[key] = len(existing)
            existing.append(row)
    return len(incoming)


def _optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object | None) -> float | None:
    if value is None:
        return None
    return float(value)


def _feature_payload(row: MetricUpsertRow, *, calculated_at: datetime) -> dict[str, object]:
    """feature_distribution_metric DDL 列のみ（entity_type / sigma_zero / table / op なし）。"""

    return {
        "batch_run_id": row.batch_run_id,
        "semantic_config_version_id": row.semantic_config_version_id,
        "feature_normalization_version_id": row.feature_normalization_version_id,
        "feature_code": row.feature_code,
        "aggregation_scope": row.aggregation_scope,
        "aggregation_key": row.aggregation_key,
        "value_layer": row.value_layer,
        "sample_count": row.sample_count,
        "mean": row.mean,
        "stddev": row.stddev,
        "min_value": row.min_value,
        "max_value": row.max_value,
        "calculated_at": calculated_at,
        "updated_at": calculated_at,
    }


def _meaning_payload(row: MetricUpsertRow, *, calculated_at: datetime) -> dict[str, object]:
    """meaning_distribution_metric DDL 列のみ（feature_code / sigma_zero / table / op なし）。"""

    return {
        "batch_run_id": row.batch_run_id,
        "semantic_config_version_id": row.semantic_config_version_id,
        "feature_normalization_version_id": row.feature_normalization_version_id,
        "entity_type": row.entity_type,
        "value_layer": row.value_layer,
        "aggregation_scope": row.aggregation_scope,
        "aggregation_key": row.aggregation_key,
        "sample_count": row.sample_count,
        "mean": row.mean,
        "stddev": row.stddev,
        "min_value": row.min_value,
        "max_value": row.max_value,
        "calculated_at": calculated_at,
        "updated_at": calculated_at,
    }


def _normalization_payload(
    row: MetricUpsertRow, *, calculated_at: datetime
) -> dict[str, object]:
    """normalization_distribution_metric DDL 列のみ（entity_type / table / op なし）。"""

    return {
        "batch_run_id": row.batch_run_id,
        "semantic_config_version_id": row.semantic_config_version_id,
        "feature_normalization_version_id": row.feature_normalization_version_id,
        "feature_code": row.feature_code,
        "value_layer": row.value_layer,
        "aggregation_scope": row.aggregation_scope,
        "aggregation_key": row.aggregation_key,
        "sample_count": row.sample_count,
        "mean": row.mean,
        "stddev": row.stddev,
        "min_value": row.min_value,
        "max_value": row.max_value,
        "sigma_zero_count": 0 if row.sigma_zero_count is None else row.sigma_zero_count,
        "calculated_at": calculated_at,
        "updated_at": calculated_at,
    }


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class DistributionMetricsRepositories:
    """Facade: 入力読取 / IF-DB-BATCH-016 UPSERT / phase・error logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_item_features: list[ItemFeatureRow] = field(default_factory=list)
    seed_item_meanings: list[ItemMeaningRow] = field(default_factory=list)
    seed_user_meanings: list[UserMeaningRow] = field(default_factory=list)
    seed_item_embeddings: list[ItemEmbeddingRow] = field(default_factory=list)

    item_features: list[ItemFeatureRow] = field(default_factory=list)
    item_meanings: list[ItemMeaningRow] = field(default_factory=list)
    user_meanings: list[UserMeaningRow] = field(default_factory=list)
    item_embeddings: list[ItemEmbeddingRow] = field(default_factory=list)

    feature_metric_rows: list[MetricUpsertRow] = field(default_factory=list)
    meaning_metric_rows: list[MetricUpsertRow] = field(default_factory=list)
    normalization_metric_rows: list[MetricUpsertRow] = field(default_factory=list)

    feature_metric_upsert_count: int = 0
    meaning_metric_upsert_count: int = 0
    normalization_metric_upsert_count: int = 0

    # 隣接 IF 非書込カウンタ（常に 0 を維持し UT で証明する）
    item_feature_write_count: int = 0
    item_meaning_write_count: int = 0
    item_embedding_write_count: int = 0
    embedding_hash_write_count: int = 0

    item_embedding_read_count: int = 0
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    _batch_run_id: str | None = field(default=None, repr=False)
    _trace_id: str | None = field(default=None, repr=False)


    def bind_run(self, *, batch_run_id: str, trace_id: str | None = None) -> None:
        """Bind ``batch_run_id`` (= job_run_id UUID) for observability DB writes."""

        self._batch_run_id = batch_run_id
        self._trace_id = trace_id

    def __post_init__(self) -> None:
        self.item_features = list(self.seed_item_features)
        self.item_meanings = list(self.seed_item_meanings)
        self.user_meanings = list(self.seed_user_meanings)
        self.item_embeddings = list(self.seed_item_embeddings)

    def load_item_features(
        self,
        *,
        semantic_config_version_id: str,
        feature_normalization_version_id: str | None = None,
    ) -> tuple[ItemFeatureRow, ...]:
        """semantic_config_version 配下の現行世代 item_feature を読む.

        ``feature_normalization_version_id`` 指定時はその version のみに絞り、
        さらに item 単位で最新 ``generated_at`` の冪等キー組を選ぶ。
        """

        norm_version = (feature_normalization_version_id or "").strip() or None
        if self.db_reader is not None:
            equals: list[tuple[str, object]] = [
                ("semantic_config_version_id", semantic_config_version_id),
            ]
            if norm_version is not None:
                equals.append(("feature_normalization_version_id", norm_version))
            result = self.db_reader.fetch_rows(
                "item_feature",
                columns=_ITEM_FEATURE_COLUMNS,
                equals=tuple(equals),
                order_by=("item_id", "feature_code"),
            )
            selected = select_current_generation_item_feature_rows(result.rows)
            return tuple(self._row_to_item_feature(row) for row in selected)

        seed_dicts: list[dict[str, object]] = []
        for row in self.item_features:
            if row.semantic_config_version_id != semantic_config_version_id:
                continue
            if (
                norm_version is not None
                and row.feature_normalization_version_id != norm_version
            ):
                continue
            seed_dicts.append(
                {
                    "item_id": row.item_id,
                    "semantic_config_version_id": row.semantic_config_version_id,
                    "feature_code": row.feature_code,
                    "raw_feature_value": row.raw_feature_value,
                    "normalized_feature_value": row.normalized_feature_value,
                    "feature_normalization_version_id": row.feature_normalization_version_id,
                    "feature_input_hash": row.feature_input_hash,
                    "generated_at": row.generated_at,
                }
            )
        selected = select_current_generation_item_feature_rows(seed_dicts)
        return tuple(self._row_to_item_feature(row) for row in selected)

    def load_item_meanings(
        self,
        *,
        semantic_config_version_id: str,
        feature_normalization_version_id: str | None = None,
    ) -> tuple[ItemMeaningRow, ...]:
        """semantic_config_version 配下の item_meaning を読む.

        ``feature_normalization_version_id`` 指定時はその version のみに絞る
        （UNIQUE は item×scv のため世代同居は無いが、旧 version 行の混在を避ける）。
        """

        norm_version = (feature_normalization_version_id or "").strip() or None
        if self.db_reader is not None:
            equals: list[tuple[str, object]] = [
                ("semantic_config_version_id", semantic_config_version_id),
            ]
            if norm_version is not None:
                equals.append(("feature_normalization_version_id", norm_version))
            result = self.db_reader.fetch_rows(
                "item_meaning",
                columns=_ITEM_MEANING_COLUMNS,
                equals=tuple(equals),
                order_by=("item_id",),
            )
            return tuple(self._row_to_item_meaning(row) for row in result.rows)
        return tuple(
            row
            for row in self.item_meanings
            if row.semantic_config_version_id == semantic_config_version_id
            and (
                norm_version is None
                or row.feature_normalization_version_id == norm_version
            )
        )

    def load_user_meanings(self, *, semantic_config_version_id: str) -> tuple[UserMeaningRow, ...]:
        # user_meaning に semantic_config_version_id 列は無い（recommendation_run JOIN が必要）。
        # DbReader JOIN 拡張 / E4 は out of scope。任意フラグ時も seed 経路のみ。
        return tuple(
            row
            for row in self.user_meanings
            if row.semantic_config_version_id == semantic_config_version_id
        )

    def load_item_embeddings(self) -> tuple[ItemEmbeddingRow, ...]:
        """任意監視入力の読取のみ。IF-VEC-BATCH-001 Upsert は行わない。"""

        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_embedding",
                columns=_ITEM_EMBEDDING_COLUMNS,
                order_by=("item_id", "model_version_id"),
            )
            rows = tuple(self._row_to_item_embedding(row) for row in result.rows)
            self.item_embedding_read_count = len(rows)
            return rows

        rows = tuple(self.item_embeddings)
        self.item_embedding_read_count = len(rows)
        return rows

    def persist_metrics(
        self,
        *,
        feature_rows: tuple[MetricUpsertRow, ...],
        meaning_rows: tuple[MetricUpsertRow, ...],
        normalization_rows: tuple[MetricUpsertRow, ...],
    ) -> None:
        """IF-DB-BATCH-016: 3 Metric テーブルへ UPSERT（同一 UNIQUE キーは上書き）。

        ``calculated_at`` / ``updated_at`` は DDL NOT NULL のため、persist 時点の UTC now を付与する。
        ``aggregation_scope == batch_run`` は ``uq_*_snapshot_key``、
        それ以外は ``uq_*_non_batch_snapshot``（``conflict_where``）を使う（#1695）。
        """

        calculated_at = datetime.now(UTC)

        if feature_rows:
            ops = _upsert_rows(self.feature_metric_rows, feature_rows, _feature_upsert_key)
            self.feature_metric_upsert_count += ops
            conflict_columns, conflict_where = _metric_conflict_target(
                aggregation_scope=feature_rows[0].aggregation_scope,
                batch_run_columns=_FEATURE_CONFLICT_COLUMNS,
                partial_columns=_FEATURE_PARTIAL_CONFLICT_COLUMNS,
            )
            self.db_writer.upsert_rows(
                "feature_distribution_metric",
                tuple(_feature_payload(r, calculated_at=calculated_at) for r in feature_rows),
                conflict_columns=conflict_columns,
                update_columns=_FEATURE_UPDATE_COLUMNS,
                conflict_where=conflict_where,
            )
        if meaning_rows:
            ops = _upsert_rows(self.meaning_metric_rows, meaning_rows, _meaning_upsert_key)
            self.meaning_metric_upsert_count += ops
            conflict_columns, conflict_where = _metric_conflict_target(
                aggregation_scope=meaning_rows[0].aggregation_scope,
                batch_run_columns=_MEANING_CONFLICT_COLUMNS,
                partial_columns=_MEANING_PARTIAL_CONFLICT_COLUMNS,
            )
            self.db_writer.upsert_rows(
                "meaning_distribution_metric",
                tuple(_meaning_payload(r, calculated_at=calculated_at) for r in meaning_rows),
                conflict_columns=conflict_columns,
                update_columns=_MEANING_UPDATE_COLUMNS,
                conflict_where=conflict_where,
            )
        if normalization_rows:
            ops = _upsert_rows(
                self.normalization_metric_rows, normalization_rows, _normalization_upsert_key
            )
            self.normalization_metric_upsert_count += ops
            conflict_columns, conflict_where = _metric_conflict_target(
                aggregation_scope=normalization_rows[0].aggregation_scope,
                batch_run_columns=_NORMALIZATION_CONFLICT_COLUMNS,
                partial_columns=_NORMALIZATION_PARTIAL_CONFLICT_COLUMNS,
            )
            self.db_writer.upsert_rows(
                "normalization_distribution_metric",
                tuple(
                    _normalization_payload(r, calculated_at=calculated_at)
                    for r in normalization_rows
                ),
                conflict_columns=conflict_columns,
                update_columns=_NORMALIZATION_UPDATE_COLUMNS,
                conflict_where=conflict_where,
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

    def record_error(self, *, code: str, summary: str) -> None:
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
        )

    @staticmethod
    def _row_to_item_feature(row: dict[str, object]) -> ItemFeatureRow:
        generated_raw = row.get("generated_at")
        generated_at: datetime | None
        if isinstance(generated_raw, datetime):
            generated_at = _as_utc_datetime(generated_raw)
        elif isinstance(generated_raw, str) and generated_raw.strip():
            generated_at = _as_utc_datetime(generated_raw)
        else:
            generated_at = None
        return ItemFeatureRow(
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            feature_code=str(row["feature_code"]),
            raw_feature_value=_optional_float(row.get("raw_feature_value")),
            normalized_feature_value=_optional_float(row.get("normalized_feature_value")),
            feature_normalization_version_id=_optional_str(
                row.get("feature_normalization_version_id")
            ),
            feature_input_hash=_optional_str(row.get("feature_input_hash")),
            generated_at=generated_at,
        )

    @staticmethod
    def _row_to_item_meaning(row: dict[str, object]) -> ItemMeaningRow:
        return ItemMeaningRow(
            item_id=str(row["item_id"]),
            semantic_config_version_id=str(row["semantic_config_version_id"]),
            item_social=float(row["item_social"]),
            item_symbolic=float(row["item_symbolic"]),
            feature_normalization_version_id=_optional_str(
                row.get("feature_normalization_version_id")
            ),
        )

    @staticmethod
    def _row_to_item_embedding(row: dict[str, object]) -> ItemEmbeddingRow:
        return ItemEmbeddingRow(
            item_id=str(row["item_id"]),
            model_version_id=str(row["model_version_id"]),
            embedding_input_hash=str(row["embedding_input_hash"]),
        )
