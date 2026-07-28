"""Repositories for BATCH-015 Item Embedding生成.

``list_target_queues`` / ``load_item`` / ``load_hash_handoff`` / skip 用
``item_embedding`` SELECT は ``DbReader`` 経由（Wave F）。

queue OR（embedding∈{queued,processing} OR semantic|feature+processing）は
equals 複数 fetch + in-process。

書込本配線（#1635 Wave 3 / #1690）:

- ``claim_or_continue``: embedding+queued → ``update_rows``（条件付き）。
  processing 継続は DB no-op
- ``update_queue_status``: 終端 → ``update_rows``（偽 ``op`` 廃止）
- ``upsert_item_embedding``（IF-VEC-BATCH-001）: ``upsert_rows`` + pgvector literal

制約:

- item READ ONLY
- BATCH-014 handoff READ ONLY（IF-DB-BATCH-015 消費・再算出禁止）
- Queue UPDATE only（INSERT 禁止）
- IF-DB-BATCH-016 分布メトリクス非書込
- ログ・例外に embedding_vector 全文を出さない（次元のみ可）
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from batch.application.item_embedding.models import (
    EmbeddingHashHandoff,
    ItemEmbeddingUpsertRow,
    ItemRow,
    QueueRow,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"
# MVP scaffold 既定の現行 Embedding model version（MOD-RECO-003 stub）
DEFAULT_EMBEDDING_MODEL_VERSION = "scaffold-embedding-model-v1"
# 入力構築ルール version（DB 物理列なし。context 内または既定）
DEFAULT_EMBEDDING_SOURCE_VERSION = "scaffold-embedding-source-v1"

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
_HANDOFF_COLUMNS = (
    "item_id",
    "model_version_id",
    "embedding_source_type",
    "embedding_input_hash",
    "item_text_context",
    "item_generation_queue_id",
    "computed_at",
)
_EMBEDDING_COLUMNS = (
    "item_id",
    "model_version_id",
    "embedding_input_hash",
    "embedding_vector",
    "embedding_source_type",
)


def _vector_literal(values: tuple[float, ...] | list[float]) -> str:
    """pgvector テキスト入力形式 ``[v1,v2,...]``（``scripts/perf/pgvector_search_bench.py`` と同型）。"""

    return "[" + ",".join(f"{float(v):.8f}" for v in values) + "]"


from batch.application.observability import (
    ApiCallLogWriter,
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_api_call, emit_error, emit_phase

# api_call_log: Embedding 呼出監査（Wave 5 / #1710）
_DDL_SOURCE_OPENAI = "openai"
_DDL_SOURCE_API_ITEM_EMBEDDING = "item_embedding"
# EmbeddingGenStatus → api_call_status
_GEN_STATUS_TO_CALL_STATUS: dict[str, str] = {
    "generated": "succeeded",
    "skipped": "skipped",
    "failed": "failed",
}

@dataclass(frozen=True)
class ExistingEmbedding:
    """skip 判定用の既存 item_embedding 行.

    冪等キー: item_id + model_version_id + embedding_input_hash。
    """

    model_version_id: str
    embedding_input_hash: str
    has_vector: bool = True
    embedding_source_type: str = "item_text_context"


@dataclass
class ItemEmbeddingRepositories:
    """Facade: Queue / handoff / item_embedding Upsert / logs（MOD-BATCH-037）."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_queues: list[QueueRow] = field(default_factory=list)
    seed_items: list[ItemRow] = field(default_factory=list)
    seed_handoffs: list[EmbeddingHashHandoff] = field(default_factory=list)
    seed_embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)

    queues: dict[str, dict[str, object]] = field(default_factory=dict)
    items: dict[str, dict[str, object]] = field(default_factory=dict)
    handoffs: dict[str, EmbeddingHashHandoff] = field(default_factory=dict)
    embeddings: dict[str, list[ExistingEmbedding]] = field(default_factory=dict)
    embedding_rows: dict[tuple[str, str, str], dict[str, object]] = field(default_factory=dict)

    item_embedding_write_count: int = 0
    item_write_count: int = 0
    queue_insert_count: int = 0
    hash_recompute_count: int = 0
    distribution_metric_write_count: int = 0
    upsert_rows: list[ItemEmbeddingUpsertRow] = field(default_factory=list)
    api_call_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)
    phase_log_writer: PhaseLogWriter | None = None
    error_log_writer: ErrorLogWriter | None = None
    api_call_log_writer: ApiCallLogWriter | None = None
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
        for handoff in self.seed_handoffs:
            # key: item_id（同一 item の最新 handoff を消費）
            self.handoffs[handoff.item_id] = handoff
        for key, rows in self.seed_embeddings.items():
            self.embeddings[key] = list(rows)
            for row in rows:
                if row.has_vector:
                    self.embedding_rows[
                        (key, row.model_version_id, row.embedding_input_hash)
                    ] = {
                        "item_id": key,
                        "model_version_id": row.model_version_id,
                        "embedding_input_hash": row.embedding_input_hash,
                        "embedding_source_type": row.embedding_source_type,
                        "has_vector": True,
                    }

    def list_target_queues(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        queue_batch_size: int | None = None,
        item_ids: tuple[str, ...] | None = None,
        queue_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[QueueRow], int]:
        """§9.1: embedding+queued/processing / semantic·feature+processing 継続."""

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

            is_embedding = q.generation_type == "embedding" and q.queue_status in {
                "queued",
                "processing",
            }
            is_continuation = (
                q.generation_type in {"semantic", "feature"} and q.queue_status == "processing"
            )
            if not (is_embedding or is_continuation):
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

        if queue_ids:
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
            # Cap over-fetch like BATCH-014
            fetch_limit = min(max(fetch_cap * 5, fetch_cap), 5000)
            filter_specs: tuple[tuple[tuple[str, object], ...], ...] = (
                (("generation_type", "embedding"), ("queue_status", "queued")),
                (("generation_type", "embedding"), ("queue_status", "processing")),
                (("generation_type", "semantic"), ("queue_status", "processing")),
                (("generation_type", "feature"), ("queue_status", "processing")),
            )
            for equals in filter_specs:
                result = reader.fetch_rows(
                    "item_generation_queue",
                    columns=_QUEUE_COLUMNS,
                    equals=equals,
                    order_by=("item_generation_queue_id",),
                    limit=fetch_limit,
                )
                candidate_rows.extend(result.rows)

        targets: list[QueueRow] = []
        non_target = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["item_generation_queue_id"])):
            q = self._cache_queue_row(row)
            if q.item_generation_queue_id in seen_ids:
                continue
            seen_ids.add(q.item_generation_queue_id)

            is_embedding = q.generation_type == "embedding" and q.queue_status in {
                "queued",
                "processing",
            }
            is_continuation = (
                q.generation_type in {"semantic", "feature"} and q.queue_status == "processing"
            )
            if not (is_embedding or is_continuation):
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
        """embedding claim（条件付き UPDATE）/ processing 継続（DB no-op）。"""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            return None
        status = row.get("queue_status")
        gen = row.get("generation_type")
        ts = started_at or datetime.now(UTC)

        if gen == "embedding" and status == "queued":
            result = self.db_writer.update_rows(
                "item_generation_queue",
                set_values={"queue_status": "processing", "started_at": ts},
                equals=(
                    ("item_generation_queue_id", item_generation_queue_id),
                    ("queue_status", "queued"),
                    ("generation_type", "embedding"),
                ),
            )
            if result.rows_affected == 0:
                return None
            row["queue_status"] = "processing"
            row["started_at"] = ts
            return self._row_to_queue(row)

        if status == "processing" and gen in {"embedding", "semantic", "feature"}:
            # 既に processing。追加 UPDATE 不要（偽 op=continue_processing 廃止）。
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

    def load_hash_handoff(
        self,
        *,
        item_id: str,
        model_version_id: str | None = None,
    ) -> EmbeddingHashHandoff | None:
        """IF-DB-BATCH-015 消費: BATCH-014 handoff を読取（再算出しない）."""

        cached = self.handoffs.get(item_id)
        if cached is not None and (
            model_version_id is None or cached.model_version_id == model_version_id
        ):
            return cached

        if self.db_reader is None:
            return None

        equals: list[tuple[str, object]] = [("item_id", item_id)]
        if model_version_id is not None:
            equals.append(("model_version_id", model_version_id))
        result = self.db_reader.fetch_rows(
            "item_embedding_input",
            columns=_HANDOFF_COLUMNS,
            equals=tuple(equals),
            order_by=("computed_at",),
            limit=50,
        )
        if not result.rows:
            return None
        # computed_at ASC で取るため最新は末尾
        row = result.rows[-1]
        handoff = self._row_to_handoff(row)
        self.handoffs[item_id] = handoff
        return handoff

    def should_skip_embedding_generation(
        self,
        *,
        item_id: str,
        model_version_id: str,
        embedding_input_hash: str,
    ) -> bool:
        """§9.3: 同一 3 列キーの成功行あり → Embedding 生成 skip."""

        key = (item_id, model_version_id, embedding_input_hash)
        existing = self.embedding_rows.get(key)
        if existing is not None and existing.get("has_vector"):
            return True

        rows = self.embeddings.get(item_id)
        if rows is None and self.db_reader is not None:
            rows = self._fetch_and_cache_embeddings(item_id)
        if not rows:
            return False
        for row in rows:
            if row.model_version_id != model_version_id:
                continue
            if row.embedding_input_hash != embedding_input_hash:
                continue
            if not row.has_vector:
                continue
            return True
        return False

    def upsert_item_embedding(self, row: ItemEmbeddingUpsertRow) -> dict[str, object]:
        """IF-VEC-BATCH-001 Upsert（item_id + model_version_id + embedding_input_hash）。

        ``embedding_vector`` は Writer に pgvector テキスト形式で渡す。
        ``item_embedding_id`` は省略（DDL DEFAULT ``gen_random_uuid()``）。
        偽 ``op`` / ``has_vector`` / ``embedding_dimension`` は DB payload に含めない。
        """

        key = (row.item_id, row.model_version_id, row.embedding_input_hash)
        dimension = len(row.embedding_vector)
        # in-memory skip index（ログ経路には vector 全文を載せない）
        memory_payload: dict[str, object] = {
            "item_id": row.item_id,
            "model_version_id": row.model_version_id,
            "embedding_source_type": row.embedding_source_type,
            "embedding_input_hash": row.embedding_input_hash,
            "embedding_dimension": dimension,
            "has_vector": True,
            "generated_at": row.generated_at,
        }
        self.embedding_rows[key] = memory_payload
        self.embeddings.setdefault(row.item_id, [])
        # refresh skip index
        self.embeddings[row.item_id] = [
            e
            for e in self.embeddings[row.item_id]
            if not (
                e.model_version_id == row.model_version_id
                and e.embedding_input_hash == row.embedding_input_hash
            )
        ]
        self.embeddings[row.item_id].append(
            ExistingEmbedding(
                model_version_id=row.model_version_id,
                embedding_input_hash=row.embedding_input_hash,
                has_vector=True,
                embedding_source_type=row.embedding_source_type,
            )
        )
        self.upsert_rows.append(row)
        self.item_embedding_write_count += 1

        persist_row: dict[str, object] = {
            "item_id": row.item_id,
            "model_version_id": row.model_version_id,
            "embedding_source_type": row.embedding_source_type,
            "embedding_input_hash": row.embedding_input_hash,
            "embedding_vector": _vector_literal(row.embedding_vector),
            "generated_at": row.generated_at,
        }
        self.db_writer.upsert_rows(
            "item_embedding",
            (persist_row,),
            conflict_columns=("item_id", "model_version_id", "embedding_input_hash"),
            update_columns=("embedding_source_type", "embedding_vector", "generated_at"),
        )
        return memory_payload

    def update_queue_status(
        self,
        *,
        item_generation_queue_id: str,
        queue_status: str,
        completed_at: datetime | None = None,
        error_message: str | None = None,
    ) -> None:
        """Queue 終端更新（succeeded / skipped / failed）。keep_processing なし."""

        row = self._ensure_queue_hydrated(item_generation_queue_id)
        if row is None:
            raise KeyError(f"queue not found: {item_generation_queue_id}")
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

    def record_api_call(
        self,
        *,
        api_call_log_id: str,
        status: str,
        model: str,
        latency_ms: int | None,
        purpose: str = "item_embedding",
        error_code: str | None = None,
    ) -> None:
        """api_call_log メタのみ（secret / ベクトル全文 / 入力全文 / API key 禁止）.

        DB 書込時: ``source=openai`` / ``source_api=item_embedding``。
        ``source`` は API 提供者識別であり ``item.source``（マーケット）とは別概念。
        """

        call_status = _GEN_STATUS_TO_CALL_STATUS.get(status, status)
        emit_api_call(
            api_call_logs=self.api_call_logs,
            api_call_log_writer=self.api_call_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            api_call_log_id=api_call_log_id,
            source=_DDL_SOURCE_OPENAI,
            source_api=_DDL_SOURCE_API_ITEM_EMBEDDING,
            call_status=call_status,
            memory_entry={
                "api_call_log_id": api_call_log_id,
                "purpose": purpose,
                "status": status,
                "call_status": call_status,
                "model": model,
                "latency_ms": latency_ms,
                "error_code": error_code,
            },
            request_params_json={"model": model, "purpose": purpose},
            error_code=error_code,
            duration_ms=latency_ms,
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

    def _fetch_and_cache_embeddings(self, item_id: str) -> list[ExistingEmbedding]:
        reader = self.db_reader
        if reader is None:
            return []
        result = reader.fetch_rows(
            "item_embedding",
            columns=_EMBEDDING_COLUMNS,
            equals=(("item_id", item_id),),
            order_by=("model_version_id",),
            limit=50,
        )
        rows = [
            ExistingEmbedding(
                model_version_id=str(row.get("model_version_id") or ""),
                embedding_input_hash=str(row.get("embedding_input_hash") or ""),
                has_vector=row.get("embedding_vector") is not None,
                embedding_source_type=str(
                    row.get("embedding_source_type") or "item_text_context"
                ),
            )
            for row in result.rows
        ]
        self.embeddings[item_id] = rows
        for row in rows:
            if row.has_vector:
                self.embedding_rows[
                    (item_id, row.model_version_id, row.embedding_input_hash)
                ] = {
                    "item_id": item_id,
                    "model_version_id": row.model_version_id,
                    "embedding_input_hash": row.embedding_input_hash,
                    "embedding_source_type": row.embedding_source_type,
                    "has_vector": True,
                }
        return rows

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
    def _parse_item_text_context(raw: object) -> dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    @classmethod
    def _row_to_handoff(cls, row: dict[str, object]) -> EmbeddingHashHandoff:
        context = cls._parse_item_text_context(row.get("item_text_context"))
        source_version = ""
        if isinstance(context.get("embedding_source_version"), str):
            source_version = str(context["embedding_source_version"]).strip()
        if not source_version:
            source_version = DEFAULT_EMBEDDING_SOURCE_VERSION
        qid = row.get("item_generation_queue_id")
        return EmbeddingHashHandoff(
            item_id=str(row["item_id"]),
            item_generation_queue_id=str(qid) if qid is not None else "",
            model_version_id=str(row.get("model_version_id") or ""),
            embedding_source_type=str(row.get("embedding_source_type") or "item_text_context"),
            embedding_source_version=source_version,
            embedding_input_hash=str(row.get("embedding_input_hash") or ""),
            item_text_context=context,
        )

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
