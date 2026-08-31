"""楽天商品ランキングAPI（①③④⑤）の取得・正規化・集計。

公式仕様: https://webservice.rakuten.co.jp/documentation/ichiba-item-ranking

| パターン | 送出パラメータ | 出力 |
| --- | --- | --- |
| ① 総合 | genreId / age / sex を送らない | 総合ランキング |
| ③ 年代 | age のみ | その年代の総合ランキング |
| ④ 性別 | sex のみ | その性別の総合ランキング |
| ⑤ 年代×性別 | age と sex | その性別の年代別ランキング |

② ジャンル指定（genreId）は公式仕様で age / sex と併用不可のため、本モジュールでは送出しない。
楽天クエリ period も送らない（BATCH-002 と同じ。realtime 以外は 400 になり得る）。
secret は例外メッセージ・cache に残さない。
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / ".cache" / "ranking"

RANKING_URL = (
    "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
)
AGES: tuple[int, ...] = (10, 20, 30, 40, 50)
SEXES: tuple[int, ...] = (0, 1)
AGE_LABELS = {10: "10代", 20: "20代", 30: "30代", 40: "40代", 50: "50代以上"}
SEX_LABELS = {0: "男性", 1: "女性"}
PATTERN_LABELS = {
    "overall": "① 総合",
    "age": "③ 年代別",
    "sex": "④ 性別",
    "age_sex": "⑤ 年代×性別",
    "cross": "横断比較",
}
MIN_INTERVAL_SEC = 1.5
DEFAULT_PAGES = 1
MAX_PAGES = 2

_TOKEN_SPLIT = re.compile(
    r"[\s\u3000/／|｜・,、。!！?？:：;；\-－—~〜+＋*＊=＝&＆'\"「」『』（）()\[\]【】<>＜＞]+"
)
_BRACKETS = re.compile(r"[【\[]([^】\]]{2,40})[】\]]")
_UNITISH = re.compile(r"^\d+[個本枚袋箱gkgmlL円点位倍巻セット]?$", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "送料",
        "送料無料",
        "無料",
        "あす楽",
        "翌日お届け",
        "即日",
        "ポイント",
        "倍",
        "クーポン",
        "公式",
        "楽天",
        "市場",
        "ショップ",
        "店内",
        "対応",
        "用",
        "付き",
        "つき",
        "入り",
        "個",
        "本",
        "枚",
        "限定",
        "特価",
        "セール",
        "最安値",
        "人気",
        "新作",
        "新商品",
        "メール便",
        "ネコポス",
        "クリックポスト",
        "宅配",
        "レビュー",
        "口コミ",
        "ランキング",
        "1位",
        "お届け",
        "発送",
    }
)


class RankingFetchError(RuntimeError):
    """楽天ランキング取得失敗（secret を含まないメッセージ）。"""


@dataclass(frozen=True)
class RankingSlice:
    slice_id: str
    pattern: str
    age: int | None = None
    sex: int | None = None

    def label(self) -> str:
        if self.pattern == "overall":
            return "総合（パラメータ無指定）"
        if self.pattern == "age" and self.age is not None:
            return f"{AGE_LABELS[self.age]} 総合"
        if self.pattern == "sex" and self.sex is not None:
            return f"{SEX_LABELS[self.sex]} 総合"
        if self.pattern == "age_sex" and self.age is not None and self.sex is not None:
            return f"{SEX_LABELS[self.sex]} {AGE_LABELS[self.age]}"
        return self.slice_id

    def query_params(self) -> dict[str, str]:
        """楽天へ送るサービス固有パラメータ。genreId / period は付けない。"""
        params: dict[str, str] = {}
        if self.age is not None:
            params["age"] = str(self.age)
        if self.sex is not None:
            params["sex"] = str(self.sex)
        return params


@dataclass
class RankingItem:
    rank: int
    item_code: str
    item_name: str
    catchcopy: str
    shop_code: str
    shop_name: str
    genre_id: str
    price: int | None
    review_count: int | None
    review_average: float | None
    image_url: str
    item_url: str
    slice_id: str
    page: int = 1


@dataclass
class CountRow:
    key: str
    label: str
    count: int
    unique_items: int
    slice_ids: list[str]
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class SliceCache:
    slice_id: str
    pattern: str
    age: int | None
    sex: int | None
    fetched_at: str
    title: str
    last_build_date: str
    page_count: int
    items: list[RankingItem]


def all_slices() -> tuple[RankingSlice, ...]:
    rows: list[RankingSlice] = [RankingSlice("overall", "overall")]
    for age in AGES:
        rows.append(RankingSlice(f"age-{age}", "age", age=age))
    for sex in SEXES:
        rows.append(RankingSlice(f"sex-{sex}", "sex", sex=sex))
    for age in AGES:
        for sex in SEXES:
            rows.append(
                RankingSlice(f"age-{age}-sex-{sex}", "age_sex", age=age, sex=sex)
            )
    return tuple(rows)


def slices_for_pattern(pattern: str) -> tuple[RankingSlice, ...]:
    return tuple(s for s in all_slices() if s.pattern == pattern)


def get_slice(slice_id: str) -> RankingSlice | None:
    for slice_ in all_slices():
        if slice_.slice_id == slice_id:
            return slice_
    return None


def resolve_fetch_targets(*, pattern: str, slice_id: str, fetch_scope: str) -> list[RankingSlice]:
    """fetch_scope: slice / pattern / all"""
    if fetch_scope == "all":
        return list(all_slices())
    if fetch_scope == "pattern":
        if pattern == "cross":
            return list(all_slices())
        return list(slices_for_pattern(pattern))
    found = get_slice(slice_id)
    return [found] if found else []


def mask_secret(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    if len(text) <= 8:
        return "***REDACTED***"
    return f"{text[:2]}***REDACTED***{text[-2:]}"


def mask_text(text: str, *, secrets: tuple[str, ...]) -> str:
    masked = text
    for secret in secrets:
        if secret and secret in masked:
            masked = masked.replace(secret, mask_secret(secret))
    return masked


def credentials_status(env: dict[str, str] | None = None) -> dict[str, bool]:
    source = env if env is not None else {}
    app_id = (source.get("RAKUTEN_APPLICATION_ID") or "").strip()
    access_key = (source.get("RAKUTEN_ACCESS_KEY") or "").strip()
    return {
        "application_id": bool(app_id),
        "access_key": bool(access_key),
        "ready": bool(app_id and access_key),
    }


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_image(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, list) or not value:
        return ""
    first = value[0]
    if isinstance(first, str):
        return first.strip()
    if isinstance(first, dict):
        return _as_str(first.get("imageUrl") or first.get("url"))
    return ""


def _shop_code(item_obj: dict[str, Any], item_code: str) -> str:
    shop = _as_str(item_obj.get("shopCode"))
    if shop:
        return shop
    if ":" in item_code:
        return item_code.split(":", 1)[0]
    return ""


def parse_ranking_payload(
    payload: dict[str, Any],
    *,
    slice_id: str,
    page: int = 1,
) -> tuple[str, str, list[RankingItem]]:
    title = _as_str(payload.get("title"))
    last_build = _as_str(payload.get("lastBuildDate"))
    raw_items = payload.get("Items")
    if raw_items is None:
        raw_items = payload.get("items")
    if not isinstance(raw_items, list):
        raise RankingFetchError("invalid ranking payload: Items が配列ではありません")

    items: list[RankingItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        item_obj = entry.get("Item") if isinstance(entry.get("Item"), dict) else entry
        if not isinstance(item_obj, dict):
            continue
        rank = _as_int(item_obj.get("rank"))
        item_code = _as_str(item_obj.get("itemCode"))
        if rank is None or not item_code:
            continue
        items.append(
            RankingItem(
                rank=rank,
                item_code=item_code,
                item_name=_as_str(item_obj.get("itemName")),
                catchcopy=_as_str(item_obj.get("catchcopy")),
                shop_code=_shop_code(item_obj, item_code),
                shop_name=_as_str(item_obj.get("shopName")),
                genre_id=_as_str(item_obj.get("genreId")),
                price=_as_int(item_obj.get("itemPrice")),
                review_count=_as_int(item_obj.get("reviewCount")),
                review_average=_as_float(item_obj.get("reviewAverage")),
                image_url=_first_image(item_obj.get("mediumImageUrls"))
                or _first_image(item_obj.get("smallImageUrls")),
                item_url=_as_str(item_obj.get("itemUrl")),
                slice_id=slice_id,
                page=page,
            )
        )
    return title, last_build, items


def extract_keywords(*texts: str) -> list[str]:
    found: list[str] = []
    for text in texts:
        if not text:
            continue
        for match in _BRACKETS.findall(text):
            token = match.strip()
            if _keep_keyword(token):
                found.append(token)
        for part in _TOKEN_SPLIT.split(text):
            token = part.strip()
            if _keep_keyword(token):
                found.append(token)
    return found


def _keep_keyword(token: str) -> bool:
    if len(token) < 2 or len(token) > 24:
        return False
    if token in _STOPWORDS:
        return False
    if token.isdigit():
        return False
    if _UNITISH.match(token):
        return False
    return True


def aggregate_items(items: list[RankingItem]) -> dict[str, list[CountRow]]:
    return {
        "genres": _count_rows(items, key_fn=lambda i: i.genre_id, label_fn=lambda i: i.genre_id),
        "shops": _count_rows(
            items,
            key_fn=lambda i: i.shop_code,
            label_fn=lambda i: i.shop_name or i.shop_code,
        ),
        "keywords": _keyword_rows(items),
    }


def _count_rows(
    items: list[RankingItem],
    *,
    key_fn: Callable[[RankingItem], str],
    label_fn: Callable[[RankingItem], str],
) -> list[CountRow]:
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}
    item_sets: dict[str, set[str]] = defaultdict(set)
    slice_sets: dict[str, set[str]] = defaultdict(set)
    for item in items:
        key = key_fn(item)
        if not key:
            continue
        counts[key] += 1
        labels[key] = label_fn(item) or key
        item_sets[key].add(item.item_code)
        slice_sets[key].add(item.slice_id)
    rows = [
        CountRow(
            key=key,
            label=labels[key],
            count=counts[key],
            unique_items=len(item_sets[key]),
            slice_ids=sorted(slice_sets[key]),
        )
        for key in counts
    ]
    rows.sort(key=lambda r: (-len(r.slice_ids), -r.count, r.key))
    return rows


def _keyword_rows(items: list[RankingItem]) -> list[CountRow]:
    counts: Counter[str] = Counter()
    item_sets: dict[str, set[str]] = defaultdict(set)
    slice_sets: dict[str, set[str]] = defaultdict(set)
    for item in items:
        for token in extract_keywords(item.item_name, item.catchcopy):
            counts[token] += 1
            item_sets[token].add(item.item_code)
            slice_sets[token].add(item.slice_id)
    rows = [
        CountRow(
            key=token,
            label=token,
            count=counts[token],
            unique_items=len(item_sets[token]),
            slice_ids=sorted(slice_sets[token]),
        )
        for token in counts
    ]
    rows.sort(key=lambda r: (-len(r.slice_ids), -r.count, r.key))
    return rows


def cross_matrix(
    items: list[RankingItem],
    *,
    row_key: Callable[[RankingItem], str],
    col_key: Callable[[RankingItem], str],
    top_rows: int = 16,
) -> tuple[list[str], list[tuple[str, dict[str, int]]]]:
    pair: dict[tuple[str, str], int] = defaultdict(int)
    row_totals: Counter[str] = Counter()
    cols: set[str] = set()
    for item in items:
        rkey = row_key(item)
        ckey = col_key(item)
        if not rkey or not ckey:
            continue
        pair[(rkey, ckey)] += 1
        row_totals[rkey] += 1
        cols.add(ckey)
    col_list = sorted(cols)
    ranked_rows = [key for key, _ in row_totals.most_common(top_rows)]
    matrix = []
    for rkey in ranked_rows:
        cells = {ckey: pair.get((rkey, ckey), 0) for ckey in col_list}
        matrix.append((rkey, cells))
    return col_list, matrix


def default_slice_for_pattern(pattern: str) -> RankingSlice:
    if pattern == "age":
        return RankingSlice("age-20", "age", age=20)
    if pattern == "sex":
        return RankingSlice("sex-1", "sex", sex=1)
    if pattern == "age_sex":
        return RankingSlice("age-20-sex-1", "age_sex", age=20, sex=1)
    return RankingSlice("overall", "overall")


def cache_path(slice_id: str) -> Path:
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", slice_id)
    return CACHE_DIR / f"{safe}.json"


def save_slice_cache(cache: SliceCache) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = cache_path(cache.slice_id)
    payload = {
        "slice_id": cache.slice_id,
        "pattern": cache.pattern,
        "age": cache.age,
        "sex": cache.sex,
        "fetched_at": cache.fetched_at,
        "title": cache.title,
        "last_build_date": cache.last_build_date,
        "page_count": cache.page_count,
        "items": [asdict(item) for item in cache.items],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_slice_cache(slice_id: str) -> SliceCache | None:
    path = cache_path(slice_id)
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    items = []
    for row in raw.get("items") or []:
        if not isinstance(row, dict):
            continue
        items.append(
            RankingItem(
                rank=int(row.get("rank") or 0),
                item_code=_as_str(row.get("item_code")),
                item_name=_as_str(row.get("item_name")),
                catchcopy=_as_str(row.get("catchcopy")),
                shop_code=_as_str(row.get("shop_code")),
                shop_name=_as_str(row.get("shop_name")),
                genre_id=_as_str(row.get("genre_id")),
                price=_as_int(row.get("price")),
                review_count=_as_int(row.get("review_count")),
                review_average=_as_float(row.get("review_average")),
                image_url=_as_str(row.get("image_url")),
                item_url=_as_str(row.get("item_url")),
                slice_id=_as_str(row.get("slice_id") or slice_id),
                page=int(row.get("page") or 1),
            )
        )
    return SliceCache(
        slice_id=_as_str(raw.get("slice_id") or slice_id),
        pattern=_as_str(raw.get("pattern")),
        age=_as_int(raw.get("age")),
        sex=_as_int(raw.get("sex")),
        fetched_at=_as_str(raw.get("fetched_at")),
        title=_as_str(raw.get("title")),
        last_build_date=_as_str(raw.get("last_build_date")),
        page_count=int(raw.get("page_count") or 1),
        items=items,
    )


def load_all_cached() -> dict[str, SliceCache]:
    result: dict[str, SliceCache] = {}
    for slice_ in all_slices():
        cached = load_slice_cache(slice_.slice_id)
        if cached:
            result[slice_.slice_id] = cached
    return result


def flatten_cached_items(
    caches: dict[str, SliceCache],
    *,
    slice_ids: list[str] | None = None,
) -> list[RankingItem]:
    items: list[RankingItem] = []
    for slice_id, cache in caches.items():
        if slice_ids is not None and slice_id not in slice_ids:
            continue
        items.extend(cache.items)
    return items


def now_jst_iso() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S %Z")


def fetch_slice(
    slice_: RankingSlice,
    *,
    application_id: str,
    access_key: str,
    pages: int = DEFAULT_PAGES,
    get_json: Callable[[dict[str, str], int], dict[str, Any]] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> SliceCache:
    page_count = max(1, min(MAX_PAGES, int(pages)))
    getter = get_json or (
        lambda extra, page: default_get_json(
            extra,
            page,
            application_id=application_id,
            access_key=access_key,
        )
    )
    all_items: list[RankingItem] = []
    title = ""
    last_build = ""
    for page in range(1, page_count + 1):
        if page > 1:
            sleep_fn(MIN_INTERVAL_SEC)
        extra = slice_.query_params()
        if "genreId" in extra:
            raise RankingFetchError("genreId は本画面では送出しません")
        payload = getter(extra, page)
        page_title, page_build, page_items = parse_ranking_payload(
            payload, slice_id=slice_.slice_id, page=page
        )
        title = title or page_title
        last_build = last_build or page_build
        all_items.extend(page_items)
    return SliceCache(
        slice_id=slice_.slice_id,
        pattern=slice_.pattern,
        age=slice_.age,
        sex=slice_.sex,
        fetched_at=now_jst_iso(),
        title=title,
        last_build_date=last_build,
        page_count=page_count,
        items=all_items,
    )


def fetch_and_cache_many(
    targets: list[RankingSlice],
    *,
    application_id: str,
    access_key: str,
    pages: int = DEFAULT_PAGES,
    get_json: Callable[[dict[str, str], int], dict[str, Any]] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> tuple[list[str], list[tuple[str, str]]]:
    """成功 slice_id 一覧と (slice_id, エラー) を返す。"""
    ok: list[str] = []
    errors: list[tuple[str, str]] = []
    secrets = (application_id, access_key)
    for index, slice_ in enumerate(targets):
        if index > 0:
            sleep_fn(MIN_INTERVAL_SEC)
        try:
            cache = fetch_slice(
                slice_,
                application_id=application_id,
                access_key=access_key,
                pages=pages,
                get_json=get_json,
                sleep_fn=sleep_fn,
            )
            save_slice_cache(cache)
            ok.append(slice_.slice_id)
        except Exception as exc:  # noqa: BLE001
            errors.append((slice_.slice_id, mask_text(str(exc), secrets=secrets)))
    return ok, errors


def default_get_json(
    extra: dict[str, str],
    page: int,
    *,
    application_id: str,
    access_key: str,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    if "genreId" in extra:
        raise RankingFetchError("genreId は本画面では送出しません")
    params = {
        "applicationId": application_id,
        "accessKey": access_key,
        "format": "json",
        "formatVersion": "2",
        "page": str(page),
        **extra,
    }
    secrets = (application_id, access_key)
    url = f"{RANKING_URL}?{urlencode(params)}"
    request = Request(
        url,
        headers={"User-Agent": "okuri-local-data-browser/ranking-analysis"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read()
            status = getattr(response, "status", 200)
    except HTTPError as exc:
        detail = _error_body_detail(exc.read() if exc.fp else b"", secrets=secrets)
        hint = ""
        if exc.code == 403:
            hint = "。登録 egress IP 以外、または資格情報不一致の可能性があります"
        raise RankingFetchError(f"楽天ランキングAPI HTTP {exc.code}{detail}{hint}") from None
    except URLError as exc:
        reason = mask_text(str(getattr(exc, "reason", exc)), secrets=secrets)
        raise RankingFetchError(f"楽天ランキングAPI 通信エラー: {reason}") from None
    except TimeoutError:
        raise RankingFetchError("楽天ランキングAPI がタイムアウトしました") from None
    if status >= 400:
        raise RankingFetchError(f"楽天ランキングAPI HTTP {status}")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RankingFetchError("楽天ランキングAPI の JSON が不正です") from exc
    if not isinstance(payload, dict):
        raise RankingFetchError("楽天ランキングAPI の応答が object ではありません")
    return payload


def _error_body_detail(body: bytes, *, secrets: tuple[str, ...]) -> str:
    if not body:
        return ""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    parts = []
    for key in ("error", "error_description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(f"{key}={mask_text(value, secrets=secrets)}")
    return (": " + "; ".join(parts)) if parts else ""
