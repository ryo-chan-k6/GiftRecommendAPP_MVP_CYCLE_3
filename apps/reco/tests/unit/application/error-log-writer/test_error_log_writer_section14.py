"""MOD-RECO-029 §14 unit test coverage (module spec No.1–9).

| §14 No | 観点 | テスト関数 |
| -----: | ---- | ---------- |
| 1 | Port 契約 | `test_write_accepts_error_log_write_request` |
| 2 | §9 マッピング | `test_section9_maps_all_request_columns_to_record` |
| 3 | 表面 code | `test_surface_error_code_preserved_on_insert` |
| 4 | detail JSON | `test_error_detail_json_preserves_detail_error_code` |
| 5 | occurred_at | `test_occurred_at_set_at_insert_time` |
| 6 | owner 検証 | `test_unknown_owner_type_raises_validation_error` |
| 7 | INSERT 失敗 | `test_repository_failure_propagates_to_caller`, `test_reco_error_handler_returns_despite_insert_failure` |
| 8 | InMemory | `test_in_memory_repository_runs_without_external_db` |
| 9 | 024 連携 | `test_reco_error_handler_delegates_write_via_explicit_di` |
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from conftest import (
    build_error_handler_with_writer,
    build_writer,
    sample_context,
    sample_write_request,
)
from reco.application.error_log_writer import ErrorLogValidationError
from reco.application.error_log_writer.mapper import map_write_request_to_record
from reco.application.error_log_writer.repository import InMemoryErrorLogRepository
from reco.application.reco_error_handler.models import ErrorLogWriteRequest


def test_write_accepts_error_log_write_request() -> None:
    """§14 No.1: ErrorLogWriterPort.write() accepts ErrorLogWriteRequest."""
    writer, repo = build_writer()
    request = sample_write_request()

    assert isinstance(request, ErrorLogWriteRequest)
    writer.write(request)

    assert len(repo.records) == 1


def test_section9_maps_all_request_columns_to_record() -> None:
    """§14 No.2: §9 columns map from request to persisted record."""
    fixed_time = datetime(2026, 7, 6, 6, 30, 0, tzinfo=UTC)
    request = sample_write_request(
        trace_id="trace-section9",
        request_id="req-section9",
        owner_type="recommendation_run",
        owner_id="660e8400-e29b-41d4-a716-446655440001",
        service="reco",
        error_code="GRS-REC-011",
        error_message="matching failed",
        severity="critical",
        retryable=True,
        error_detail_json={
            "source_module_id": "MOD-RECO-015",
            "phase_name": "matching",
            "detail_error_code": "GRS-REC-010",
            "extra_context": {"attempt": 1},
        },
    )

    record = map_write_request_to_record(request, occurred_at=fixed_time)

    assert record.trace_id == "trace-section9"
    assert record.request_id == "req-section9"
    assert record.owner_type == "recommendation_run"
    assert record.owner_id == "660e8400-e29b-41d4-a716-446655440001"
    assert record.service == "reco"
    assert record.error_code == "GRS-REC-011"
    assert record.error_message == "matching failed"
    assert record.severity == "critical"
    assert record.retryable is True
    assert record.error_detail_json == {
        "source_module_id": "MOD-RECO-015",
        "phase_name": "matching",
        "detail_error_code": "GRS-REC-010",
        "extra_context": {"attempt": 1},
    }
    assert record.occurred_at == fixed_time

    writer, repo = build_writer()
    writer.write(request)
    persisted = repo.records[0]
    assert persisted.trace_id == request.trace_id
    assert persisted.request_id == request.request_id
    assert persisted.owner_type == request.owner_type
    assert persisted.owner_id == request.owner_id
    assert persisted.service == request.service
    assert persisted.error_code == request.error_code
    assert persisted.error_message == request.error_message
    assert persisted.severity == request.severity
    assert persisted.retryable == request.retryable
    assert persisted.error_detail_json == request.error_detail_json
    assert persisted.occurred_at.tzinfo is not None


def test_surface_error_code_preserved_on_insert() -> None:
    """§14 No.3: surface GRS-REC-* code is stored unchanged."""
    writer, repo = build_writer()
    request = sample_write_request(error_code="GRS-REC-099")

    writer.write(request)

    assert repo.records[0].error_code == "GRS-REC-099"


def test_error_detail_json_preserves_detail_error_code() -> None:
    """§14 No.4: error_detail_json.detail_error_code is preserved."""
    writer, repo = build_writer()
    request = sample_write_request(
        error_detail_json={
            "source_module_id": "MOD-RECO-017",
            "phase_name": "ranking",
            "detail_error_code": "GRS-DB-002",
        }
    )

    writer.write(request)

    detail = repo.records[0].error_detail_json
    assert detail["detail_error_code"] == "GRS-DB-002"
    assert detail["source_module_id"] == "MOD-RECO-017"
    assert detail["phase_name"] == "ranking"


@patch("reco.application.error_log_writer.mapper.datetime")
def test_occurred_at_set_at_insert_time(mock_datetime) -> None:
    """§14 No.5: occurred_at is set when INSERT runs."""
    fixed_now = datetime(2026, 7, 6, 12, 0, 0, tzinfo=UTC)
    mock_datetime.now.return_value = fixed_now

    writer, repo = build_writer()
    writer.write(sample_write_request())

    assert repo.records[0].occurred_at == fixed_now
    mock_datetime.now.assert_called_once_with(UTC)


def test_unknown_owner_type_raises_validation_error() -> None:
    """§14 No.6: unknown owner_type raises validation error."""
    writer, repo = build_writer()
    request = sample_write_request(owner_type="unknown_owner")

    with pytest.raises(ErrorLogValidationError, match="unsupported owner_type"):
        writer.write(request)

    assert repo.records == []


def test_system_owner_allows_null_owner_id() -> None:
    """§11.1: system owner_type requires null owner_id."""
    writer, repo = build_writer()
    request = sample_write_request(owner_type="system", owner_id=None)

    writer.write(request)

    assert len(repo.records) == 1
    assert repo.records[0].owner_type == "system"
    assert repo.records[0].owner_id is None


def test_repository_failure_propagates_to_caller() -> None:
    """§14 No.7: repository INSERT failure propagates to write() caller."""
    repo = InMemoryErrorLogRepository(should_fail_on_insert=True)
    writer, _ = build_writer(repository=repo)

    with pytest.raises(RuntimeError, match="error_log insert failed"):
        writer.write(sample_write_request())


def test_reco_error_handler_returns_despite_insert_failure() -> None:
    """§14 No.7: 024 receives the exception and still returns RecoError."""
    repo = InMemoryErrorLogRepository(should_fail_on_insert=True)
    handler, _ = build_error_handler_with_writer(repository=repo)
    context = sample_context()

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="db write failed",
        phase_name="ranking",
    )

    assert reco_error.error_code == "GRS-REC-012"
    assert repo.records == []


def test_in_memory_repository_runs_without_external_db() -> None:
    """§14 No.8: InMemory repository enables pytest without production DB."""
    repo = InMemoryErrorLogRepository()
    writer = build_writer(repository=repo)[0]

    writer.write(sample_write_request())
    writer.write(sample_write_request(error_code="GRS-REC-011", owner_id="770e8400-e29b-41d4-a716-446655440002"))

    assert len(repo.records) == 2
    assert {record.error_code for record in repo.records} == {"GRS-REC-012", "GRS-REC-011"}


def test_reco_error_handler_delegates_write_via_explicit_di() -> None:
    """§14 No.9: 024 handle() delegates to ErrorLogWriter via explicit DI."""
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
    record = repo.records[0]
    assert record.error_code == "GRS-REC-012"
    assert record.trace_id == context.trace_id
    assert record.request_id == context.recommendation_request.request_id
    assert record.error_detail_json.get("detail_error_code") == "GRS-DB-001"
    assert record.error_detail_json.get("source_module_id") == "MOD-RECO-017"
    assert record.error_detail_json.get("phase_name") == "ranking"
