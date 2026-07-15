"""request_mapper: NgCondition ngKeywords / ngCategories の domain マップ（レーン1f）。"""

from __future__ import annotations

from reco.api.mappers.request_mapper import to_domain_recommendation_request
from reco.api.schemas.recommendations import RecoRecommendationRunRequest


def test_to_domain_maps_ng_keywords_and_categories() -> None:
    body = RecoRecommendationRunRequest.model_validate(
        {
            "recommendationRequestId": "req-ng-1",
            "recommendationRequest": {
                "relationship": {"relationshipCode": "boss"},
                "occasion": {"occasionCode": "thanks"},
                "ngCondition": {
                    "ngText": "アルコールはNG",
                    "ngKeywords": ["アルコール", " ワイン "],
                    "ngCategories": ["alcohol"],
                },
                "execution": {"mode": "ui"},
            },
        },
    )

    domain = to_domain_recommendation_request(body)
    assert domain.ng_condition is not None
    assert domain.ng_condition.ng_text == "アルコールはNG"
    assert domain.ng_condition.ng_keywords == ("アルコール", "ワイン")
    assert domain.ng_condition.ng_categories == ("alcohol",)
