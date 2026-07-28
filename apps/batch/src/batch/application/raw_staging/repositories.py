"""Repositories for BATCH-005 Raw selection / GET / Staging upsert.

``list_eligible_raws`` uses ``DbReader`` when injected (Wave A SELECT wiring).
Without a reader, in-memory ``seed_raws`` remains for scaffold / UT.

Forbidden writes (must remain empty in result checks):
item / product_diff_result / item.active_status / external_genre
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.raw_staging.hashing import content_hash_for_bytes
from batch.application.raw_staging.models import (
    ItemTransformBundle,
    RawMetadataSeed,
    StagingGenreRow,
    StagingItemImageRow,
    StagingItemRow,
    StagingRankingSignalRow,
)
from batch.infrastructure.db import DbReader, DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient, ObjectStorageError

DEFAULT_SOURCE_API = "item_search"
SKIP_STATUSES = frozenset({"staged", "imported"})
FORCE_STATUSES = ("raw_saved", "failed", "staged", "imported")
_READ_COLUMNS = (
    "raw_metadata_id",
    "object_key",
    "content_hash",
    "source",
    "source_api",
    "import_status",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class RawStagingRepositories:
    """Facade: Raw selection / GET / Staging upsert / metadata status / logs."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    db_reader: DbReader | None = None
    seed_raws: list[RawMetadataSeed] = field(default_factory=list)
    # mutable metadata store keyed by raw_metadata_id
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_items: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    staging_item_images: dict[tuple[str, str, str], dict[str, object]] = field(
        default_factory=dict
    )
    staging_ranking: dict[tuple[str, int], dict[str, object]] = field(default_factory=dict)
    staging_genre: dict[tuple[str, int], dict[str, object]] = field(default_factory=dict)
    # boundary probes — must stay empty under correct job behavior
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_product_diff_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    written_external_genre_rows: list[dict[str, object]] = field(default_factory=list)
    object_storage_put_count: int = 0
    object_storage_delete_count: int = 0
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
        for seed in self.seed_raws:
            if seed.raw_metadata_id not in self.raw_metadata:
                self.raw_metadata[seed.raw_metadata_id] = {
                    "raw_metadata_id": seed.raw_metadata_id,
                    "object_key": seed.object_key,
                    "content_hash": seed.content_hash,
                    "source": seed.source,
                    "source_api": seed.source_api,
                    "import_status": seed.import_status,
                    "batch_run_id": seed.batch_run_id,
                    "bucket": seed.bucket or self.bucket,
                    "staged_at": None,
                }

    def list_eligible_raws(
        self,
        *,
        max_raw: int,
        source_apis: tuple[str, ...] | None = None,
        raw_metadata_ids: tuple[str, ...] | None = None,
        force: bool = False,
    ) -> list[RawMetadataSeed]:
        """§18.1 No.2: default import_status=raw_saved, item_search preferred."""

        if self.db_reader is not None:
            return self._list_eligible_raws_from_db(
                max_raw=max_raw,
                source_apis=source_apis,
                raw_metadata_ids=raw_metadata_ids,
                force=force,
            )

        preferred = source_apis or (DEFAULT_SOURCE_API,)
        preferred_set = set(preferred)

        if raw_metadata_ids:
            selected: list[RawMetadataSeed] = []
            for raw_id in raw_metadata_ids:
                meta = self.raw_metadata.get(raw_id)
                if meta is None:
                    continue
                seed = self._meta_to_seed(meta)
                if not force and seed.import_status in SKIP_STATUSES:
                    continue
                selected.append(seed)
                if len(selected) >= max_raw:
                    break
            return selected

        eligible: list[RawMetadataSeed] = []
        for meta in self.raw_metadata.values():
            seed = self._meta_to_seed(meta)
            if seed.source_api not in preferred_set:
                continue
            if force:
                if seed.import_status not in set(FORCE_STATUSES):
                    continue
            else:
                if seed.import_status != "raw_saved":
                    continue
            eligible.append(seed)

        eligible.sort(key=self._prefer_sort_key)
        return eligible[: max(0, max_raw)]

    def _list_eligible_raws_from_db(
        self,
        *,
        max_raw: int,
        source_apis: tuple[str, ...] | None,
        raw_metadata_ids: tuple[str, ...] | None,
        force: bool,
    ) -> list[RawMetadataSeed]:
        """SELECT via DbReader (equals-only; no arbitrary SQL)."""

        reader = self.db_reader
        if reader is None:
            return []

        if raw_metadata_ids:
            selected: list[RawMetadataSeed] = []
            for raw_id in raw_metadata_ids:
                result = reader.fetch_rows(
                    "raw_product_metadata",
                    columns=_READ_COLUMNS,
                    equals=(("raw_metadata_id", raw_id),),
                    limit=1,
                )
                if not result.rows:
                    continue
                seed = self._row_to_seed(result.rows[0])
                if not force and seed.import_status in SKIP_STATUSES:
                    continue
                self._cache_seed(seed)
                selected.append(seed)
                if len(selected) >= max_raw:
                    break
            return selected

        preferred = source_apis or (DEFAULT_SOURCE_API,)
        statuses = FORCE_STATUSES if force else ("raw_saved",)
        collected: dict[str, RawMetadataSeed] = {}
        fetch_limit = max(0, max_raw)
        if fetch_limit == 0:
            return []

        for status in statuses:
            for api in preferred:
                result = reader.fetch_rows(
                    "raw_product_metadata",
                    columns=_READ_COLUMNS,
                    equals=(("import_status", status), ("source_api", api)),
                    order_by=("raw_metadata_id",),
                    limit=fetch_limit,
                )
                for row in result.rows:
                    seed = self._row_to_seed(row)
                    if seed.raw_metadata_id in collected:
                        continue
                    self._cache_seed(seed)
                    collected[seed.raw_metadata_id] = seed

        eligible = list(collected.values())
        eligible.sort(key=self._prefer_sort_key)
        return eligible[:fetch_limit]

    @staticmethod
    def _prefer_sort_key(seed: RawMetadataSeed) -> tuple[int, str]:
        prefer_rank = 0 if seed.source_api == DEFAULT_SOURCE_API else 1
        return (prefer_rank, seed.raw_metadata_id)

    def _row_to_seed(self, row: dict[str, object]) -> RawMetadataSeed:
        return RawMetadataSeed(
            raw_metadata_id=str(row["raw_metadata_id"]),
            object_key=str(row["object_key"]),
            content_hash=str(row["content_hash"]),
            source=str(row.get("source") or "rakuten"),
            source_api=str(row.get("source_api") or DEFAULT_SOURCE_API),
            import_status=str(row.get("import_status") or "raw_saved"),
            batch_run_id=None,
            bucket=self.bucket,
        )

    def _cache_seed(self, seed: RawMetadataSeed) -> None:
        self.raw_metadata[seed.raw_metadata_id] = {
            "raw_metadata_id": seed.raw_metadata_id,
            "object_key": seed.object_key,
            "content_hash": seed.content_hash,
            "source": seed.source,
            "source_api": seed.source_api,
            "import_status": seed.import_status,
            "batch_run_id": seed.batch_run_id,
            "bucket": seed.bucket or self.bucket,
            "staged_at": None,
        }

    def _meta_to_seed(self, meta: dict[str, object]) -> RawMetadataSeed:
        return RawMetadataSeed(
            raw_metadata_id=str(meta["raw_metadata_id"]),
            object_key=str(meta["object_key"]),
            content_hash=str(meta["content_hash"]),
            source=str(meta.get("source") or "rakuten"),
            source_api=str(meta.get("source_api") or DEFAULT_SOURCE_API),
            import_status=str(meta.get("import_status") or "raw_saved"),
            batch_run_id=str(meta["batch_run_id"]) if meta.get("batch_run_id") else None,
            bucket=str(meta["bucket"]) if meta.get("bucket") else self.bucket,
        )

    def read_raw_body(self, *, meta: RawMetadataSeed) -> bytes:
        """GET Raw Object and verify content_hash. Never put/delete."""

        if not meta.object_key:
            raise ObjectStorageError(code="GRS-RAW-003", message="object_key missing")

        bucket = meta.bucket or self.bucket
        ref = ObjectRef(bucket=bucket, key=meta.object_key)
        try:
            stored = self.object_storage.get_object(ref)
        except ObjectStorageError:
            raise
        except Exception as exc:  # noqa: BLE001 — map unexpected GET failure
            raise ObjectStorageError(code="GRS-RAW-004", message=str(exc)) from exc

        if stored is None:
            raise ObjectStorageError(code="GRS-RAW-003", message="raw object not found")

        actual_hash = content_hash_for_bytes(stored.body)
        if actual_hash != meta.content_hash:
            raise ObjectStorageError(
                code="GRS-RAW-005",
                message="content_hash mismatch",
            )
        return stored.body

    def upsert_staging_item(self, row: StagingItemRow) -> dict[str, object]:
        key = (row.raw_metadata_id, row.external_item_code)
        existing = self.staging_items.get(key)
        # scaffold / UT: keep stable in-memory id. Postgres PK uses gen_random_uuid().
        staging_id = (
            str(existing["staging_item_id"])
            if existing and existing.get("staging_item_id")
            else f"si_{uuid.uuid4().hex[:12]}"
        )
        staged_at = row.staged_at or datetime.now(UTC)
        record: dict[str, object] = {
            "staging_item_id": staging_id,
            "raw_metadata_id": row.raw_metadata_id,
            "source": row.source,
            "external_item_code": row.external_item_code,
            "item_name": row.item_name,
            "item_caption": row.item_caption,
            "catchcopy": row.catchcopy,
            "price": row.price,
            "item_url": row.item_url,
            "external_genre_id": row.external_genre_id,
            "shop_code": row.shop_code,
            "availability": row.availability,
            "review_average": row.review_average,
            "review_count": row.review_count,
            "normalized_hash": row.normalized_hash,
            "diff_status": None,  # BATCH-005: always NULL on insert/update
            "staged_at": staged_at,
        }
        self.staging_items[key] = record
        # Omit staging_item_id from upsert payload: DB default on insert; never overwrite PK.
        persist_row = {
            "raw_metadata_id": row.raw_metadata_id,
            "source": row.source,
            "external_item_code": row.external_item_code,
            "item_name": row.item_name,
            "item_caption": row.item_caption,
            "catchcopy": row.catchcopy,
            "price": row.price,
            "item_url": row.item_url,
            "external_genre_id": row.external_genre_id,
            "shop_code": row.shop_code,
            "availability": row.availability,
            "review_average": row.review_average,
            "review_count": row.review_count,
            "normalized_hash": row.normalized_hash,
            "diff_status": None,
            "staged_at": staged_at,
        }
        self.db_writer.upsert_rows(
            "staging_item",
            (persist_row,),
            conflict_columns=("raw_metadata_id", "external_item_code"),
            update_columns=(
                "source",
                "item_name",
                "item_caption",
                "catchcopy",
                "price",
                "item_url",
                "external_genre_id",
                "shop_code",
                "availability",
                "review_average",
                "review_count",
                "normalized_hash",
                "diff_status",
                "staged_at",
            ),
        )
        return record

    def upsert_staging_item_images(
        self,
        *,
        raw_metadata_id: str,
        external_item_code: str,
        images: tuple[StagingItemImageRow, ...],
    ) -> tuple[int, int]:
        """Upsert images then sync-delete URLs not in the current set (§5.8).

        Sync-delete strategy:
        - ``db_reader`` あり: equals で既存 URL を取得し、集合外を ``delete_rows``
        - なし（scaffold/UT）: in-memory 集合と照合し、実テーブル名で ``delete_rows``
        """

        url_set = {img.image_url for img in images}
        persist_rows: list[dict[str, object]] = []
        for img in images:
            key = (img.raw_metadata_id, img.external_item_code, img.image_url)
            existing = self.staging_item_images.get(key)
            image_id = (
                str(existing["staging_item_image_id"])
                if existing and existing.get("staging_item_image_id")
                else f"sii_{uuid.uuid4().hex[:12]}"
            )
            staged_at = img.staged_at or datetime.now(UTC)
            record: dict[str, object] = {
                "staging_item_image_id": image_id,
                "raw_metadata_id": img.raw_metadata_id,
                "external_item_code": img.external_item_code,
                "image_url": img.image_url,
                "image_size_type": img.image_size_type,
                "display_order": img.display_order,
                "is_primary_candidate": img.is_primary_candidate,
                "staged_at": staged_at,
            }
            self.staging_item_images[key] = record
            persist_rows.append(
                {
                    "raw_metadata_id": img.raw_metadata_id,
                    "external_item_code": img.external_item_code,
                    "image_url": img.image_url,
                    "image_size_type": img.image_size_type,
                    "display_order": img.display_order,
                    "is_primary_candidate": img.is_primary_candidate,
                    "staged_at": staged_at,
                }
            )

        upserted = len(persist_rows)
        if persist_rows:
            self.db_writer.upsert_rows(
                "staging_item_image",
                tuple(persist_rows),
                conflict_columns=("raw_metadata_id", "external_item_code", "image_url"),
                update_columns=(
                    "image_size_type",
                    "display_order",
                    "is_primary_candidate",
                    "staged_at",
                ),
            )

        deleted = self._sync_delete_staging_item_images(
            raw_metadata_id=raw_metadata_id,
            external_item_code=external_item_code,
            url_set=url_set,
        )
        return upserted, deleted

    def _sync_delete_staging_item_images(
        self,
        *,
        raw_metadata_id: str,
        external_item_code: str,
        url_set: set[str],
    ) -> int:
        """Delete staging_item_image rows outside the current URL set."""

        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "staging_item_image",
                columns=("image_url",),
                equals=(
                    ("raw_metadata_id", raw_metadata_id),
                    ("external_item_code", external_item_code),
                ),
            )
            existing_urls = {str(row["image_url"]) for row in result.rows}
        else:
            existing_urls = {
                key[2]
                for key in self.staging_item_images
                if key[0] == raw_metadata_id and key[1] == external_item_code
            }

        deleted = 0
        for image_url in sorted(existing_urls - url_set):
            self.db_writer.delete_rows(
                "staging_item_image",
                equals=(
                    ("raw_metadata_id", raw_metadata_id),
                    ("external_item_code", external_item_code),
                    ("image_url", image_url),
                ),
            )
            deleted += 1

        # Keep scaffold/UT in-memory cache aligned with the current URL set.
        for key in list(self.staging_item_images):
            if (
                key[0] == raw_metadata_id
                and key[1] == external_item_code
                and key[2] not in url_set
            ):
                del self.staging_item_images[key]
        return deleted

    def persist_item_bundles(self, bundles: tuple[ItemTransformBundle, ...]) -> tuple[int, int]:
        item_count = 0
        image_count = 0
        for bundle in bundles:
            self.upsert_staging_item(bundle.item)
            item_count += 1
            up, _ = self.upsert_staging_item_images(
                raw_metadata_id=bundle.item.raw_metadata_id,
                external_item_code=bundle.item.external_item_code,
                images=bundle.images,
            )
            image_count += up
        return item_count, image_count

    def upsert_staging_ranking_signal(self, row: StagingRankingSignalRow) -> dict[str, object]:
        key = (row.raw_metadata_id, row.rank)
        existing = self.staging_ranking.get(key)
        # scaffold / UT: keep stable in-memory id. Postgres PK uses gen_random_uuid().
        staging_id = (
            str(existing["staging_ranking_signal_id"])
            if existing and existing.get("staging_ranking_signal_id")
            else f"srs_{uuid.uuid4().hex[:12]}"
        )
        staged_at = row.staged_at or datetime.now(UTC)
        record: dict[str, object] = {
            "staging_ranking_signal_id": staging_id,
            "raw_metadata_id": row.raw_metadata_id,
            "external_item_code": row.external_item_code,
            "external_genre_id": row.external_genre_id,
            "rank": row.rank,
            "period": row.period,
            "last_build_date": row.last_build_date,
            "staged_at": staged_at,
        }
        self.staging_ranking[key] = record
        # Omit PK from upsert payload: DB default on insert; never overwrite PK.
        persist_row = {
            "raw_metadata_id": row.raw_metadata_id,
            "external_item_code": row.external_item_code,
            "external_genre_id": row.external_genre_id,
            "rank": row.rank,
            "period": row.period,
            "last_build_date": row.last_build_date,
            "staged_at": staged_at,
        }
        self.db_writer.upsert_rows(
            "staging_ranking_signal",
            (persist_row,),
            conflict_columns=("raw_metadata_id", "rank"),
            update_columns=(
                "external_item_code",
                "external_genre_id",
                "period",
                "last_build_date",
                "staged_at",
            ),
        )
        return record

    def upsert_staging_genre(self, row: StagingGenreRow) -> dict[str, object]:
        key = (row.raw_metadata_id, row.external_genre_id)
        existing = self.staging_genre.get(key)
        staging_id = (
            str(existing["staging_genre_id"])
            if existing and existing.get("staging_genre_id")
            else f"sg_{uuid.uuid4().hex[:12]}"
        )
        staged_at = row.staged_at or datetime.now(UTC)
        record: dict[str, object] = {
            "staging_genre_id": staging_id,
            "raw_metadata_id": row.raw_metadata_id,
            "source": row.source,
            "external_genre_id": row.external_genre_id,
            "genre_name": row.genre_name,
            "parent_external_genre_id": row.parent_external_genre_id,
            "genre_level": row.genre_level,
            "is_leaf": row.is_leaf,
            "staged_at": staged_at,
        }
        self.staging_genre[key] = record
        persist_row = {
            "raw_metadata_id": row.raw_metadata_id,
            "source": row.source,
            "external_genre_id": row.external_genre_id,
            "genre_name": row.genre_name,
            "parent_external_genre_id": row.parent_external_genre_id,
            "genre_level": row.genre_level,
            "is_leaf": row.is_leaf,
            "staged_at": staged_at,
        }
        self.db_writer.upsert_rows(
            "staging_genre",
            (persist_row,),
            conflict_columns=("raw_metadata_id", "external_genre_id"),
            update_columns=(
                "source",
                "genre_name",
                "parent_external_genre_id",
                "genre_level",
                "is_leaf",
                "staged_at",
            ),
        )
        return record

    def persist_ranking_rows(self, rows: tuple[StagingRankingSignalRow, ...]) -> int:
        count = 0
        for row in rows:
            self.upsert_staging_ranking_signal(row)
            count += 1
        return count

    def persist_genre_rows(self, rows: tuple[StagingGenreRow, ...]) -> int:
        count = 0
        for row in rows:
            self.upsert_staging_genre(row)
            count += 1
        return count

    def mark_staged(self, *, raw_metadata_id: str, staged_at: datetime | None = None) -> None:
        meta = self.raw_metadata.get(raw_metadata_id)
        if meta is None:
            return
        now = staged_at or datetime.now(UTC)
        meta["import_status"] = "staged"
        meta["staged_at"] = now
        self.db_writer.update_rows(
            "raw_product_metadata",
            set_values={"import_status": "staged", "staged_at": now},
            equals=(("raw_metadata_id", raw_metadata_id),),
        )

    def mark_failed(self, *, raw_metadata_id: str, error_code: str) -> None:
        meta = self.raw_metadata.get(raw_metadata_id)
        if meta is None:
            return
        # CHECK: import_status=failed requires error_message IS NOT NULL（secret なし短文）
        error_message = f"staging failed: {error_code}"
        meta["import_status"] = "failed"
        meta["error_code"] = error_code
        meta["error_message"] = error_message
        self.db_writer.update_rows(
            "raw_product_metadata",
            set_values={
                "import_status": "failed",
                "error_code": error_code,
                "error_message": error_message,
            },
            equals=(("raw_metadata_id", raw_metadata_id),),
        )

    def record_error(self, *, code: str, summary: str, raw_metadata_id: str | None = None) -> None:
        detail: dict[str, object] = {}
        if raw_metadata_id is not None:
            detail["raw_metadata_id"] = raw_metadata_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"raw_metadata_id": raw_metadata_id},
            detail=detail or None,
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
