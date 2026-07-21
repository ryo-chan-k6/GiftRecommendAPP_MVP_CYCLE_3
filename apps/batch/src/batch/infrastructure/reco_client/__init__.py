"""IF-SHARED-004 Offline Evaluation 推薦実行 client（scaffold = mock）.

実 HTTP / 実 reco は呼ばない。後続で HTTP / in-process 実装を追加可能。
"""

from batch.infrastructure.reco_client.mock import (
    MockRecoEvaluationClient,
    RecoEvaluationClient,
    RecoEvaluationRequest,
    RecoEvaluationResponse,
)

__all__ = [
    "MockRecoEvaluationClient",
    "RecoEvaluationClient",
    "RecoEvaluationRequest",
    "RecoEvaluationResponse",
]
