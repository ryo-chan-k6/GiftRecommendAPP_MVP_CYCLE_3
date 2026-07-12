"""MOD-RECO-024 Reco Error Handler smoke tests (implementation Task)."""

from __future__ import annotations

from conftest import (
    DEFAULT_REQUEST_ID,
    DEFAULT_RUN_ID,
    DEFAULT_TRACE_ID,
    PreHardFilterError,
    RetrievalError,
    _sample_context,
    build_error_handler,
)
from reco.application.reco_error_handler import (
    SURFACE_ERROR_CODE_CONFIG,
    SURFACE_ERROR_CODE_UNKNOWN,
)
from reco.application.reco_error_handler.executor import NoOpErrorLogWriter


def test_handle_maps_cfg_detail_code_to_surface_rec_003() -> None:
    context = _sample_context()
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-003",
        error_code="GRS-CFG-002",
        message="config resolution failed",
        phase_name="config_resolved",
    )

    assert reco_error.error_code == SURFACE_ERROR_CODE_CONFIG
    assert writer.requests[0].error_code == SURFACE_ERROR_CODE_CONFIG
    assert writer.requests[0].error_detail_json["detail_error_code"] == "GRS-CFG-002"
    assert context.error_log_events[0]["error_code"] == SURFACE_ERROR_CODE_CONFIG


def test_handle_prefers_reco_domain_error_surface_code() -> None:
    context = _sample_context()
    handler = build_error_handler()

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-012",
        error_code="GRS-REC-009",
        message="pre hard filter failed",
        phase_name="pre_hard_filter",
        cause=PreHardFilterError("filter failed"),
    )

    assert reco_error.error_code == "GRS-REC-008"


def test_handle_prefers_retrieval_error_surface_code() -> None:
    context = _sample_context()
    handler = build_error_handler()

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-012",
        error_code="GRS-REC-008",
        message="retrieval failed",
        phase_name="retrieval",
        cause=RetrievalError("vector search failed"),
    )

    assert reco_error.error_code == "GRS-REC-009"


def test_handle_masks_authorization_in_message() -> None:
    context = _sample_context()
    handler = build_error_handler()

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-010",
        error_code="GRS-REC-007",
        message="upstream failed Authorization: Bearer secret-token-value",
        phase_name="query_embedding_generated",
    )

    assert "***REDACTED***" in reco_error.message
    assert "secret-token-value" not in reco_error.message


def test_handle_returns_999_for_invalid_input() -> None:
    context = _sample_context()
    handler = build_error_handler()

    reco_error = handler.handle(
        context,
        module_id="",
        error_code="GRS-REC-011",
        message="",
    )

    assert reco_error.error_code == SURFACE_ERROR_CODE_UNKNOWN


def test_handle_continues_when_error_log_writer_fails() -> None:
    context = _sample_context()

    class FailingWriter(NoOpErrorLogWriter):
        def write(self, request: object) -> None:
            raise RuntimeError("db unavailable")

    handler = build_error_handler(error_log_writer=FailingWriter())

    reco_error = handler.handle(
        context,
        module_id="MOD-RECO-014",
        error_code="GRS-REC-011",
        message="matching failed",
        phase_name="feature_matched",
    )

    assert reco_error.error_code == "GRS-REC-011"
    assert context.error_log_events == []


def test_handle_builds_owner_from_run_id() -> None:
    context = _sample_context(include_run=True)
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-REC-012",
        message="ranking failed",
    )

    request = writer.requests[0]
    assert request.owner_type == "recommendation_run"
    assert request.owner_id == DEFAULT_RUN_ID
    assert request.request_id == DEFAULT_REQUEST_ID
    assert request.trace_id == DEFAULT_TRACE_ID
    assert request.service == "reco"


def test_handle_falls_back_to_request_owner_without_run() -> None:
    context = _sample_context(include_run=False)
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-REC-012",
        message="ranking failed",
    )

    request = writer.requests[0]
    assert request.owner_type == "recommendation_request"
    assert request.owner_id == DEFAULT_REQUEST_ID
