"""BATCH-003 楽天商品疑似差分取得ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → priority → fetch → adapt → extract → dedupe → raw_save → cursor → finalize

Run予算（pages_per_run / cursors_per_run / wall_clock）は 1 Run の進行量上限であり、
カタログ深さ打ち切りではない。予算到達時は cursor を active のまま保持し次回継続する。
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from collections.abc import Sequence

from batch.application.item_pseudo_diff.idempotency import (
    SOURCE_RAKUTEN,
    build_item_search_raw_object_key,
    content_hash_for_payload,
)
from batch.application.item_pseudo_diff.models import (
    FetchCursorRow,
    ProductCandidate,
    PseudoDiffFetchPlan,
    PseudoDiffSyncResult,
    RawItemSearchArtifact,
)
from batch.application.item_pseudo_diff.repositories import ItemPseudoDiffRepositories
from batch.application.job_run import (
    PIPELINE_ITEM_IMPORT_BATCH_NAME,
    JobRunTracker,
    ScaffoldJobRunTracker,
)
from batch.infrastructure.logger import BatchLogger, ScaffoldBatchLogger
from batch.infrastructure.object_storage import ObjectStorageError
from batch.infrastructure.rakuten import (
    RakutenApiClient,
    RakutenItemSearchApiError,
    ScaffoldRakutenApiClient,
    adapt_item_search_raw_payload,
)

BATCH_ID = "BATCH-003"
ITEM_PSEUDO_DIFF_PHASES: tuple[str, ...] = (
    "plan",
    "priority",
    "fetch",
    "adapt",
    "extract",
    "dedupe",
    "raw_save",
    "cursor",
    "finalize",
)

# MVP placeholder（本番ジャンルID / 上限は Human が fetch_plan で設定）
DEFAULT_TARGET_GENRE_IDS: tuple[str, ...] = ("100",)
# smoke / scaffold 既定。通常継続の採択値は pages_per_run=60（CLI で指定）
DEFAULT_PAGES_PER_RUN = 1
DEFAULT_MAX_PAGES = DEFAULT_PAGES_PER_RUN  # 互換 alias
# CLI 既定は 1。job.run(cursors_per_run=None) は計画上の全 active cursor（UT 互換）
DEFAULT_CURSORS_PER_RUN = 1
DEFAULT_WALL_CLOCK_SECONDS: int | None = None
DEFAULT_HITS = 30

# ranking_supplement を最優先（仕様書 §18.2 推奨）
_CURSOR_PRIORITY: dict[str, int] = {
    "ranking_supplement": 0,
    "genre": 1,
    "update_sort": 2,
    "keyword": 3,
}

_RATE_LIMIT_CODE = "GRS-EXT-102"


class ItemPseudoDiffJob:
    """Orchestrates BATCH-003 item pseudo-diff fetch phases."""

    def __init__(
        self,
        *,
        rakuten_client: RakutenApiClient | None = None,
        repositories: ItemPseudoDiffRepositories,
        job_run_tracker: JobRunTracker | None = None,
        logger: BatchLogger | None = None,
    ) -> None:
        self._rakuten = rakuten_client or ScaffoldRakutenApiClient()
        self._repos = repositories
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
        batch_run_id: str | None = None,
        target_genre_ids: Sequence[str] | None = None,
        keywords: Sequence[str] | None = None,
        max_pages: int | None = None,
        pages_per_run: int | None = None,
        cursors_per_run: int | None = None,
        wall_clock_seconds: int | None = None,
        hits: int | None = None,
        include_update_sort: bool = True,
        trace_id: str | None = None,
    ) -> PseudoDiffSyncResult:
        # tracker は葉 job_run_id。業務 data / raw object key は共有 batch_run_id。
        business_run_id = (batch_run_id or "").strip() or job_run_id
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        # 案 A: pipeline UUID を batch_run_log 親ヘッダとして ensure（017 / LOGICAL FK）
        if business_run_id != job_run_id:
            self._tracker.ensure_batch_run(
                batch_id=PIPELINE_ITEM_IMPORT_BATCH_NAME,
                batch_run_id=business_run_id,
            )
            print(
                "pipeline batch_run_log ensure: "
                f"batch_run_id={business_run_id} batch_name={PIPELINE_ITEM_IMPORT_BATCH_NAME}",
                file=sys.stderr,
            )
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = PseudoDiffSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
        seen_item_codes: set[str] = set()

        try:
            plan = self._phase_plan(
                target_genre_ids=target_genre_ids,
                keywords=keywords,
                pages_per_run=pages_per_run if pages_per_run is not None else max_pages,
                cursors_per_run=cursors_per_run,
                wall_clock_seconds=wall_clock_seconds,
                hits=hits,
                include_update_sort=include_update_sort,
            )
            result.planned_cursor_count = len(plan.cursors)
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")

            ordered = self._phase_priority(plan.cursors)
            active_ordered = [c for c in ordered if c.cursor_status == "active"]
            result.skipped_inactive_cursor_count = len(ordered) - len(active_ordered)
            result.completed_phases.append("priority")
            self._repos.record_phase(phase="priority", status="succeeded")
            bound_logger.info(
                "item_pseudo_diff.plan",
                cursor_count=len(ordered),
                active_cursor_count=len(active_ordered),
                pages_per_run=plan.pages_per_run,
                cursors_per_run=plan.cursors_per_run,
            )

            if not ordered:
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty fetch_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            if not active_ordered:
                # paused/failed/exhausted のみ — 手動再開待ち。失敗扱いにしない。
                result.status = "succeeded"
                self._tracker.complete(
                    batch_id=BATCH_ID, job_run_id=job_run_id, status="succeeded"
                )
                result.completed_phases.extend(
                    ["fetch", "adapt", "extract", "dedupe", "raw_save", "cursor", "finalize"]
                )
                self._repos.record_phase(phase="finalize", status="succeeded")
                return result

            deadline: float | None = None
            if plan.wall_clock_seconds is not None and plan.wall_clock_seconds > 0:
                deadline = time.monotonic() + float(plan.wall_clock_seconds)

            pages_remaining = plan.pages_per_run
            cursors_remaining = (
                plan.cursors_per_run
                if plan.cursors_per_run is not None
                else len(active_ordered)
            )

            for cursor in active_ordered:
                if cursors_remaining <= 0 or pages_remaining <= 0:
                    result.run_budget_stopped = True
                    break
                if deadline is not None and time.monotonic() >= deadline:
                    result.run_budget_stopped = True
                    break

                cursor_key = cursor.cursor_id or f"{cursor.cursor_type}:{cursor.scope}"
                pages_for_cursor = (
                    1 if cursor.cursor_type == "ranking_supplement" else pages_remaining
                )
                try:
                    pages_done = self._sync_one_cursor(
                        cursor=cursor,
                        max_pages=pages_for_cursor,
                        hits=plan.hits,
                        batch_run_id=business_run_id,
                        result=result,
                        seen_item_codes=seen_item_codes,
                        deadline=deadline,
                    )
                    result.pages_fetched += pages_done
                    result.cursors_started += 1
                    pages_remaining -= pages_done
                    cursors_remaining -= 1
                    if pages_remaining <= 0 or (
                        deadline is not None and time.monotonic() >= deadline
                    ):
                        result.run_budget_stopped = True
                    result.succeeded_cursor_ids.append(cursor_key)
                    if cursor.cursor_type == "ranking_supplement":
                        result.ranking_supplement_consumed_count += 1
                except RakutenItemSearchApiError as exc:
                    result.failed_cursor_ids.append(cursor_key)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        cursor_id=cursor.cursor_id,
                    )
                    result.cursors_started += 1
                    cursors_remaining -= 1
                    print(
                        f"item_pseudo_diff.cursor_failed cursor_type={cursor.cursor_type} "
                        f"error_code={exc.code} summary={exc.message}",
                        file=sys.stderr,
                    )
                    bound_logger.error(
                        "item_pseudo_diff.cursor_failed",
                        cursor_type=cursor.cursor_type,
                        error_code=exc.code,
                    )
                except ObjectStorageError as exc:
                    result.failed_cursor_ids.append(cursor_key)
                    result.error_codes.append(exc.code)
                    self._repos.record_error(
                        code=exc.code,
                        summary=exc.message,
                        cursor_id=cursor.cursor_id,
                    )
                    result.cursors_started += 1
                    cursors_remaining -= 1
                    print(
                        f"item_pseudo_diff.cursor_failed cursor_type={cursor.cursor_type} "
                        f"error_code={exc.code} summary={exc.message}",
                        file=sys.stderr,
                    )
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_cursor_ids.append(cursor_key)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        cursor_id=cursor.cursor_id,
                    )
                    result.cursors_started += 1
                    cursors_remaining -= 1
                    print(
                        f"item_pseudo_diff.unexpected_failure cursor_type={cursor.cursor_type} "
                        f"error_type={type(exc).__name__} summary={exc}",
                        file=sys.stderr,
                    )
                    bound_logger.error(
                        "item_pseudo_diff.unexpected_failure",
                        cursor_type=cursor.cursor_type,
                    )

            for phase in ("fetch", "adapt", "extract", "dedupe", "raw_save", "cursor"):
                if phase not in result.completed_phases:
                    result.completed_phases.append(phase)

            result.candidate_item_code_count = len(seen_item_codes)
            result.created_items = list(self._repos.created_items)
            result.created_staging = list(self._repos.created_staging)
            result = self._phase_finalize(result)
            bound_logger.info(
                "item_pseudo_diff.finalize",
                status=result.status,
                succeeded=len(result.succeeded_cursor_ids),
                failed=len(result.failed_cursor_ids),
                pages_fetched=result.pages_fetched,
                run_budget_stopped=result.run_budget_stopped,
            )
            return result
        except Exception:
            self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
            raise

    def _phase_plan(
        self,
        *,
        target_genre_ids: Sequence[str] | None,
        keywords: Sequence[str] | None,
        pages_per_run: int | None,
        cursors_per_run: int | None,
        wall_clock_seconds: int | None,
        hits: int | None,
        include_update_sort: bool,
    ) -> PseudoDiffFetchPlan:
        resolved_pages = (
            DEFAULT_PAGES_PER_RUN if pages_per_run is None else max(1, int(pages_per_run))
        )
        resolved_cursors: int | None
        if cursors_per_run is None:
            resolved_cursors = None  # 計画上の全 active（CLI は既定 1 を渡す）
        else:
            resolved_cursors = max(1, int(cursors_per_run))
        resolved_wall = wall_clock_seconds
        if resolved_wall is not None:
            resolved_wall = max(1, int(resolved_wall))
        resolved_hits = DEFAULT_HITS if hits is None else max(1, min(30, int(hits)))

        cursors: list[FetchCursorRow] = []

        # 既存 active カーソル（ranking_supplement 等）を取り込み
        for seed in self._repos.list_active_cursors():
            cursors.append(self._repos.get_or_create_cursor(seed))

        genre_ids = (
            DEFAULT_TARGET_GENRE_IDS
            if target_genre_ids is None or len(tuple(target_genre_ids)) == 0
            else tuple(str(g).strip() for g in target_genre_ids if str(g).strip())
        )
        for genre_id in genre_ids:
            cursors.append(
                self._repos.get_or_create_cursor(
                    FetchCursorRow(
                        cursor_type="genre",
                        target_external_genre_id=genre_id,
                        scope={"sort": "-updateTimestamp"},
                        page=1,
                    )
                )
            )

        if include_update_sort:
            cursors.append(
                self._repos.get_or_create_cursor(
                    FetchCursorRow(
                        cursor_type="update_sort",
                        scope={"sort": "-updateTimestamp"},
                        page=1,
                    )
                )
            )

        if keywords:
            for keyword in keywords:
                kw = str(keyword).strip()
                if not kw:
                    continue
                cursors.append(
                    self._repos.get_or_create_cursor(
                        FetchCursorRow(
                            cursor_type="keyword",
                            scope={"keyword": kw},
                            page=1,
                        )
                    )
                )

        # 重複 cursor_id を除去（同一 get-or-create 結果）
        unique: dict[str, FetchCursorRow] = {}
        for row in cursors:
            assert row.cursor_id is not None
            unique[row.cursor_id] = row

        return PseudoDiffFetchPlan(
            source=SOURCE_RAKUTEN,
            cursors=tuple(unique.values()),
            pages_per_run=resolved_pages,
            hits=resolved_hits,
            cursors_per_run=resolved_cursors,
            wall_clock_seconds=resolved_wall,
        )

    def _phase_priority(self, cursors: Sequence[FetchCursorRow]) -> list[FetchCursorRow]:
        return sorted(
            cursors,
            key=lambda c: (_CURSOR_PRIORITY.get(c.cursor_type, 99), c.cursor_id or ""),
        )

    def _sync_one_cursor(
        self,
        *,
        cursor: FetchCursorRow,
        max_pages: int,
        hits: int,
        batch_run_id: str,
        result: PseudoDiffSyncResult,
        seen_item_codes: set[str],
        deadline: float | None,
    ) -> int:
        """Fetch up to max_pages for one cursor. Returns pages successfully fetched.

        Run予算到達や wall-clock で途中停止した場合も、成功ページ分の cursor は
        active のまま次 page を保持する（exhausted にしない）。
        """

        pages = 1 if cursor.cursor_type == "ranking_supplement" else max_pages
        start_page = max(1, cursor.page)
        pages_done = 0
        for page in range(start_page, start_page + pages):
            if deadline is not None and time.monotonic() >= deadline:
                result.run_budget_stopped = True
                break
            exhausted = self._sync_one_page(
                cursor=cursor,
                page=page,
                hits=hits,
                batch_run_id=batch_run_id,
                result=result,
                seen_item_codes=seen_item_codes,
            )
            pages_done += 1
            if exhausted:
                break
        return pages_done

    def _sync_one_page(
        self,
        *,
        cursor: FetchCursorRow,
        page: int,
        hits: int,
        batch_run_id: str,
        result: PseudoDiffSyncResult,
        seen_item_codes: set[str],
    ) -> bool:
        """Process one page. Returns True when cursor reached catalog end (exhausted)."""

        api_call_log_id = str(uuid.uuid4())
        cursor_id = cursor.cursor_id

        genre_id = cursor.target_external_genre_id
        keyword = str(cursor.scope.get("keyword") or "") or None
        item_code = str(cursor.scope.get("external_item_code") or "") or None
        sort = str(cursor.scope.get("sort") or "") or None

        # fetch
        try:
            raw_payload = self._rakuten.fetch_item_search_raw(
                cursor_type=cursor.cursor_type,
                genre_id=genre_id,
                keyword=keyword,
                item_code=item_code,
                sort=sort,
                page=page,
                hits=hits,
            )
        except RakutenItemSearchApiError as exc:
            call_status = "rate_limited" if exc.code == _RATE_LIMIT_CODE else "failed"
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                fetch_cursor_id=cursor_id,
                cursor_type=cursor.cursor_type,
                status=call_status,
                page=page,
                error_code=exc.code,
            )
            # rate_limited → paused。page / last_fetched_at は成功扱いで進めない。
            if exc.code == _RATE_LIMIT_CODE and cursor_id is not None:
                self._repos.update_cursor_progress(
                    cursor_id=cursor_id,
                    page=page,
                    cursor_status="paused",
                    mark_fetched=False,
                )
            raise

        # adapt + extract（空 Items は範囲完了 = exhausted。GRS-EXT-103 にしない）
        try:
            adapted = adapt_item_search_raw_payload(
                raw_payload,
                cursor_type=cursor.cursor_type,
                page=page,
                allow_empty=True,
            )
        except RakutenItemSearchApiError as exc:
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                fetch_cursor_id=cursor_id,
                cursor_type=cursor.cursor_type,
                status="failed",
                page=page,
                error_code=exc.code,
            )
            raise

        self._repos.record_api_call(
            api_call_log_id=api_call_log_id,
            fetch_cursor_id=cursor_id,
            cursor_type=cursor.cursor_type,
            status="succeeded",
            page=page,
        )

        catalog_exhausted = False
        if cursor.cursor_type == "ranking_supplement":
            catalog_exhausted = True
        elif not adapted.candidates:
            catalog_exhausted = True
        else:
            page_count = _as_positive_int(raw_payload.get("pageCount"))
            if page_count is not None and page >= page_count:
                catalog_exhausted = True

        # dedupe（Run 内 itemCode）
        unique_candidates: list[ProductCandidate] = []
        for entry in adapted.candidates:
            if entry.external_item_code in seen_item_codes:
                continue
            seen_item_codes.add(entry.external_item_code)
            unique_candidates.append(
                ProductCandidate(
                    external_item_code=entry.external_item_code,
                    item_name=entry.item_name,
                    genre_id=entry.genre_id,
                )
            )
        _ = unique_candidates  # 抽出結果は Raw 保存が正。後続 BATCH-005 が利用

        # raw_save（object key の batch_run_id は共有 pipeline UUID）
        body = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        object_key = build_item_search_raw_object_key(
            batch_run_id=batch_run_id,
            api_call_log_id=api_call_log_id,
        )
        artifact = RawItemSearchArtifact(
            object_key=object_key,
            content_hash=content_hash_for_payload(body),
            api_call_log_id=api_call_log_id,
            cursor_id=cursor_id,
            cursor_type=cursor.cursor_type,
            page=page,
            body=body,
        )
        saved = self._repos.save_raw(artifact)
        if saved:
            result.raw_save_success_count += 1

        # cursor 進捗（API 成功後のみ）。Run予算停止では exhausted にしない。
        if cursor_id is not None:
            if catalog_exhausted:
                next_status = "completed"
                next_page = page
            else:
                next_status = "active"
                next_page = page + 1
            self._repos.update_cursor_progress(
                cursor_id=cursor_id,
                page=next_page,
                cursor_status=next_status,
            )
        return catalog_exhausted

    def _phase_finalize(self, result: PseudoDiffSyncResult) -> PseudoDiffSyncResult:
        if result.failed_cursor_ids and result.succeeded_cursor_ids:
            result.status = "partially_succeeded"
            if "GRS-BAT-002" not in result.error_codes:
                result.error_codes.append("GRS-BAT-002")
            tracker_status = "partially_succeeded"
        elif result.failed_cursor_ids and not result.succeeded_cursor_ids:
            result.status = "failed"
            if "GRS-BAT-001" not in result.error_codes:
                result.error_codes.append("GRS-BAT-001")
            tracker_status = "failed"
        else:
            result.status = "succeeded"
            tracker_status = "succeeded"

        self._tracker.complete(
            batch_id=BATCH_ID,
            job_run_id=result.job_run_id,
            status=tracker_status,
        )
        self._repos.record_phase(phase="finalize", status=result.status)
        result.completed_phases.append("finalize")
        return result


def _as_positive_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None
