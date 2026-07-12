"""MOD-RECO-024 §14 unit test coverage (module spec No.1–9, 11, 12).

| §14 No | 観点 | テスト関数 |
| -----: | ---- | ---------- |
| 1 | Port 契約 | `test_handle_port_contract_returns_reco_error` |
| 2 | Domain error 優先 | `test_pre_hard_filter_domain_error_surface_preserved`, `test_retrieval_domain_error_surface_preserved` |
| 3 | CFG 集約 | `test_cfg_detail_code_maps_to_rec_003` |
| 4 | LLM 集約 | `test_llm_detail_code_maps_for_user_meaning_module` |
| 5 | fallback 映射 | `test_plain_exception_uses_module_surface_mapping` |
| 6 | 029 Port 委譲 | `test_delegates_to_error_log_writer_and_survives_insert_failure` |
| 7 | Error Log 項目 | `test_error_log_request_uses_surface_code_and_detail_json` |
| 8 | マスキング | `test_message_masking_strips_secrets` |
| 9 | 999 fallback | `test_unknown_module_returns_rec_999` |
| 10 | Orchestrator 連携 | out of scope（Wiring 後 integration） |
| 11 | REC-001 除外 | `test_rec_001_surface_passes_through_unchanged` |
| 12 | 内部失敗 | `test_internal_failure_returns_999_without_propagating` |
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from conftest import (
    PreHardFilterError,
    RetrievalError,
    RecoError,
    _sample_context,
    build_error_handler,
    build_error_handler_with_writer,
)
from reco.application.error_log_writer.repository import InMemoryErrorLogRepository
from reco.application.reco_error_handler import SURFACE_ERROR_CODE_CONFIG, SURFACE_ERROR_CODE_UNKNOWN
from reco.application.reco_error_handler.executor import NoOpErrorLogWriter


def test_handle_port_contract_returns_reco_error() -> None:
    """§14 No.1: handle() returns RecoError matching §6 contract."""
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="ranking failed",
        phase_name="ranking",
        cause=RuntimeError("db timeout"),
    )

    assert isinstance(result, RecoError)
    assert result.error_code == "GRS-REC-012"
    assert result.module_id == "MOD-RECO-017"
    assert result.phase_name == "ranking"
    assert result.message == "ranking failed"


def test_pre_hard_filter_domain_error_surface_preserved() -> None:
    """§14 No.2: PreHardFilterError surface is not overwritten."""
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-012",
        error_code="GRS-REC-009",
        message="pre hard filter failed",
        phase_name="pre_hard_filter",
        cause=PreHardFilterError("filter failed"),
    )

    assert result.error_code == "GRS-REC-008"


def test_retrieval_domain_error_surface_preserved() -> None:
    """§14 No.2: RetrievalError surface is not overwritten."""
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-012",
        error_code="GRS-REC-008",
        message="retrieval failed",
        phase_name="retrieval",
        cause=RetrievalError("vector search failed"),
    )

    assert result.error_code == "GRS-REC-009"


def test_cfg_detail_code_maps_to_rec_003() -> None:
    """§14 No.3: GRS-CFG-002 aggregates to GRS-REC-003."""
    context = _sample_context()
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    result = handler.handle(
        context,
        module_id="MOD-RECO-003",
        error_code="GRS-CFG-002",
        message="config resolution failed",
        phase_name="config_resolved",
    )

    assert result.error_code == SURFACE_ERROR_CODE_CONFIG
    assert writer.requests[0].error_code == SURFACE_ERROR_CODE_CONFIG
    assert writer.requests[0].error_detail_json["detail_error_code"] == "GRS-CFG-002"


def test_llm_detail_code_maps_for_user_meaning_module() -> None:
    """§14 No.4: User Meaning phase GRS-LLM-103 maps to GRS-REC-007."""
    context = _sample_context()
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    result = handler.handle(
        context,
        module_id="MOD-RECO-010",
        error_code="GRS-LLM-103",
        message="embedding generation failed",
        phase_name="query_embedding_generated",
    )

    assert result.error_code == "GRS-REC-007"
    assert writer.requests[0].error_detail_json["detail_error_code"] == "GRS-LLM-103"


def test_plain_exception_uses_module_surface_mapping() -> None:
    """§14 No.5: plain Exception triggers MODULE_SURFACE_ERROR_CODES fallback."""
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-014",
        error_code="",
        message="matching failed",
        phase_name="feature_matched",
        cause=RuntimeError("unexpected"),
    )

    assert result.error_code == "GRS-REC-011"


def test_delegates_to_error_log_writer_and_survives_insert_failure() -> None:
    """§14 No.6: ErrorLogWriterPort.write() is invoked; 029 failure does not block RecoError."""
    repo = InMemoryErrorLogRepository(should_fail_on_insert=True)
    handler, _ = build_error_handler_with_writer(repository=repo)
    context = _sample_context()

    result = handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="ranking failed",
        phase_name="ranking",
    )

    assert result.error_code == "GRS-REC-012"
    assert repo.records == []

    repo_ok = InMemoryErrorLogRepository()
    handler_ok, repo_ok_ref = build_error_handler_with_writer(repository=repo_ok)
    handler_ok.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="ranking failed",
        phase_name="ranking",
    )
    assert len(repo_ok_ref.records) == 1


def test_error_log_request_uses_surface_code_and_detail_json() -> None:
    """§14 No.7: surface code is error_log.error_code; detail is error_detail_json."""
    context = _sample_context()
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="ranking failed",
        phase_name="ranking",
    )

    request = writer.requests[0]
    assert request.error_code == "GRS-REC-012"
    assert request.error_detail_json["detail_error_code"] == "GRS-DB-001"
    assert request.error_detail_json["source_module_id"] == "MOD-RECO-017"
    assert request.error_detail_json["phase_name"] == "ranking"


def test_message_masking_strips_secrets() -> None:
    """§14 No.8: masked message must not contain secret literals."""
    context = _sample_context()
    handler = build_error_handler()
    secret = "super-secret-api-key-value"

    result = handler.handle(
        context,
        module_id="MOD-RECO-010",
        error_code="GRS-REC-007",
        message=f"upstream failed Authorization: Bearer {secret}",
        phase_name="query_embedding_generated",
    )

    assert secret not in result.message
    assert "***REDACTED***" in result.message


def test_unknown_module_returns_rec_999() -> None:
    """§14 No.9: unclassifiable input resolves to GRS-REC-999."""
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-UNKNOWN",
        error_code="UNCLASSIFIED",
        message="unexpected failure",
    )

    assert result.error_code == SURFACE_ERROR_CODE_UNKNOWN


def test_rec_001_surface_passes_through_unchanged() -> None:
    """§14 No.11: GRS-REC-001 is not remapped to fatal unknown codes."""
    context = _sample_context()
    writer = NoOpErrorLogWriter()
    handler = build_error_handler(error_log_writer=writer)

    result = handler.handle(
        context,
        module_id="MOD-RECO-012",
        error_code="GRS-REC-001",
        message="no candidates found",
        phase_name="retrieval",
    )

    assert result.error_code == "GRS-REC-001"
    assert writer.requests[0].error_code == "GRS-REC-001"


@patch("reco.application.reco_error_handler.executor.build_error_log_write_request")
def test_internal_failure_returns_999_without_propagating(mock_build) -> None:
    """§14 No.12: internal handler failure returns GRS-REC-999 without re-raising."""
    mock_build.side_effect = RuntimeError("builder exploded")
    context = _sample_context()
    handler = build_error_handler()

    result = handler.handle(
        context,
        module_id="MOD-RECO-017",
        error_code="GRS-DB-001",
        message="ranking failed",
        phase_name="ranking",
    )

    assert result.error_code == SURFACE_ERROR_CODE_UNKNOWN
    assert result.message == "Reco Error Handler internal failure"
