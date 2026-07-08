"""MOD-RECO-023 Reason Generator executor unit tests (module spec §14 unit)."""

from __future__ import annotations

import json

from conftest import (
    DEFAULT_ITEM_ID,
    _sample_context,
    build_reason_generator,
)
from reco.application.reason_generator import MODULE_ID, PHASE_NAME
from reco.infrastructure.logger.logger import ScaffoldRecoLogger

_EXPECTED_LOG_ATTRIBUTE_KEYS = frozenset(
    {
        "fallback_item_count",
        "module_id",
        "reason_generation_latency_ms",
        "reason_generator_fallback_count",
        "reason_generator_item_count",
        "reason_generator_persisted",
        "reason_generator_success_count",
    },
)


# §14 No.18 ログ
def test_generate_emits_structured_log_with_trace_id_without_reason_basis_json() -> None:
    context = _sample_context(
        run_id="run-mod-reco-023-log",
        trace_id="trace-mod-reco-023-unit",
    )
    logger = ScaffoldRecoLogger()
    generator = build_reason_generator(logger=logger)

    generator.generate(context)

    completion_logs = [record for record in logger.records if record.event == PHASE_NAME]
    assert len(completion_logs) == 1
    log_record = completion_logs[0]
    assert log_record.context.trace_id == "trace-mod-reco-023-unit"
    assert log_record.context.run_id == "run-mod-reco-023-log"
    assert log_record.attributes["reason_generator_item_count"] == 1
    assert log_record.attributes["module_id"] == MODULE_ID
    assert set(log_record.attributes) == _EXPECTED_LOG_ATTRIBUTE_KEYS
    assert "reason_basis_json" not in log_record.attributes
    serialized = json.dumps(log_record.attributes, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_generate_records_reason_generator_metrics_in_version_info() -> None:
    context = _sample_context()
    generator = build_reason_generator()

    generator.generate(context)

    version_info = context.recommendation_result.version_info
    assert version_info["reason_generator_item_count"] == "1"
    assert version_info["reason_generator_success_count"] == "1"
    assert version_info["reason_generator_fallback_count"] == "0"
    assert version_info["reason_generator_persisted"] == "true"
    assert int(version_info["reason_generation_latency_ms"]) >= 0
    assert version_info[f"item:{DEFAULT_ITEM_ID}:recommendation_reason_id"]
