"""Rakuten API client scaffold."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class RakutenItem:
    """Placeholder for a Rakuten marketplace item."""

    item_code: str
    item_name: str


@dataclass(frozen=True)
class RakutenRankingEntry:
    """Placeholder for a Rakuten ranking hit."""

    rank: int
    item_code: str


@dataclass(frozen=True)
class RakutenGenre:
    """Rakuten genre node used by BATCH-001 and ranking fetch."""

    genre_id: str
    genre_name: str
    parent_genre_id: str | None = None
    genre_level: int | None = None
    children: tuple[str, ...] = ()


class RakutenGenreApiError(Exception):
    """Raised when genre fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, genre_id: str, code: str, message: str) -> None:
        self.genre_id = genre_id
        self.code = code
        self.message = message
        super().__init__(f"{code}: genre_id={genre_id}: {message}")


class RakutenRankingApiError(Exception):
    """Raised when ranking fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, genre_id: str, page: int, code: str, message: str) -> None:
        self.genre_id = genre_id
        self.page = page
        self.code = code
        self.message = message
        super().__init__(f"{code}: genre_id={genre_id} page={page}: {message}")


class RakutenItemSearchApiError(Exception):
    """Raised when item search fetch fails (mapped to GRS-EXT-* in the job layer)."""

    def __init__(self, *, cursor_type: str, page: int, code: str, message: str) -> None:
        self.cursor_type = cursor_type
        self.page = page
        self.code = code
        self.message = message
        super().__init__(f"{code}: cursor_type={cursor_type} page={page}: {message}")


class RakutenApiClient(Protocol):
    """Rakuten external API boundary (Phase4a protocol)."""

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]: ...

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]: ...

    def fetch_ranking_raw(
        self,
        *,
        genre_id: str,
        period: str = "daily",
        page: int = 1,
    ) -> dict[str, object]: ...

    def fetch_item_search_raw(
        self,
        *,
        cursor_type: str,
        genre_id: str | None = None,
        keyword: str | None = None,
        item_code: str | None = None,
        sort: str | None = None,
        page: int = 1,
        hits: int = 30,
    ) -> dict[str, object]: ...

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None: ...

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]: ...


@dataclass
class ScaffoldRakutenApiClient:
    """Phase4a placeholder client without outbound Rakuten API calls."""

    items: tuple[RakutenItem, ...] = ()
    ranking: tuple[RakutenRankingEntry, ...] = ()
    genres: dict[str, RakutenGenre] = field(default_factory=dict)
    raw_responses: dict[str, dict[str, object]] = field(default_factory=dict)
    # key: (genre_id, period, page)
    ranking_raw_responses: dict[tuple[str, str, int], dict[str, object]] = field(default_factory=dict)
    # key: (cursor_type, genre_id|keyword|item_code|*, page)
    item_search_raw_responses: dict[tuple[str, str, int], dict[str, object]] = field(
        default_factory=dict
    )
    fail_genre_ids: set[str] = field(default_factory=set)
    rate_limited_genre_ids: set[str] = field(default_factory=set)
    fail_ranking_keys: set[tuple[str, str, int]] = field(default_factory=set)
    rate_limited_ranking_keys: set[tuple[str, str, int]] = field(default_factory=set)
    fail_item_search_keys: set[tuple[str, str, int]] = field(default_factory=set)
    rate_limited_item_search_keys: set[tuple[str, str, int]] = field(default_factory=set)
    search_calls: list[dict[str, object]] = field(default_factory=list)
    ranking_calls: list[dict[str, object]] = field(default_factory=list)
    genre_calls: list[dict[str, object]] = field(default_factory=list)
    item_search_calls: list[dict[str, object]] = field(default_factory=list)

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]:
        self.search_calls.append({"keyword": keyword, "page": page})
        return self.items

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]:
        self.ranking_calls.append({"genre_id": genre_id, "page": page})
        return self.ranking

    def fetch_ranking_raw(
        self,
        *,
        genre_id: str,
        period: str = "daily",
        page: int = 1,
    ) -> dict[str, object]:
        """Return Raw JSON-compatible ranking payload for Object Storage persistence."""

        key = (genre_id, period, page)
        self.ranking_calls.append(
            {"genre_id": genre_id, "period": period, "page": page, "mode": "raw"}
        )
        self._raise_if_ranking_forced_failure(genre_id=genre_id, period=period, page=page)
        if key in self.ranking_raw_responses:
            return dict(self.ranking_raw_responses[key])

        if self.ranking:
            return {
                "lastBuildDate": "2026-07-13T00:00:00+0900",
                "genreId": genre_id,
                "period": period,
                "Items": [
                    {"rank": entry.rank, "itemCode": entry.item_code} for entry in self.ranking
                ],
            }

        raise RakutenRankingApiError(
            genre_id=genre_id,
            page=page,
            code="GRS-EXT-104",
            message="ranking not found in scaffold",
        )

    def fetch_item_search_raw(
        self,
        *,
        cursor_type: str,
        genre_id: str | None = None,
        keyword: str | None = None,
        item_code: str | None = None,
        sort: str | None = None,
        page: int = 1,
        hits: int = 30,
    ) -> dict[str, object]:
        """Return Raw JSON-compatible item search payload for Object Storage persistence."""

        scope_key = item_code or keyword or genre_id or "*"
        key = (cursor_type, scope_key, page)
        self.item_search_calls.append(
            {
                "cursor_type": cursor_type,
                "genre_id": genre_id,
                "keyword": keyword,
                "item_code": item_code,
                "sort": sort,
                "page": page,
                "hits": hits,
                "mode": "raw",
            }
        )
        self._raise_if_item_search_forced_failure(
            cursor_type=cursor_type,
            scope_key=scope_key,
            page=page,
        )
        if key in self.item_search_raw_responses:
            return dict(self.item_search_raw_responses[key])

        if self.items:
            # map 外（例: page>=2）でも BATCH-005 検証を通る最小形を返す。
            # サイレント劣化を避けるため stderr に警告を出す。
            print(
                "scaffold item_search fallback: "
                f"cursor_type={cursor_type!r} scope_key={scope_key!r} page={page} "
                "(no mapped response; using staging-complete items)",
                file=sys.stderr,
            )
            genre_value: int | str = 100
            if genre_id is not None and str(genre_id).strip() != "":
                try:
                    genre_value = int(str(genre_id))
                except ValueError:
                    genre_value = str(genre_id)
            return {
                "Items": [
                    {
                        "Item": {
                            "itemCode": item.item_code,
                            "itemName": item.item_name or item.item_code,
                            "itemCaption": f"Scaffold caption for {item.item_code}",
                            "catchcopy": "Scaffold catch",
                            "itemPrice": 1000,
                            "itemUrl": f"https://item.example/{item.item_code}",
                            "genreId": genre_value,
                            "shopCode": (
                                item.item_code.split(":", 1)[0]
                                if ":" in item.item_code
                                else "shop"
                            ),
                            "availability": 1,
                            "reviewAverage": 4.0,
                            "reviewCount": 0,
                            "mediumImageUrls": [
                                {
                                    "imageUrl": (
                                        f"https://img.example/medium/{item.item_code}.jpg"
                                    )
                                }
                            ],
                            "smallImageUrls": [
                                {
                                    "imageUrl": (
                                        f"https://img.example/small/{item.item_code}.jpg"
                                    )
                                }
                            ],
                        }
                    }
                    for item in self.items
                ]
            }

        raise RakutenItemSearchApiError(
            cursor_type=cursor_type,
            page=page,
            code="GRS-EXT-104",
            message="item search not found in scaffold",
        )

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None:
        self.genre_calls.append({"genre_id": genre_id})
        self._raise_if_forced_failure(genre_id)
        return self.genres.get(genre_id)

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]:
        """Return Raw JSON-compatible payload for Object Storage persistence."""

        self.genre_calls.append({"genre_id": genre_id, "mode": "raw"})
        self._raise_if_forced_failure(genre_id)
        if genre_id in self.raw_responses:
            return dict(self.raw_responses[genre_id])

        genre = self.genres.get(genre_id)
        if genre is None:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-104",
                message="genre not found in scaffold",
            )
        return {
            "genre": {
                "genreId": genre.genre_id,
                "jaName": genre.genre_name,
                "level": genre.genre_level,
            },
            "ancestors": (
                [{"genreId": genre.parent_genre_id}] if genre.parent_genre_id else []
            ),
            "children": [{"genreId": child_id} for child_id in genre.children],
        }

    def _raise_if_forced_failure(self, genre_id: str) -> None:
        if genre_id in self.rate_limited_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-102",
                message="scaffold forced rate limit",
            )
        if genre_id in self.fail_genre_ids:
            raise RakutenGenreApiError(
                genre_id=genre_id,
                code="GRS-EXT-100",
                message="scaffold forced genre fetch failure",
            )

    def _raise_if_ranking_forced_failure(
        self,
        *,
        genre_id: str,
        period: str,
        page: int,
    ) -> None:
        key = (genre_id, period, page)
        if key in self.rate_limited_ranking_keys:
            raise RakutenRankingApiError(
                genre_id=genre_id,
                page=page,
                code="GRS-EXT-102",
                message="scaffold forced ranking rate limit",
            )
        if key in self.fail_ranking_keys:
            raise RakutenRankingApiError(
                genre_id=genre_id,
                page=page,
                code="GRS-EXT-100",
                message="scaffold forced ranking fetch failure",
            )

    def _raise_if_item_search_forced_failure(
        self,
        *,
        cursor_type: str,
        scope_key: str,
        page: int,
    ) -> None:
        key = (cursor_type, scope_key, page)
        if key in self.rate_limited_item_search_keys:
            raise RakutenItemSearchApiError(
                cursor_type=cursor_type,
                page=page,
                code="GRS-EXT-102",
                message="scaffold forced item search rate limit",
            )
        if key in self.fail_item_search_keys:
            raise RakutenItemSearchApiError(
                cursor_type=cursor_type,
                page=page,
                code="GRS-EXT-100",
                message="scaffold forced item search fetch failure",
            )


# 楽天公開 API（Ichiba）。プロジェクト docs に URL 正本がないため公式エンドポイントを使用。
# 2026- 現行 endpoint（openapi.rakuten.co.jp）。旧 app.rakuten.co.jp は
# 新形式 applicationId(UUID)+accessKey を受け付けず specify valid applicationId になる。
_GENRE_SEARCH_URL = (
    "https://openapi.rakuten.co.jp/ichibagt/api/IchibaGenre/Search/20260701"
)
_ITEM_RANKING_URL = (
    "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
)
_ITEM_SEARCH_URL = (
    "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
)


def mask_rakuten_secret(value: str) -> str:
    """Redact Rakuten credentials that may appear in error strings."""

    if value.strip() == "":
        return ""
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _mask_text(text: str, *, secrets: tuple[str, ...]) -> str:
    masked = text
    for secret in secrets:
        if secret and secret in masked:
            masked = masked.replace(secret, mask_rakuten_secret(secret))
    return masked


def _rakuten_error_detail(response: object, *, secrets: tuple[str, ...]) -> str:
    """Extract short Rakuten error/error_description without leaking secrets."""

    try:
        payload = response.json()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        return ""
    if not isinstance(payload, dict):
        return ""
    parts: list[str] = []
    for key in ("error", "error_description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}={_mask_text(value, secrets=secrets)}")
    if not parts:
        return ""
    return ": " + "; ".join(parts)


@dataclass
class HttpRakutenApiClient:
    """Rakuten Ichiba HTTP client (genre / ranking / item_search).

    Secrets are never logged. Errors map to GRS-EXT-* used by job layers.
    Rate limiting uses MOD-BATCH-008 ``ExternalApiRateLimiter`` when provided.
    """

    application_id: str
    access_key: str
    timeout_seconds: float = 30.0
    backend: str = "http"
    rate_limiter: object | None = None

    def search_items(self, *, keyword: str, page: int = 1) -> tuple[RakutenItem, ...]:
        raw = self.fetch_item_search_raw(
            cursor_type="keyword",
            keyword=keyword,
            page=page,
        )
        items_raw = raw.get("Items")
        if not isinstance(items_raw, list):
            return ()
        result: list[RakutenItem] = []
        for entry in items_raw:
            if not isinstance(entry, dict):
                continue
            item_obj = entry.get("Item") if isinstance(entry.get("Item"), dict) else entry
            if not isinstance(item_obj, dict):
                continue
            code = str(item_obj.get("itemCode") or "")
            name = str(item_obj.get("itemName") or "")
            if code:
                result.append(RakutenItem(item_code=code, item_name=name))
        return tuple(result)

    def fetch_ranking(self, *, genre_id: str, page: int = 1) -> tuple[RakutenRankingEntry, ...]:
        raw = self.fetch_ranking_raw(genre_id=genre_id, page=page)
        items_raw = raw.get("Items")
        if not isinstance(items_raw, list):
            return ()
        entries: list[RakutenRankingEntry] = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            rank = item.get("rank")
            code = item.get("itemCode")
            if isinstance(rank, int) and isinstance(code, str) and code:
                entries.append(RakutenRankingEntry(rank=rank, item_code=code))
        return tuple(entries)

    def fetch_ranking_raw(
        self,
        *,
        genre_id: str,
        period: str = "daily",
        page: int = 1,
    ) -> dict[str, object]:
        # ドメイン上の period（daily 等）と楽天クエリ period は別物。
        # 現行 Ranking API の period は realtime 等の限定値で、genreId 併用時は
        # 送ると 400 になり得るため、API が認識する値のときだけ付与する。
        params = {
            **self._auth_params(),
            "genreId": genre_id,
            "page": str(page),
            "format": "json",
            "formatVersion": "2",
        }
        if period == "realtime":
            params["period"] = period
        return self._get_json(
            _ITEM_RANKING_URL,
            params,
            error_factory=lambda code, message: RakutenRankingApiError(
                genre_id=genre_id,
                page=page,
                code=code,
                message=message,
            ),
        )

    def fetch_item_search_raw(
        self,
        *,
        cursor_type: str,
        genre_id: str | None = None,
        keyword: str | None = None,
        item_code: str | None = None,
        sort: str | None = None,
        page: int = 1,
        hits: int = 30,
    ) -> dict[str, object]:
        params: dict[str, str] = {
            **self._auth_params(),
            "format": "json",
            "formatVersion": "2",
            "page": str(page),
            "hits": str(min(hits, 30)),
        }
        if genre_id:
            params["genreId"] = genre_id
        if keyword:
            params["keyword"] = keyword
        if item_code:
            params["itemCode"] = item_code
        resolved_sort = sort
        if resolved_sort is None and cursor_type in {"genre", "update_sort"}:
            resolved_sort = "-updateTimestamp"
        if resolved_sort:
            params["sort"] = resolved_sort

        return self._get_json(
            _ITEM_SEARCH_URL,
            params,
            error_factory=lambda code, message: RakutenItemSearchApiError(
                cursor_type=cursor_type,
                page=page,
                code=code,
                message=message,
            ),
        )

    def fetch_genre(self, *, genre_id: str) -> RakutenGenre | None:
        from batch.infrastructure.rakuten.adapter import adapt_genre_raw_payload

        raw = self.fetch_genre_raw(genre_id=genre_id)
        return adapt_genre_raw_payload(raw, requested_genre_id=genre_id)

    def fetch_genre_raw(self, *, genre_id: str) -> dict[str, object]:
        params = {
            **self._auth_params(),
            "genreId": genre_id,
            "format": "json",
            "formatVersion": "2",
        }
        return self._get_json(
            _GENRE_SEARCH_URL,
            params,
            error_factory=lambda code, message: RakutenGenreApiError(
                genre_id=genre_id,
                code=code,
                message=message,
            ),
        )

    def _auth_params(self) -> dict[str, str]:
        return {
            "applicationId": self.application_id,
            "accessKey": self.access_key,
        }

    def _get_json(
        self,
        url: str,
        params: dict[str, str],
        *,
        error_factory: object,
    ) -> dict[str, object]:
        import httpx

        from batch.infrastructure.rate_limiter import ExternalApiRateLimiter

        secrets = (self.application_id, self.access_key)
        limiter = self.rate_limiter if isinstance(self.rate_limiter, ExternalApiRateLimiter) else None
        max_attempts = 1 + (limiter.max_retries_on_429 if limiter is not None else 0)

        last_error: Exception | None = None
        for attempt in range(max_attempts):
            if limiter is not None:
                limiter.acquire()
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.get(url, params=params)
            except httpx.TimeoutException as exc:
                message = _mask_text(str(exc), secrets=secrets)
                raise error_factory("GRS-EXT-101", f"rakuten timeout: {message}") from exc  # type: ignore[operator]
            except httpx.HTTPError as exc:
                message = _mask_text(str(exc), secrets=secrets)
                raise error_factory("GRS-EXT-100", f"rakuten transport error: {message}") from exc  # type: ignore[operator]

            if response.status_code == 429:
                last_error = error_factory(  # type: ignore[operator]
                    "GRS-EXT-102",
                    "rakuten rate limited (HTTP 429)",
                )
                if limiter is not None and attempt + 1 < max_attempts:
                    limiter.wait_after_rate_limit()
                    continue
                raise last_error

            if response.status_code == 400:
                detail = _rakuten_error_detail(response, secrets=secrets)
                raise error_factory(  # type: ignore[operator]
                    "GRS-EXT-105",
                    f"rakuten invalid request (HTTP 400){detail}",
                )
            if response.status_code >= 400:
                detail = _rakuten_error_detail(response, secrets=secrets)
                raise error_factory(  # type: ignore[operator]
                    "GRS-EXT-100",
                    f"rakuten HTTP {response.status_code}{detail}",
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise error_factory("GRS-EXT-103", "rakuten invalid JSON response") from exc  # type: ignore[operator]
            if not isinstance(payload, dict):
                raise error_factory("GRS-EXT-103", "rakuten response is not an object")  # type: ignore[operator]
            return payload

        assert last_error is not None
        raise last_error


def create_rakuten_client(
    application_id: str | None,
    access_key: str | None,
    *,
    live: bool = False,
    fallback: RakutenApiClient | None = None,
    rate_limiter: object | None = None,
    enable_rate_limiter: bool = True,
) -> RakutenApiClient:
    """Build a RakutenApiClient.

    - ``live=False``（既定）→ Scaffold（CI / 通常 local）
    - ``live=True`` かつ credentials あり → HttpRakutenApiClient（MOD-BATCH-008 付き）
    - ``live=True`` だが credentials 不足 → Scaffold（呼び出し側で exit 2 を推奨）
    """

    if live and application_id and access_key:
        from batch.infrastructure.rate_limiter import create_external_api_rate_limiter

        limiter = rate_limiter
        if limiter is None and enable_rate_limiter:
            limiter = create_external_api_rate_limiter()
        return HttpRakutenApiClient(
            application_id=application_id,
            access_key=access_key,
            rate_limiter=limiter,
        )
    return fallback or ScaffoldRakutenApiClient()


def resolve_live_rakuten_flag(*, cli_live: bool, env_value: str | None) -> bool:
    """Resolve live flag from CLI and ``BATCH_RAKUTEN_LIVE`` env."""

    if cli_live:
        return True
    if env_value is None:
        return False
    return env_value.strip().lower() in {"1", "true", "yes", "on"}
