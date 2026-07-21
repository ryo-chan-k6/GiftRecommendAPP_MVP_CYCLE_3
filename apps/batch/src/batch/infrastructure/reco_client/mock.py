"""IF-SHARED-004 mock 実装（外部 HTTP なし）.

MVP scaffold: Case の golden_item_ids を予測リストとして返し、
recommendation_result_id は決定論的 stub を付与する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid5, UUID

# 名前空間（secret ではない固定 UUID。決定論的 result id 用）
_MOCK_RESULT_NS = UUID("01800000-0000-7000-8000-000000000018")


@dataclass(frozen=True)
class RecoEvaluationRequest:
    """IF-SHARED-004 入力（evaluation mode）。"""

    evaluation_case_id: str
    evaluation_run_id: str
    input_condition_json: dict[str, object] | None = None
    expected_result_json: dict[str, object] | None = None
    mode: str = "evaluation"


@dataclass(frozen=True)
class RecoEvaluationResponse:
    """IF-SHARED-004 応答（成功時）。"""

    recommendation_result_id: str
    predicted_item_ids: tuple[str, ...]
    ok: bool = True
    error_code: str | None = None
    error_summary: str | None = None


class RecoEvaluationClient(Protocol):
    """IF-SHARED-004 抽象。"""

    def evaluate(self, request: RecoEvaluationRequest) -> RecoEvaluationResponse: ...


def _extract_golden_item_ids(expected: dict[str, object] | None) -> tuple[str, ...]:
    if not expected:
        return ()
    raw = expected.get("golden_item_ids")
    if not isinstance(raw, list):
        return ()
    items: list[str] = []
    for value in raw:
        if isinstance(value, str) and value.strip():
            items.append(value.strip())
    return tuple(items)


class MockRecoEvaluationClient:
    """scaffold mock。HTTP / network を一切使わない。"""

    def __init__(
        self,
        *,
        predicted_override: dict[str, tuple[str, ...]] | None = None,
        fail_case_ids: frozenset[str] | None = None,
    ) -> None:
        self._predicted_override = predicted_override or {}
        self._fail_case_ids = fail_case_ids or frozenset()
        self.call_count: int = 0
        self.last_request: RecoEvaluationRequest | None = None

    def evaluate(self, request: RecoEvaluationRequest) -> RecoEvaluationResponse:
        self.call_count += 1
        self.last_request = request

        if request.mode != "evaluation":
            return RecoEvaluationResponse(
                recommendation_result_id="",
                predicted_item_ids=(),
                ok=False,
                error_code="GRS-REC-001",
                error_summary=f"unsupported mode: {request.mode!r}",
            )

        if request.evaluation_case_id in self._fail_case_ids:
            return RecoEvaluationResponse(
                recommendation_result_id="",
                predicted_item_ids=(),
                ok=False,
                error_code="GRS-REC-002",
                error_summary="mock reco failure",
            )

        if request.evaluation_case_id in self._predicted_override:
            predicted = self._predicted_override[request.evaluation_case_id]
        else:
            predicted = _extract_golden_item_ids(request.expected_result_json)

        result_id = str(uuid5(_MOCK_RESULT_NS, request.evaluation_case_id))
        return RecoEvaluationResponse(
            recommendation_result_id=result_id,
            predicted_item_ids=predicted,
            ok=True,
        )
