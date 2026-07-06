"""MOD-RECO-029 Error Log Writer smoke tests (implementation Task)."""

from __future__ import annotations

import pytest
from conftest import (
    build_error_handler_with_writer,
    build_writer,
    sample_context,
    sample_write_request,
)
from reco.application.error_log_writer import ErrorLogValidationError
from reco.application.error_log_writer.repository import InMemoryErrorLogRepository


def test_write_inserts_error_log_record() -> None:
    writer, repo = build_writer()
    request = sample_write_request()

    writer.write(request)

    assert len(repo.records) == 1
    record = repo.records[0]
    assert record.error_code == "GRS-REC-012"
    assert record.owner_type == "recommendation_run"
    assert record.service == "reco"
    assert record.error_detail_json["detail_error_code"] == "GRS-DB-001"
    assert record.occurred_at.tzinfo is not None


def test_write_rejects_invalid_error_code() -> None:
    writer, repo = build_writer()
    request = sample_write_request(error_code="INVALID")

    with pytest.raises(ErrorLogValidationError):
        writer.write(request)

    assert repo.records == []


def test_write_rejects_system_owner_with_owner_id() -> None:
    writer, repo = build_writer()
    request = sample_write_request(
        owner_type="system",
        owner_id="550e8400-e29b-41d4-a716-446655440000",
    )

    with pytest.raises(ErrorLogValidationError):
        writer.write(request)

    assert repo.records == []


def test_write_propagates_repository_failure() -> None:
    repo = InMemoryErrorLogRepository(should_fail_on_insert=True)
    writer, _ = build_writer(repository=repo)

    with pytest.raises(RuntimeError, match="error_log insert failed"):
        writer.write(sample_write_request())


def test_reco_error_handler_delegates_to_error_log_writer() -> None:
    handler, repo = build_error_handler_with_writer()
    context = sample_context()

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="db write failed",
        phase_name="ranking",
    )

    assert reco_error.error_code == "GRS-REC-012"
    assert len(repo.records) == 1
    assert repo.records[0].error_code == "GRS-REC-012"
    assert repo.records[0].error_detail_json.get("detail_error_code") == "GRS-DB-001"
