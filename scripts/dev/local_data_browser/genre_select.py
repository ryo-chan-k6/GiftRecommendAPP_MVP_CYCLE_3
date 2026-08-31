"""OKURI 初期取り扱いジャンルの選択（local cache）。

DB には書かない。external_genre の階層表示・後段フィルター用。
level 1 は parent が NULL の実データがあるため、仮想 root（id=0）の直下として扱う。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
HERE = Path(__file__).resolve().parent
CACHE_PATH = HERE / ".cache" / "okuri_target_genres.json"
VIRTUAL_ROOT_ID = 0
FILTER_MODES = ("descendants", "exact")


def parse_genre_id(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def parse_genre_ids(values: Iterable[Any]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for raw in values:
        gid = parse_genre_id(raw)
        if gid is None or gid == VIRTUAL_ROOT_ID or gid in seen:
            continue
        seen.add(gid)
        result.append(gid)
    return result


def normalize_filter_mode(raw: Any) -> str:
    text = str(raw or "").strip()
    return text if text in FILTER_MODES else "descendants"


def empty_selection() -> dict[str, Any]:
    return {
        "genre_ids": [],
        "filter_mode": "descendants",
        "updated_at": "",
    }


def load_selection(path: Path | None = None) -> dict[str, Any]:
    target = path or CACHE_PATH
    if not target.is_file():
        return empty_selection()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_selection()
    if not isinstance(raw, dict):
        return empty_selection()
    return {
        "genre_ids": parse_genre_ids(raw.get("genre_ids") or []),
        "filter_mode": normalize_filter_mode(raw.get("filter_mode")),
        "updated_at": str(raw.get("updated_at") or ""),
    }


def save_selection(
    genre_ids: Iterable[int],
    *,
    filter_mode: str = "descendants",
    path: Path | None = None,
) -> dict[str, Any]:
    target = path or CACHE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "genre_ids": parse_genre_ids(genre_ids),
        "filter_mode": normalize_filter_mode(filter_mode),
        "updated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S %Z"),
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def merge_visible_selection(
    existing: Iterable[int],
    *,
    visible: Iterable[int],
    checked: Iterable[int],
) -> list[int]:
    """現在ページのチェックだけ更新し、他階層の選択は残す。"""
    existing_ids = set(parse_genre_ids(existing))
    visible_ids = set(parse_genre_ids(visible))
    checked_ids = set(parse_genre_ids(checked))
    kept = existing_ids - visible_ids
    return sorted(kept | (checked_ids & visible_ids))


def is_virtual_root(genre_id: int | None) -> bool:
    return genre_id is None or genre_id == VIRTUAL_ROOT_ID


def child_parent_clause(parent_id: int | None) -> tuple[str, tuple[Any, ...]]:
    """直下の子を取る WHERE。仮想 root は parent IS NULL かつ id<>0。

    external_genre.parent が L1 直付けになっている場合の fallback 用。
    階層表示の正は pick_closest_parents / staging 再構成。
    """
    if is_virtual_root(parent_id):
        return (
            "g.parent_external_genre_id IS NULL AND g.external_genre_id <> %s",
            (VIRTUAL_ROOT_ID,),
        )
    return ("g.parent_external_genre_id = %s", (int(parent_id),))


def parse_parent_id(raw: Any) -> int | None:
    """親ID。0（仮想 root）は保持する。"""
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return value


def pick_closest_parents(
    rows: Iterable[tuple[Any, Any, Any]],
) -> dict[int, int | None]:
    """(child_id, parent_id, parent_level) から、親レベルが最大の親を選ぶ。

    BATCH-001 が後から L1 の children を再 upsert すると、
    external_genre.parent が L1 直付けになる。staging 上の複数親から
    最も深い親を直近親とする。
    """
    best: dict[int, tuple[int | None, int]] = {}
    for child_raw, parent_raw, parent_level_raw in rows:
        child_id = parse_genre_id(child_raw)
        if child_id is None:
            continue
        parent_id = parse_parent_id(parent_raw)
        try:
            parent_level = int(parent_level_raw)
        except (TypeError, ValueError):
            parent_level = -1
        prev = best.get(child_id)
        if prev is None or parent_level > prev[1]:
            best[child_id] = (parent_id, parent_level)
    return {child_id: parent_id for child_id, (parent_id, _) in best.items()}


def build_children_map(parent_of: dict[int, int | None]) -> dict[int, list[int]]:
    children: dict[int, list[int]] = {}
    for child_id, parent_id in parent_of.items():
        if child_id == VIRTUAL_ROOT_ID:
            continue
        key = VIRTUAL_ROOT_ID if parent_id is None else parent_id
        children.setdefault(key, []).append(child_id)
    for values in children.values():
        values.sort()
    return children


def count_descendants(
    node: int,
    children_by_parent: dict[int, list[int]],
    memo: dict[int, int] | None = None,
) -> int:
    store = memo if memo is not None else {}
    if node in store:
        return store[node]
    total = 0
    for child in children_by_parent.get(node, ()):
        total += 1 + count_descendants(child, children_by_parent, store)
    store[node] = total
    return total


def descendant_counts(children_by_parent: dict[int, list[int]]) -> dict[int, int]:
    memo: dict[int, int] = {}
    for parent_id in children_by_parent:
        count_descendants(parent_id, children_by_parent, memo)
    for child_ids in children_by_parent.values():
        for child_id in child_ids:
            count_descendants(child_id, children_by_parent, memo)
    return memo


def expand_descendants(
    selected_ids: Iterable[int],
    children_by_parent: dict[int, list[int]],
) -> set[int]:
    expanded: set[int] = set(parse_genre_ids(selected_ids))
    stack = list(expanded)
    while stack:
        current = stack.pop()
        for child in children_by_parent.get(current, ()):
            if child not in expanded:
                expanded.add(child)
                stack.append(child)
    return expanded
