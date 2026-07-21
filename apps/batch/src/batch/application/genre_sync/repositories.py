"""In-memory repositories used by BATCH-001 unit tests / scaffold wiring.

Production will replace these with real DB / Object Storage adapters while
keeping the same upsert semantics (source + external_genre_id).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from batch.application.genre_sync.idempotency import SOURCE_API_GENRE, SOURCE_RAKUTEN
from batch.application.genre_sync.models import GenreRow, RawGenreArtifact
from batch.infrastructure.db import DbWriter
from batch.infrastructure.object_storage import ObjectRef, ObjectStorageClient


@dataclass
class GenreSyncRepositories:
    """Facade that persists Raw / Staging / external_genre via infrastructure protocols."""

    object_storage: ObjectStorageClient
    db_writer: DbWriter
    bucket: str
    raw_metadata: dict[str, dict[str, object]] = field(default_factory=dict)
    staging_genres: dict[tuple[str, str], GenreRow] = field(default_factory=dict)
    external_genres: dict[tuple[str, str], GenreRow] = field(default_factory=dict)
    api_call_logs: list[dict[str, object]] = field(default_factory=list)
    error_logs: list[dict[str, object]] = field(default_factory=list)
    phase_logs: list[dict[str, object]] = field(default_factory=list)

    def save_raw(self, artifact: RawGenreArtifact) -> None:
        ref = ObjectRef(bucket=self.bucket, key=artifact.object_key)
        existing_meta = self.raw_metadata.get(artifact.object_key)
        if (
            existing_meta is not None
            and existing_meta.get("content_hash") == artifact.content_hash
            and existing_meta.get("import_status") in {"raw_saved", "staged", "imported"}
        ):
            # Same content_hash: skip Object Storage rewrite (仕様書 §11)
            self.raw_metadata[artifact.object_key] = {
                **existing_meta,
                "import_status": existing_meta.get("import_status", "raw_saved"),
                "api_call_log_id": artifact.api_call_log_id,
                "genre_id": artifact.genre_id,
                "source": SOURCE_RAKUTEN,
                "source_api": SOURCE_API_GENRE,
            }
            return

        self.object_storage.put_object(
            ref,
            body=artifact.body,
            content_type="application/json",
        )
        self.raw_metadata[artifact.object_key] = {
            "object_key": artifact.object_key,
            "content_hash": artifact.content_hash,
            "api_call_log_id": artifact.api_call_log_id,
            "genre_id": artifact.genre_id,
            "source": SOURCE_RAKUTEN,
            "source_api": SOURCE_API_GENRE,
            "import_status": "raw_saved",
        }
        self.db_writer.write_rows(
            "raw_product_metadata",
            (dict(self.raw_metadata[artifact.object_key]),),
        )

    def upsert_staging(self, row: GenreRow) -> None:
        key = row.idempotency_key
        self.staging_genres[key] = row
        self.db_writer.write_rows(
            "staging_genre",
            (
                {
                    "source": row.source,
                    "external_genre_id": row.external_genre_id,
                    "genre_name": row.genre_name,
                    "parent_external_genre_id": row.parent_external_genre_id,
                    "genre_level": row.genre_level,
                },
            ),
        )

    def upsert_external(self, row: GenreRow) -> None:
        # Idempotency: source + external_genre_id (仕様書 §11)
        key = row.idempotency_key
        self.external_genres[key] = row
        self.db_writer.write_rows(
            "external_genre",
            (
                {
                    "source": row.source,
                    "external_genre_id": row.external_genre_id,
                    "genre_name": row.genre_name,
                    "parent_external_genre_id": row.parent_external_genre_id,
                    "genre_level": row.genre_level,
                },
            ),
        )

    def record_api_call(
        self,
        *,
        api_call_log_id: str,
        genre_id: str,
        status: str,
        error_code: str | None = None,
    ) -> None:
        self.api_call_logs.append(
            {
                "api_call_log_id": api_call_log_id,
                "genre_id": genre_id,
                "status": status,
                "error_code": error_code,
                # Never log Authorization / access keys
            }
        )

    def record_error(self, *, code: str, summary: str, genre_id: str | None = None) -> None:
        self.error_logs.append(
            {
                "code": code,
                "summary": summary,
                "genre_id": genre_id,
            }
        )

    def record_phase(self, *, phase: str, status: str) -> None:
        self.phase_logs.append({"phase": phase, "status": status})
