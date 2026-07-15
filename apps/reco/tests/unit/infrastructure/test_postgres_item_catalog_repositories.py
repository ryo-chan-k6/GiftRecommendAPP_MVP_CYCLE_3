"""Unit tests for Postgres item catalog repositories."""

from __future__ import annotations

from reco.application.candidate_retriever.models import (
    FilterPredicate,
    MergedFilterConditions,
)
from reco.infrastructure.db.repositories.postgres_item_feature_repository import (
    PostgresFeatureNormalizationRepository,
    PostgresItemFeatureRepository,
)
from reco.infrastructure.db.repositories.postgres_item_repository import (
    PostgresItemRepository,
)
from reco.infrastructure.db.repositories.postgres_item_snapshot_repository import (
    PostgresItemSnapshotReadRepository,
)
from reco.infrastructure.db.repositories.postgres_post_filter_item_repository import (
    PostgresPostFilterItemRepository,
)
from unit.infrastructure.db.helpers import ScriptedDatabaseSession


def test_item_repository_count_and_search() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [{"cnt": 3}],
            [{"cnt": 2}],
            [
                {
                    "item_id": "b1111111-1111-4111-8111-111111111001",
                    "similarity_score": 0.91,
                },
            ],
        ],
    )
    repo = PostgresItemRepository(session=session)
    assert repo.count_active_items() == 3
    predicate = FilterPredicate(
        merged_filter_conditions=MergedFilterConditions(budget_min=3000, budget_max=5000),
        active_only=True,
        data_quality_rules={"require_image": True, "require_url": True},
    )
    assert repo.count_filtered_items(predicate) == 2
    hits = repo.search_vector_candidates(
        predicate,
        query_vector=(0.1, 0.2),
        model_version_id="model-1",
        limit=10,
    )
    assert len(hits) == 1
    assert hits[0].item_id.endswith("001")
    assert hits[0].similarity_score == 0.91


def test_post_filter_item_repository_maps_rows() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "item_id": "item-1",
                    "name": "ギフト",
                    "price": 4000,
                    "is_active": True,
                    "active_status": "active",
                    "has_image": True,
                },
            ],
            [
                {
                    "item_id": "item-1",
                    "semantic_config_version_id": "sem-1",
                    "semantic_json": {
                        "concepts": [{"concept_code": "formal_refined", "confidence": 0.8}],
                    },
                },
            ],
        ],
    )
    repo = PostgresPostFilterItemRepository(session=session)
    items = repo.fetch_items_for_validation(("item-1",))
    assert items["item-1"].name == "ギフト"
    semantics = repo.fetch_item_semantics(("item-1",))
    assert semantics["item-1"].concepts[0].concept_code == "formal_refined"


def test_item_feature_and_normalization_repositories() -> None:
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "item_id": "item-1",
                    "feature_code": "formality",
                    "normalized_feature_value": 0.85,
                },
            ],
            [
                {
                    "normalization_method": "sigmoid",
                    "parameter_json": {"center_feature": 0.5, "k_feature": 4.0},
                },
            ],
        ],
    )
    features = PostgresItemFeatureRepository(session=session).fetch_item_features(
        ("item-1",),
        "sem-1",
    )
    assert features["item-1"]["formality"] == 0.85
    params = PostgresFeatureNormalizationRepository(session=session).get_parameters(
        "norm-1",
    )
    assert params is not None
    assert params.center_feature == 0.5


def test_item_snapshot_read_repository_maps_rows() -> None:
    item_id = "b1111111-1111-4111-8111-111111111001"
    session = ScriptedDatabaseSession(
        scripted_query_results=[
            [
                {
                    "item_id": item_id,
                    "item_name": "テストギフト",
                    "price": 4500,
                    "item_url": "https://example.com/item",
                    "catchcopy": "贈る喜び",
                    "shop_code": "shop-001",
                },
            ],
            [
                {
                    "item_id": item_id,
                    "image_url": "https://example.com/image.jpg",
                },
            ],
            [
                {
                    "item_id": item_id,
                    "review_average": 4.5,
                    "review_count": 12,
                },
            ],
        ],
    )
    repo = PostgresItemSnapshotReadRepository(session=session)
    items = repo.fetch_items((item_id,))
    assert items[item_id].item_name == "テストギフト"
    assert items[item_id].price == 4500
    images = repo.fetch_primary_images((item_id,))
    assert images[item_id].image_url.endswith(".jpg")
    reviews = repo.fetch_review_snapshots((item_id,))
    assert reviews[item_id].review_average == 4.5
    assert reviews[item_id].review_count == 12


def test_item_snapshot_read_repository_empty_ids() -> None:
    repo = PostgresItemSnapshotReadRepository(session=ScriptedDatabaseSession())
    assert repo.fetch_items(()) == {}
    assert repo.fetch_primary_images(()) == {}
    assert repo.fetch_review_snapshots(()) == {}
