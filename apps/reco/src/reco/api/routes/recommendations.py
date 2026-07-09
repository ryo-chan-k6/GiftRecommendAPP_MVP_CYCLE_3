"""POST /internal/reco/v1/recommendations/run route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from reco.api.auth.internal_api_key import require_internal_api_key
from reco.api.dependencies import OrchestratorDep
from reco.api.errors import reco_error_from_code
from reco.api.exception_handlers.reco_errors import map_reco_error
from reco.api.mappers.request_mapper import to_domain_recommendation_request
from reco.api.mappers.response_mapper import to_success_response
from reco.api.middleware.trace_context import TraceContext, require_json_headers, require_trace_context
from reco.api.schemas.recommendations import RecoRecommendationRunRequest

router = APIRouter(prefix="/internal/reco/v1", tags=["RecoRecommendations"])


@router.post(
    "/recommendations/run",
    response_model=None,
    summary="Reco推薦実行（API-INT-002）",
)
async def run_recommendation(
    request: Request,
    body: RecoRecommendationRunRequest,
    orchestrator: OrchestratorDep,
    _auth: None = Depends(require_internal_api_key),
    trace: TraceContext = Depends(require_trace_context),
) -> JSONResponse:
    require_json_headers(request)
    domain_request = to_domain_recommendation_request(body)
    outcome = orchestrator.run(
        domain_request,
        trace_id=trace.trace_id,
        caller_context={"request_id": trace.request_id},
    )

    if not outcome.success or outcome.recommendation_result is None:
        if outcome.reco_error is None:
            raise reco_error_from_code("GRS-REC-999")
        raise map_reco_error(outcome.reco_error)

    execution_context = outcome.execution_context
    if execution_context is None:
        raise reco_error_from_code("GRS-REC-999")

    response = to_success_response(
        result=outcome.recommendation_result,
        context=execution_context,
        trace=trace,
    )
    return JSONResponse(
        status_code=200,
        content=response.model_dump(by_alias=True, exclude_none=True),
    )
