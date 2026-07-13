"""BATCH-002 楽天ランキングスナップショット — domain models and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RankingSyncRunStatus = Literal["succeeded", "partially_succeeded", "failed"]


@dataclass(frozen=True)
class RankingFetchPlan:
    """Resolved fetch plan for BATCH-002 (plan phase output)."""

    source: str
    target_genre_ids: tuple[str, ...]
    period: str
    max_pages: int = 1


@dataclass(frozen=True)
class RankingSnapshotHeader:
    """ranking_snapshot header (観測正本).

    Idempotency key: source + external_genre_id + period + last_build_date
    """

    source: str
    external_genre_id: str
    period: str
    last_build_date: str
    ranking_snapshot_id: str | None = None

    @property
    def idempotency_key(self) -> tuple[str, str, str, str]:
        return (self.source, self.external_genre_id, self.period, self.last_build_date)


@dataclass(frozen=True)
class PopularitySignalRow:
    """item_popularity_signal row.

    Idempotency key: ranking_snapshot_id + rank
    """

    ranking_snapshot_id: str
    rank: int
    external_item_code: str
    item_id: str | None
    external_genre_id: str
    period: str

    @property
    def idempotency_key(self) -> tuple[str, int]:
        return (self.ranking_snapshot_id, self.rank)


@dataclass(frozen=True)
class StagingRankingRow:
    """staging_ranking_signal row (本 Batch 内中間)."""

    source: str
    external_genre_id: str
    period: str
    last_build_date: str
    rank: int
    external_item_code: str

    @property
    def idempotency_key(self) -> tuple[str, str, str, str, int]:
        return (
            self.source,
            self.external_genre_id,
            self.period,
            self.last_build_date,
            self.rank,
        )


@dataclass(frozen=True)
class RawRankingArtifact:
    """Raw Object Storage + Metadata artifact for one ranking fetch."""

    object_key: str
    content_hash: str
    api_call_log_id: str
    genre_id: str
    period: str
    page: int
    body: bytes


@dataclass(frozen=True)
class UnknownItemCandidate:
    """未登録 itemCode 補完候補（fetch_cursor / ranking_supplement）。

    Item 正本は作らない。BATCH-003 入力となる。
    """

    external_item_code: str
    external_genre_id: str
    period: str
    ranking_snapshot_id: str
    rank: int
    cursor_type: str = "ranking_supplement"


@dataclass
class RankingSyncResult:
    """Finalize-phase summary for BATCH-002."""

    batch_id: str
    job_run_id: str
    status: RankingSyncRunStatus
    planned_genre_ids: tuple[str, ...] = ()
    period: str = ""
    succeeded_genre_ids: list[str] = field(default_factory=list)
    failed_genre_ids: list[str] = field(default_factory=list)
    completed_phases: list[str] = field(default_factory=list)
    snapshot_count: int = 0
    popularity_signal_upsert_count: int = 0
    unknown_item_count: int = 0
    error_codes: list[str] = field(default_factory=list)
