"""BATCH-003 楽天商品疑似差分取得ジョブ実装.

処理 Phase（仕様書 §8.2）:
plan → priority → fetch → adapt → extract → dedupe → raw_save → cursor → finalize
"""

from __future__ import annotations

import json
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
from batch.application.job_run import JobRunTracker, ScaffoldJobRunTracker
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
DEFAULT_MAX_PAGES = 1
DEFAULT_HITS = 30

# ranking_supplement を最優先（仕様書 §18.2 推奨）
_CURSOR_PRIORITY: dict[str, int] = {
    "ranking_supplement": 0,
    "genre": 1,
    "update_sort": 2,
    "keyword": 3,
}


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

    def run(
        self,
        *,
        job_run_id: str,
        target_genre_ids: Sequence[str] | None = None,
        keywords: Sequence[str] | None = None,
        max_pages: int | None = None,
        hits: int | None = None,
        include_update_sort: bool = True,
        trace_id: str | None = None,
    ) -> PseudoDiffSyncResult:
        bound_logger = self._logger.bind(job_run_id=job_run_id, trace_id=trace_id or job_run_id)
        self._tracker.start(batch_id=BATCH_ID, job_run_id=job_run_id)

        result = PseudoDiffSyncResult(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
        seen_item_codes: set[str] = set()

        try:
            plan = self._phase_plan(
                target_genre_ids=target_genre_ids,
                keywords=keywords,
                max_pages=max_pages,
                hits=hits,
                include_update_sort=include_update_sort,
            )
            result.planned_cursor_count = len(plan.cursors)
            result.completed_phases.append("plan")
            self._repos.record_phase(phase="plan", status="succeeded")

            ordered = self._phase_priority(plan.cursors)
            result.completed_phases.append("priority")
            self._repos.record_phase(phase="priority", status="succeeded")
            bound_logger.info(
                "item_pseudo_diff.plan",
                cursor_count=len(ordered),
            )

            if not ordered:
                result.status = "failed"
                result.error_codes.append("GRS-BAT-001")
                self._repos.record_error(code="GRS-BAT-001", summary="empty fetch_plan")
                self._tracker.complete(batch_id=BATCH_ID, job_run_id=job_run_id, status="failed")
                result.completed_phases.append("finalize")
                return result

            for cursor in ordered:
                cursor_key = cursor.cursor_id or f"{cursor.cursor_type}:{cursor.scope}"
                try:
                    self._sync_one_cursor(
                        cursor=cursor,
                        max_pages=plan.max_pages,
                        hits=plan.hits,
                        job_run_id=job_run_id,
                        result=result,
                        seen_item_codes=seen_item_codes,
                    )
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
                except Exception as exc:  # noqa: BLE001 — finalize partial failure
                    result.failed_cursor_ids.append(cursor_key)
                    result.error_codes.append("GRS-BAT-001")
                    self._repos.record_error(
                        code="GRS-BAT-001",
                        summary=str(exc),
                        cursor_id=cursor.cursor_id,
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
        max_pages: int | None,
        hits: int | None,
        include_update_sort: bool,
    ) -> PseudoDiffFetchPlan:
        resolved_pages = DEFAULT_MAX_PAGES if max_pages is None else max(1, int(max_pages))
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
            max_pages=resolved_pages,
            hits=resolved_hits,
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
        job_run_id: str,
        result: PseudoDiffSyncResult,
        seen_item_codes: set[str],
    ) -> None:
        # ranking_supplement は itemCode 指定のため 1 ページのみ
        pages = 1 if cursor.cursor_type == "ranking_supplement" else max_pages
        start_page = max(1, cursor.page)
        for page in range(start_page, start_page + pages):
            self._sync_one_page(
                cursor=cursor,
                page=page,
                hits=hits,
                job_run_id=job_run_id,
                result=result,
                seen_item_codes=seen_item_codes,
            )

    def _sync_one_page(
        self,
        *,
        cursor: FetchCursorRow,
        page: int,
        hits: int,
        job_run_id: str,
        result: PseudoDiffSyncResult,
        seen_item_codes: set[str],
    ) -> None:
        api_call_log_id = f"api_{uuid.uuid4().hex[:12]}"
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
            self._repos.record_api_call(
                api_call_log_id=api_call_log_id,
                fetch_cursor_id=cursor_id,
                cursor_type=cursor.cursor_type,
                status="failed",
                page=page,
                error_code=exc.code,
            )
            raise

        # adapt + extract
        try:
            adapted = adapt_item_search_raw_payload(raw_payload, cursor_type=cursor.cursor_type)
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

        # raw_save
        body = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        object_key = build_item_search_raw_object_key(
            batch_run_id=job_run_id,
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

        # cursor 進捗（API 成功後のみ）
        if cursor_id is not None:
            next_status = (
                "completed" if cursor.cursor_type == "ranking_supplement" else "active"
            )
            self._repos.update_cursor_progress(
                cursor_id=cursor_id,
                page=page + 1,
                cursor_status=next_status,
            )

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
