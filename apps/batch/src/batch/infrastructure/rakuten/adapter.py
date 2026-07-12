"""Rakuten genre response adapter for BATCH-001."""

from __future__ import annotations

from typing import Any

from batch.infrastructure.rakuten.client import RakutenGenre, RakutenGenreApiError


def adapt_genre_raw_payload(payload: dict[str, object], *, requested_genre_id: str) -> RakutenGenre:
    """Map Rakuten genre search JSON (formatVersion=2 shape) to RakutenGenre.

    Secret fields are never expected in payloads persisted by this adapter.
    """

    genre_obj = payload.get("genre")
    if not isinstance(genre_obj, dict):
        raise RakutenGenreApiError(
            genre_id=requested_genre_id,
            code="GRS-EXT-103",
            message="invalid genre payload: missing genre object",
        )

    genre_id = _as_str(genre_obj.get("genreId")) or requested_genre_id
    genre_name = _as_str(genre_obj.get("jaName")) or _as_str(genre_obj.get("genreName"))
    if not genre_name:
        raise RakutenGenreApiError(
            genre_id=genre_id,
            code="GRS-EXT-103",
            message="invalid genre payload: missing jaName/genreName",
        )

    parent_genre_id = _as_str(genre_obj.get("parentGenreId"))
    if parent_genre_id is None:
        ancestors = payload.get("ancestors")
        if isinstance(ancestors, list) and ancestors:
            first = ancestors[0]
            if isinstance(first, dict):
                parent_genre_id = _as_str(first.get("genreId"))

    level_raw = genre_obj.get("level")
    genre_level: int | None
    if isinstance(level_raw, int):
        genre_level = level_raw
    elif isinstance(level_raw, str) and level_raw.isdigit():
        genre_level = int(level_raw)
    else:
        genre_level = None

    children: list[str] = []
    children_raw = payload.get("children")
    if isinstance(children_raw, list):
        for child in children_raw:
            if isinstance(child, dict):
                child_id = _as_str(child.get("genreId"))
                if child_id:
                    children.append(child_id)

    return RakutenGenre(
        genre_id=genre_id,
        genre_name=genre_name,
        parent_genre_id=parent_genre_id,
        genre_level=genre_level,
        children=tuple(children),
    )


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
