"""BATCH-001 楽天ジャンル同期 — domain models and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

GenreSyncRunStatus = Literal["succeeded", "partially_succeeded", "failed"]


@dataclass(frozen=True)
class GenreFetchPlan:
    """Resolved fetch plan for BATCH-001 (plan phase output)."""

    source: str
    target_genre_ids: tuple[str, ...]


@dataclass(frozen=True)
class GenreRow:
    """Normalized genre row for staging_genre / external_genre upsert.

    Idempotency key: source + external_genre_id
    """

    source: str
    external_genre_id: str
    genre_name: str
    parent_external_genre_id: str | None
    genre_level: int | None
    is_leaf: bool = False

    @property
    def idempotency_key(self) -> tuple[str, str]:
        return (self.source, self.external_genre_id)


@dataclass(frozen=True)
class RawGenreArtifact:
    """Raw Object Storage + Metadata artifact for one genre fetch."""

    object_key: str
    content_hash: str
    api_call_log_id: str
    genre_id: str
    body: bytes


@dataclass
class GenreSyncResult:
    """Finalize-phase summary for BATCH-001."""

    batch_id: str
    job_run_id: str
    status: GenreSyncRunStatus
    planned_genre_ids: tuple[str, ...] = ()
    succeeded_genre_ids: list[str] = field(default_factory=list)
    failed_genre_ids: list[str] = field(default_factory=list)
    completed_phases: list[str] = field(default_factory=list)
    upserted_external_genre_count: int = 0
    error_codes: list[str] = field(default_factory=list)
