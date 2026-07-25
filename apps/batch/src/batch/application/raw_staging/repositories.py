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
    StagingItemImageRow,
    StagingItemRow,
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
    staging_ranking: list[dict[str, object]] = field(default_factory=list)
    staging_genre: list[dict[str, object]] = field(default_factory=list)
    # boundary probes — must stay empty under correct job behavior
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_product_diff_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    written_external_genre_rows: list[dict[str, object]] = field(default_factory=list)
    object_storage_put_count: int = 0
    object_storage_delete_count: int = 0
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)

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
            "diff_status": None,  # BATCH-005: always NULL
            "staged_at": staged_at,
        }
        self.staging_items[key] = record
        self.db_writer.write_rows("staging_item", (dict(record),))
        return record

    def upsert_staging_item_images(
        self,
        *,
        raw_metadata_id: str,
        external_item_code: str,
        images: tuple[StagingItemImageRow, ...],
    ) -> tuple[int, int]:
        """Upsert images then sync-delete URLs not in the current set (§5.8)."""

        url_set = {img.image_url for img in images}
        upserted = 0
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
            self.db_writer.write_rows("staging_item_image", (dict(record),))
            upserted += 1

        deleted = 0
        to_delete = [
            key
            for key in list(self.staging_item_images)
            if key[0] == raw_metadata_id
            and key[1] == external_item_code
            and key[2] not in url_set
        ]
        for key in to_delete:
            del self.staging_item_images[key]
            deleted += 1
            self.db_writer.write_rows(
                "staging_item_image_delete",
                (
                    {
                        "raw_metadata_id": raw_metadata_id,
                        "external_item_code": external_item_code,
                        "image_url": key[2],
                    },
                ),
            )
        return upserted, deleted

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

    def mark_staged(self, *, raw_metadata_id: str, staged_at: datetime | None = None) -> None:
        meta = self.raw_metadata.get(raw_metadata_id)
        if meta is None:
            return
        now = staged_at or datetime.now(UTC)
        meta["import_status"] = "staged"
        meta["staged_at"] = now
        self.db_writer.write_rows(
            "raw_product_metadata",
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "import_status": "staged",
                    "staged_at": now,
                },
            ),
        )

    def mark_failed(self, *, raw_metadata_id: str, error_code: str) -> None:
        meta = self.raw_metadata.get(raw_metadata_id)
        if meta is None:
            return
        meta["import_status"] = "failed"
        meta["error_code"] = error_code
        self.db_writer.write_rows(
            "raw_product_metadata",
            (
                {
                    "raw_metadata_id": raw_metadata_id,
                    "import_status": "failed",
                    "error_code": error_code,
                },
            ),
        )

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        raw_metadata_id: str | None = None,
    ) -> None:
        self.error_logs.append(
            {"code": code, "summary": summary, "raw_metadata_id": raw_metadata_id}
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})
