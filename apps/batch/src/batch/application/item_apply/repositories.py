"""Repositories for BATCH-007 Item apply.

``list_eligible_diffs`` / ``load_*`` / ``resolve_item`` use ``DbReader`` when injected
(Wave C). Without a reader, in-memory ``seed_*`` remains for scaffold / UT.

Write path uses ``DbWriter.upsert_rows`` / ``update_rows`` / ``delete_rows``
(IF-DB-BATCH-007 Wave 1). ``active_status`` / ``is_active`` are never written here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from batch.application.item_apply.models import (
    PROCESSABLE_DIFF_STATUSES,
    DiffStatus,
    ItemSeed,
    ProductDiffResultSeed,
    StagingImageSeed,
    StagingItemSeed,
)
from batch.infrastructure.db import DbReader, DbWriter

DEFAULT_SOURCE = "rakuten"
DEFAULT_ACTIVE_STATUS = "active"
DEFAULT_IS_ACTIVE = True

_DIFF_COLUMNS = (
    "product_diff_result_id",
    "batch_run_id",
    "staging_item_id",
    "external_item_code",
    "old_hash",
    "new_hash",
    "diff_status",
    "judged_at",
)
_STAGING_COLUMNS = (
    "staging_item_id",
    "raw_metadata_id",
    "source",
    "external_item_code",
    "normalized_hash",
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
)
_STAGING_IMAGE_COLUMNS = (
    "raw_metadata_id",
    "external_item_code",
    "image_url",
    "image_size_type",
    "display_order",
    "is_primary_candidate",
)
_ITEM_COLUMNS = (
    "item_id",
    "source",
    "external_item_code",
    "normalized_hash",
    "item_name",
    "item_caption",
    "catchcopy",
    "price",
    "item_url",
    "external_genre_id",
    "shop_code",
    "active_status",
    "is_active",
    "first_fetched_at",
    "last_checked_at",
)
_ITEM_IMAGE_COLUMNS = ("image_url",)
_ITEM_UPSERT_UPDATE_COLUMNS = (
    "item_name",
    "item_caption",
    "catchcopy",
    "price",
    "item_url",
    "external_genre_id",
    "shop_code",
    "normalized_hash",
    "last_checked_at",
    "updated_at",
    # first_fetched_at / active_status / is_active / item_id は DO UPDATE 対象外（仕様 §10.1.1）
)
_ITEM_IMAGE_UPSERT_UPDATE_COLUMNS = (
    "image_size_type",
    "display_order",
    "is_primary",
    "fetched_at",
)
_ITEM_REVIEW_UPSERT_UPDATE_COLUMNS = (
    "review_average",
    "review_count",
    "fetched_at",
)


from batch.application.observability import (
    ErrorLogWriter,
    PhaseLogWriter,
)
from batch.application.observability.binding import emit_error, emit_phase

@dataclass
class ItemApplyRepositories:
    """Facade: Diff read / Staging read / Item Upsert / Image sync / Review Upsert / logs."""

    db_writer: DbWriter
    db_reader: DbReader | None = None
    seed_diffs: list[ProductDiffResultSeed] = field(default_factory=list)
    seed_staging: list[StagingItemSeed] = field(default_factory=list)
    seed_images: list[StagingImageSeed] = field(default_factory=list)
    seed_items: list[ItemSeed] = field(default_factory=list)
    product_diff_results: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_items: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_images: dict[str, list[dict[str, object]]] = field(default_factory=dict)
    items: dict[tuple[str, str], dict[str, object]] = field(default_factory=dict)
    item_images: dict[str, dict[str, dict[str, object]]] = field(default_factory=dict)
    item_reviews: dict[str, dict[str, object]] = field(default_factory=dict)
    # boundary probes
    written_item_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_image_rows: list[dict[str, object]] = field(default_factory=list)
    written_item_review_rows: list[dict[str, object]] = field(default_factory=list)
    written_active_status_rows: list[dict[str, object]] = field(default_factory=list)
    product_diff_write_count: int = 0
    hash_recalculate_calls: list[str] = field(default_factory=list)
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
        for seed in self.seed_diffs:
            if seed.product_diff_result_id not in self.product_diff_results:
                self.product_diff_results[seed.product_diff_result_id] = {
                    "product_diff_result_id": seed.product_diff_result_id,
                    "batch_run_id": seed.batch_run_id,
                    "staging_item_id": seed.staging_item_id,
                    "external_item_code": seed.external_item_code,
                    "diff_status": seed.diff_status,
                    "old_hash": seed.old_hash,
                    "new_hash": seed.new_hash,
                }
        for seed in self.seed_staging:
            if seed.staging_item_id not in self.staging_items:
                self.staging_items[seed.staging_item_id] = {
                    "staging_item_id": seed.staging_item_id,
                    "raw_metadata_id": None,
                    "source": seed.source,
                    "external_item_code": seed.external_item_code,
                    "normalized_hash": seed.normalized_hash,
                    "item_name": seed.item_name,
                    "item_caption": seed.item_caption,
                    "catchcopy": seed.catchcopy,
                    "price": seed.price,
                    "item_url": seed.item_url,
                    "external_genre_id": seed.external_genre_id,
                    "shop_code": seed.shop_code,
                    "availability": seed.availability,
                    "review_average": seed.review_average,
                    "review_count": seed.review_count,
                }
        for seed in self.seed_images:
            bucket = self.staging_images.setdefault(seed.staging_item_id, [])
            bucket.append(
                {
                    "staging_item_id": seed.staging_item_id,
                    "image_url": seed.image_url,
                    "image_size_type": seed.image_size_type,
                    "display_order": seed.display_order,
                    "is_primary_candidate": seed.is_primary_candidate,
                }
            )
        for seed in self.seed_items:
            key = (seed.source, seed.external_item_code)
            if key not in self.items:
                item_id = seed.item_id or f"it_{uuid.uuid4().hex[:12]}"
                self.items[key] = {
                    "item_id": item_id,
                    "source": seed.source,
                    "external_item_code": seed.external_item_code,
                    "normalized_hash": seed.normalized_hash,
                    "item_name": seed.item_name,
                    "item_caption": seed.item_caption,
                    "catchcopy": seed.catchcopy,
                    "price": seed.price,
                    "item_url": seed.item_url,
                    "external_genre_id": seed.external_genre_id,
                    "shop_code": seed.shop_code,
                    "active_status": seed.active_status
                    if seed.active_status is not None
                    else DEFAULT_ACTIVE_STATUS,
                    "is_active": DEFAULT_IS_ACTIVE if seed.is_active is None else seed.is_active,
                    "first_fetched_at": seed.first_fetched_at,
                    "last_checked_at": seed.last_checked_at,
                    "updated_at": None,
                }

    def list_eligible_diffs(
        self,
        *,
        max_items: int,
        source: str = DEFAULT_SOURCE,
        diff_batch_run_id: str | None = None,
        external_item_codes: tuple[str, ...] | None = None,
        staging_item_ids: tuple[str, ...] | None = None,
    ) -> tuple[list[ProductDiffResultSeed], int]:
        """§18.1 No.12: processable = new/updated/unchanged; unavailable counted separately."""

        if self.db_reader is not None:
            return self._list_eligible_diffs_from_db(
                max_items=max_items,
                source=source,
                diff_batch_run_id=diff_batch_run_id,
                external_item_codes=external_item_codes,
                staging_item_ids=staging_item_ids,
            )

        code_set = set(external_item_codes) if external_item_codes else None
        staging_id_set = set(staging_item_ids) if staging_item_ids else None
        processable: list[ProductDiffResultSeed] = []
        unavailable_count = 0

        rows = sorted(
            self.product_diff_results.values(),
            key=lambda r: str(r["product_diff_result_id"]),
        )
        for row in rows:
            seed = self._row_to_diff(row)
            if diff_batch_run_id and seed.batch_run_id != diff_batch_run_id:
                continue
            if code_set is not None and seed.external_item_code not in code_set:
                continue
            if staging_id_set is not None and seed.staging_item_id not in staging_id_set:
                continue
            staging = self.staging_items.get(seed.staging_item_id)
            if staging is None:
                continue
            if str(staging.get("source") or DEFAULT_SOURCE) != source:
                continue

            if seed.diff_status == "unavailable":
                unavailable_count += 1
                continue
            if seed.diff_status not in PROCESSABLE_DIFF_STATUSES:
                continue
            processable.append(seed)

        return processable[: max(0, max_items)], unavailable_count

    def _list_eligible_diffs_from_db(
        self,
        *,
        max_items: int,
        source: str,
        diff_batch_run_id: str | None,
        external_item_codes: tuple[str, ...] | None,
        staging_item_ids: tuple[str, ...] | None,
    ) -> tuple[list[ProductDiffResultSeed], int]:
        """SELECT via DbReader (equals-only; source / status filtered in-process)."""

        reader = self.db_reader
        if reader is None:
            return [], 0

        candidate_rows: list[dict[str, object]] = []

        if staging_item_ids:
            for sid in staging_item_ids:
                if not sid:
                    continue
                equals: list[tuple[str, object]] = [("staging_item_id", sid)]
                if diff_batch_run_id:
                    equals.append(("batch_run_id", diff_batch_run_id))
                result = reader.fetch_rows(
                    "product_diff_result",
                    columns=_DIFF_COLUMNS,
                    equals=tuple(equals),
                    order_by=("product_diff_result_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        elif external_item_codes:
            for code in external_item_codes:
                if not code:
                    continue
                equals = [("external_item_code", code)]
                if diff_batch_run_id:
                    equals.append(("batch_run_id", diff_batch_run_id))
                result = reader.fetch_rows(
                    "product_diff_result",
                    columns=_DIFF_COLUMNS,
                    equals=tuple(equals),
                    order_by=("product_diff_result_id",),
                    limit=100,
                )
                candidate_rows.extend(result.rows)
        else:
            fetch_cap = max(0, max_items)
            if fetch_cap == 0 and not diff_batch_run_id:
                return [], 0
            # Over-fetch then filter status/source in-process (no IN / JOIN).
            scan_target = max(fetch_cap, 1)
            fetch_limit = min(max(scan_target * 5, scan_target), 5000)
            equals_scan: tuple[tuple[str, object], ...] = ()
            if diff_batch_run_id:
                equals_scan = (("batch_run_id", diff_batch_run_id),)
            result = reader.fetch_rows(
                "product_diff_result",
                columns=_DIFF_COLUMNS,
                equals=equals_scan,
                order_by=("product_diff_result_id",),
                limit=fetch_limit,
            )
            candidate_rows.extend(result.rows)

        processable: list[ProductDiffResultSeed] = []
        unavailable_count = 0
        seen_ids: set[str] = set()

        for row in sorted(candidate_rows, key=lambda r: str(r["product_diff_result_id"])):
            seed = self._cache_diff_row(row)
            if seed.product_diff_result_id in seen_ids:
                continue
            seen_ids.add(seed.product_diff_result_id)

            staging = self._load_staging_row(seed.staging_item_id)
            if staging is None:
                continue
            if str(staging.get("source") or DEFAULT_SOURCE) != source:
                continue

            if seed.diff_status == "unavailable":
                unavailable_count += 1
                continue
            if seed.diff_status not in PROCESSABLE_DIFF_STATUSES:
                continue
            processable.append(seed)

        return processable[: max(0, max_items)], unavailable_count

    def load_diff(self, *, product_diff_result_id: str) -> ProductDiffResultSeed:
        row = self.product_diff_results.get(product_diff_result_id)
        if row is None and self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "product_diff_result",
                columns=_DIFF_COLUMNS,
                equals=(("product_diff_result_id", product_diff_result_id),),
                limit=1,
            )
            if result.rows:
                return self._cache_diff_row(result.rows[0])
        if row is None:
            raise KeyError(f"product_diff_result not found: {product_diff_result_id}")
        return self._row_to_diff(row)

    def load_staging(self, *, staging_item_id: str) -> StagingItemSeed:
        row = self.staging_items.get(staging_item_id)
        if row is None and self.db_reader is not None:
            row = self._load_staging_row(staging_item_id)
        if row is None:
            raise KeyError(f"staging_item not found: {staging_item_id}")
        return self._row_to_staging(row)

    def load_staging_images(self, *, staging_item_id: str) -> list[StagingImageSeed]:
        if self.db_reader is not None:
            staging = self.staging_items.get(staging_item_id) or self._load_staging_row(
                staging_item_id
            )
            if staging is None:
                return []
            raw_metadata_id = staging.get("raw_metadata_id")
            external_item_code = staging.get("external_item_code")
            if raw_metadata_id is None or external_item_code is None:
                return []
            result = self.db_reader.fetch_rows(
                "staging_item_image",
                columns=_STAGING_IMAGE_COLUMNS,
                equals=(
                    ("raw_metadata_id", raw_metadata_id),
                    ("external_item_code", str(external_item_code)),
                ),
                order_by=("display_order",),
                limit=500,
            )
            images = [
                StagingImageSeed(
                    staging_item_id=staging_item_id,
                    image_url=str(r["image_url"]),
                    image_size_type=(
                        str(r["image_size_type"]) if r.get("image_size_type") is not None else None
                    ),
                    display_order=int(r.get("display_order") or 0),
                    is_primary_candidate=bool(r.get("is_primary_candidate") or False),
                )
                for r in result.rows
            ]
            self.staging_images[staging_item_id] = [
                {
                    "staging_item_id": staging_item_id,
                    "image_url": img.image_url,
                    "image_size_type": img.image_size_type,
                    "display_order": img.display_order,
                    "is_primary_candidate": img.is_primary_candidate,
                }
                for img in images
            ]
            return images

        rows = self.staging_images.get(staging_item_id, [])
        return [
            StagingImageSeed(
                staging_item_id=str(r["staging_item_id"]),
                image_url=str(r["image_url"]),
                image_size_type=str(r["image_size_type"])
                if r.get("image_size_type") is not None
                else None,
                display_order=int(r.get("display_order") or 0),
                is_primary_candidate=bool(r.get("is_primary_candidate") or False),
            )
            for r in rows
        ]

    def resolve_item(self, *, source: str, external_item_code: str) -> ItemSeed | None:
        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item",
                columns=_ITEM_COLUMNS,
                equals=(("source", source), ("external_item_code", external_item_code)),
                limit=1,
            )
            if not result.rows:
                return None
            return self._cache_item_row(result.rows[0])

        row = self.items.get((source, external_item_code))
        if row is None:
            return None
        return self._row_to_item(row)

    def _ensure_item_hydrated(self, *, source: str, external_item_code: str) -> None:
        key = (source, external_item_code)
        if key in self.items:
            return
        if self.db_reader is None:
            return
        self.resolve_item(source=source, external_item_code=external_item_code)

    def upsert_item_from_staging(
        self,
        *,
        staging: StagingItemSeed,
        checked_at: datetime,
        is_new: bool,
    ) -> dict[str, object]:
        """new/updated: business columns + normalized_hash copy. No active_status/is_active update."""

        if staging.normalized_hash is None:
            raise ValueError("normalized_hash is required for new/updated upsert")

        key = (staging.source, staging.external_item_code)
        self._ensure_item_hydrated(
            source=staging.source, external_item_code=staging.external_item_code
        )
        existing = self.items.get(key)
        now = checked_at if checked_at.tzinfo else checked_at.replace(tzinfo=UTC)

        if existing is None:
            # Client UUID for INSERT; ON CONFLICT must not overwrite item_id.
            item_id = str(uuid.uuid4())
            record: dict[str, object] = {
                "item_id": item_id,
                "source": staging.source,
                "external_item_code": staging.external_item_code,
                "item_name": staging.item_name,
                "item_caption": staging.item_caption,
                "catchcopy": staging.catchcopy,
                "price": staging.price,
                "item_url": staging.item_url,
                "external_genre_id": staging.external_genre_id,
                "shop_code": staging.shop_code,
                "normalized_hash": staging.normalized_hash,
                "first_fetched_at": now,
                "last_checked_at": now,
                "updated_at": now,
                # DDL defaults only on INSERT — never derived from availability; not in writer payload
                "active_status": DEFAULT_ACTIVE_STATUS,
                "is_active": DEFAULT_IS_ACTIVE,
            }
            self.items[key] = record
        else:
            # Preserve active_status / is_active / first_fetched_at
            existing["item_name"] = staging.item_name
            existing["item_caption"] = staging.item_caption
            existing["catchcopy"] = staging.catchcopy
            existing["price"] = staging.price
            existing["item_url"] = staging.item_url
            existing["external_genre_id"] = staging.external_genre_id
            existing["shop_code"] = staging.shop_code
            existing["normalized_hash"] = staging.normalized_hash
            existing["last_checked_at"] = now
            existing["updated_at"] = now
            if is_new and existing.get("first_fetched_at") is None:
                existing["first_fetched_at"] = now
            record = existing

        # active_status / is_active omitted: INSERT relies on DB DEFAULT; UPDATE never SETs them.
        # first_fetched_at is in INSERT payload only (not in update_columns).
        persist_row = {
            "item_id": record["item_id"],
            "source": record["source"],
            "external_item_code": record["external_item_code"],
            "item_name": record["item_name"],
            "item_caption": record["item_caption"],
            "catchcopy": record["catchcopy"],
            "price": record["price"],
            "item_url": record["item_url"],
            "external_genre_id": record["external_genre_id"],
            "shop_code": record["shop_code"],
            "normalized_hash": record["normalized_hash"],
            "first_fetched_at": record["first_fetched_at"],
            "last_checked_at": record["last_checked_at"],
            "updated_at": record["updated_at"],
        }
        self.written_item_rows.append(dict(persist_row))
        self.db_writer.upsert_rows(
            "item",
            (dict(persist_row),),
            conflict_columns=("source", "external_item_code"),
            update_columns=_ITEM_UPSERT_UPDATE_COLUMNS,
        )
        return dict(record)

    def touch_item_last_checked(
        self,
        *,
        source: str,
        external_item_code: str,
        checked_at: datetime,
    ) -> dict[str, object]:
        """unchanged: last_checked_at (+ updated_at) only via update_rows (no partial upsert)."""

        key = (source, external_item_code)
        self._ensure_item_hydrated(source=source, external_item_code=external_item_code)
        row = self.items.get(key)
        if row is None:
            raise KeyError(f"item not found for unchanged touch: {source}/{external_item_code}")
        now = checked_at if checked_at.tzinfo else checked_at.replace(tzinfo=UTC)
        row["last_checked_at"] = now
        row["updated_at"] = now
        set_values = {
            "last_checked_at": now,
            "updated_at": now,
        }
        probe_row = {
            "item_id": row["item_id"],
            "source": source,
            "external_item_code": external_item_code,
            **set_values,
        }
        self.written_item_rows.append(dict(probe_row))
        self.db_writer.update_rows(
            "item",
            set_values=dict(set_values),
            equals=(("source", source), ("external_item_code", external_item_code)),
        )
        return dict(row)

    def sync_item_images(
        self,
        *,
        item_id: str,
        images: list[StagingImageSeed],
        fetched_at: datetime,
    ) -> list[dict[str, object]]:
        """Item 単位同期置換。空集合でも DELETE 可。UNIQUE (item_id, image_url)。"""

        now = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=UTC)
        desired_urls = {img.image_url for img in images}
        current = self.item_images.setdefault(item_id, {})

        # Determine single is_primary (first primary candidate, else first by display_order)
        primary_url: str | None = None
        ordered = sorted(images, key=lambda i: (i.display_order, i.image_url))
        for img in ordered:
            if img.is_primary_candidate:
                primary_url = img.image_url
                break
        if primary_url is None and ordered:
            primary_url = ordered[0].image_url

        by_url: dict[str, dict[str, object]] = {}
        for img in ordered:
            record: dict[str, object] = {
                "item_id": item_id,
                "image_url": img.image_url,
                "image_size_type": img.image_size_type,
                "display_order": img.display_order,
                "is_primary": img.image_url == primary_url,
                "fetched_at": now,
            }
            by_url[img.image_url] = record
            current[img.image_url] = dict(record)
            self.written_item_image_rows.append(dict(record))

        written = list(by_url.values())
        if written:
            self.db_writer.upsert_rows(
                "item_image",
                tuple(dict(r) for r in written),
                conflict_columns=("item_id", "image_url"),
                update_columns=_ITEM_IMAGE_UPSERT_UPDATE_COLUMNS,
            )

        self._sync_delete_item_images(item_id=item_id, url_set=desired_urls)
        return written

    def _sync_delete_item_images(self, *, item_id: str, url_set: set[str]) -> int:
        """Delete item_image rows outside the current URL set (005 staging と同型)."""

        if self.db_reader is not None:
            result = self.db_reader.fetch_rows(
                "item_image",
                columns=_ITEM_IMAGE_COLUMNS,
                equals=(("item_id", item_id),),
            )
            existing_urls = {str(row["image_url"]) for row in result.rows}
        else:
            existing_urls = set(self.item_images.get(item_id, {}).keys())

        deleted = 0
        for image_url in sorted(existing_urls - url_set):
            self.db_writer.delete_rows(
                "item_image",
                equals=(("item_id", item_id), ("image_url", image_url)),
            )
            deleted += 1

        current = self.item_images.setdefault(item_id, {})
        for url in list(current.keys()):
            if url not in url_set:
                del current[url]
        return deleted

    def upsert_item_review(
        self,
        *,
        item_id: str,
        review_average: float | None,
        review_count: int | None,
        fetched_at: datetime,
    ) -> dict[str, object] | None:
        """Both columns valid → Upsert. Missing → skip (no DELETE). UNIQUE item_id."""

        if review_average is None or review_count is None:
            return None
        now = fetched_at if fetched_at.tzinfo else fetched_at.replace(tzinfo=UTC)
        record = {
            "item_id": item_id,
            "review_average": float(review_average),
            "review_count": int(review_count),
            "fetched_at": now,
        }
        self.item_reviews[item_id] = dict(record)
        self.written_item_review_rows.append(dict(record))
        self.db_writer.upsert_rows(
            "item_review_summary",
            (dict(record),),
            conflict_columns=("item_id",),
            update_columns=_ITEM_REVIEW_UPSERT_UPDATE_COLUMNS,
        )
        return dict(record)

    def record_error(
        self,
        *,
        code: str,
        summary: str,
        external_item_code: str | None = None,
        staging_item_id: str | None = None,
    ) -> None:
        detail: dict[str, object] = {}
        if external_item_code is not None:
            detail["external_item_code"] = external_item_code
        if staging_item_id is not None:
            detail["staging_item_id"] = staging_item_id
        emit_error(
            error_logs=self.error_logs,
            error_log_writer=self.error_log_writer,
            batch_run_id=self._batch_run_id,
            trace_id=self._trace_id,
            code=code,
            summary=summary,
            memory_extra={"external_item_code": external_item_code, "staging_item_id": staging_item_id},
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

    def _cache_diff_row(self, row: dict[str, object]) -> ProductDiffResultSeed:
        seed = self._row_to_diff(row)
        self.product_diff_results[seed.product_diff_result_id] = {
            "product_diff_result_id": seed.product_diff_result_id,
            "batch_run_id": seed.batch_run_id,
            "staging_item_id": seed.staging_item_id,
            "external_item_code": seed.external_item_code,
            "diff_status": seed.diff_status,
            "old_hash": seed.old_hash,
            "new_hash": seed.new_hash,
            "judged_at": row.get("judged_at"),
        }
        return seed

    def _load_staging_row(self, staging_item_id: str) -> dict[str, object] | None:
        cached = self.staging_items.get(staging_item_id)
        if cached is not None:
            return cached
        if self.db_reader is None:
            return None
        result = self.db_reader.fetch_rows(
            "staging_item",
            columns=_STAGING_COLUMNS,
            equals=(("staging_item_id", staging_item_id),),
            limit=1,
        )
        if not result.rows:
            return None
        return self._cache_staging_row(result.rows[0])

    def _cache_staging_row(self, row: dict[str, object]) -> dict[str, object]:
        seed = self._row_to_staging(row)
        cached: dict[str, object] = {
            "staging_item_id": seed.staging_item_id,
            "raw_metadata_id": row.get("raw_metadata_id"),
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "normalized_hash": seed.normalized_hash,
            "item_name": seed.item_name,
            "item_caption": seed.item_caption,
            "catchcopy": seed.catchcopy,
            "price": seed.price,
            "item_url": seed.item_url,
            "external_genre_id": seed.external_genre_id,
            "shop_code": seed.shop_code,
            "availability": seed.availability,
            "review_average": seed.review_average,
            "review_count": seed.review_count,
        }
        self.staging_items[seed.staging_item_id] = cached
        return cached

    def _cache_item_row(self, row: dict[str, object]) -> ItemSeed:
        seed = self._row_to_item(row)
        key = (seed.source, seed.external_item_code)
        self.items[key] = {
            "item_id": seed.item_id or f"it_{uuid.uuid4().hex[:12]}",
            "source": seed.source,
            "external_item_code": seed.external_item_code,
            "normalized_hash": seed.normalized_hash,
            "item_name": seed.item_name,
            "item_caption": seed.item_caption,
            "catchcopy": seed.catchcopy,
            "price": seed.price,
            "item_url": seed.item_url,
            "external_genre_id": seed.external_genre_id,
            "shop_code": seed.shop_code,
            "active_status": seed.active_status
            if seed.active_status is not None
            else DEFAULT_ACTIVE_STATUS,
            "is_active": DEFAULT_IS_ACTIVE if seed.is_active is None else seed.is_active,
            "first_fetched_at": seed.first_fetched_at,
            "last_checked_at": seed.last_checked_at,
            "updated_at": None,
        }
        return seed

    def _row_to_diff(self, row: dict[str, object]) -> ProductDiffResultSeed:
        status = str(row["diff_status"])
        if status not in {"new", "updated", "unchanged", "unavailable"}:
            raise ValueError(f"unsupported diff_status: {status}")
        return ProductDiffResultSeed(
            product_diff_result_id=str(row["product_diff_result_id"]),
            batch_run_id=str(row["batch_run_id"]),
            staging_item_id=str(row["staging_item_id"]),
            external_item_code=str(row["external_item_code"]),
            diff_status=status,  # type: ignore[arg-type]
            old_hash=str(row["old_hash"]) if row.get("old_hash") is not None else None,
            new_hash=str(row["new_hash"]) if row.get("new_hash") is not None else None,
        )

    def _row_to_staging(self, row: dict[str, object]) -> StagingItemSeed:
        return StagingItemSeed(
            staging_item_id=str(row["staging_item_id"]),
            source=str(row.get("source") or DEFAULT_SOURCE),
            external_item_code=str(row["external_item_code"]),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            item_caption=str(row["item_caption"]) if row.get("item_caption") is not None else None,
            catchcopy=str(row["catchcopy"]) if row.get("catchcopy") is not None else None,
            price=int(row["price"]) if row.get("price") is not None else None,
            item_url=str(row["item_url"]) if row.get("item_url") is not None else None,
            external_genre_id=(
                str(row["external_genre_id"]) if row.get("external_genre_id") is not None else None
            ),
            shop_code=str(row["shop_code"]) if row.get("shop_code") is not None else None,
            availability=int(row["availability"]) if row.get("availability") is not None else None,
            review_average=(
                float(row["review_average"]) if row.get("review_average") is not None else None
            ),
            review_count=int(row["review_count"]) if row.get("review_count") is not None else None,
        )

    def _row_to_item(self, row: dict[str, object]) -> ItemSeed:
        return ItemSeed(
            source=str(row["source"]),
            external_item_code=str(row["external_item_code"]),
            normalized_hash=str(row["normalized_hash"]) if row.get("normalized_hash") else None,
            item_id=str(row["item_id"]) if row.get("item_id") else None,
            item_name=str(row["item_name"]) if row.get("item_name") is not None else None,
            item_caption=str(row["item_caption"]) if row.get("item_caption") is not None else None,
            catchcopy=str(row["catchcopy"]) if row.get("catchcopy") is not None else None,
            price=int(row["price"]) if row.get("price") is not None else None,
            item_url=str(row["item_url"]) if row.get("item_url") is not None else None,
            external_genre_id=(
                str(row["external_genre_id"]) if row.get("external_genre_id") is not None else None
            ),
            shop_code=str(row["shop_code"]) if row.get("shop_code") is not None else None,
            active_status=str(row["active_status"]) if row.get("active_status") is not None else None,
            is_active=bool(row["is_active"]) if row.get("is_active") is not None else None,
            first_fetched_at=(
                row["first_fetched_at"]  # type: ignore[arg-type]
                if isinstance(row.get("first_fetched_at"), datetime)
                else None
            ),
            last_checked_at=(
                row["last_checked_at"]  # type: ignore[arg-type]
                if isinstance(row.get("last_checked_at"), datetime)
                else None
            ),
        )


# Re-export for type checkers / tests that want DiffStatus alias near repos
__all__ = [
    "DEFAULT_ACTIVE_STATUS",
    "DEFAULT_IS_ACTIVE",
    "DEFAULT_SOURCE",
    "DiffStatus",
    "ItemApplyRepositories",
]
