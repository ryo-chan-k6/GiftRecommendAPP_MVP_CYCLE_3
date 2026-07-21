"""MOD-BATCH-040 Evaluation Metric Calculator.

初版最小セット（§9.1 / §18.1 No.16）:
precision_at_10 / recall_at_10 / ndcg_at_10 / mrr_at_10
"""

from __future__ import annotations

import math
from typing import Iterable

from batch.application.offline_evaluation.models import (
    METRIC_K,
    MVP_METRIC_NAMES,
    MetricScore,
)


def extract_relevant_item_ids(expected_result_json: dict[str, object] | None) -> frozenset[str]:
    """expected_result_json.golden_item_ids を関連集合として抽出する."""

    if not expected_result_json:
        return frozenset()
    raw = expected_result_json.get("golden_item_ids")
    if not isinstance(raw, list):
        return frozenset()
    items: list[str] = []
    for value in raw:
        if isinstance(value, str) and value.strip():
            items.append(value.strip())
    return frozenset(items)


def precision_at_k(
    predicted: Iterable[str], relevant: frozenset[str], *, k: int = METRIC_K
) -> float:
    top = list(predicted)[:k]
    if k <= 0:
        return 0.0
    hits = sum(1 for item in top if item in relevant)
    return hits / float(k)


def recall_at_k(
    predicted: Iterable[str], relevant: frozenset[str], *, k: int = METRIC_K
) -> float:
    if not relevant:
        return 0.0
    top = list(predicted)[:k]
    hits = sum(1 for item in top if item in relevant)
    return hits / float(len(relevant))


def mrr_at_k(
    predicted: Iterable[str], relevant: frozenset[str], *, k: int = METRIC_K
) -> float:
    for rank, item in enumerate(list(predicted)[:k], start=1):
        if item in relevant:
            return 1.0 / float(rank)
    return 0.0


def ndcg_at_k(
    predicted: Iterable[str], relevant: frozenset[str], *, k: int = METRIC_K
) -> float:
    top = list(predicted)[:k]
    dcg = 0.0
    for rank, item in enumerate(top, start=1):
        if item in relevant:
            dcg += 1.0 / math.log2(rank + 1)
    ideal_n = min(len(relevant), k)
    if ideal_n <= 0:
        return 0.0
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_n + 1))
    if idcg <= 0.0:
        return 0.0
    return dcg / idcg


def calculate_mvp_metrics(
    *,
    predicted_item_ids: tuple[str, ...],
    expected_result_json: dict[str, object] | None,
    k: int = METRIC_K,
) -> tuple[MetricScore, ...]:
    """初版 4 種を算出する。expected 欠如時は空タプル（Metric INSERT スキップ）.

    Raises:
        ValueError: 算出不能（GRS-EVAL-004 相当）の場合。
    """

    if expected_result_json is None:
        return ()

    relevant = extract_relevant_item_ids(expected_result_json)
    if not relevant:
        # golden_item_ids なし → Metric スキップ（仕様 §9.2 許容）
        return ()

    try:
        scores = (
            MetricScore(
                metric_name="precision_at_10",
                metric_value=precision_at_k(predicted_item_ids, relevant, k=k),
                metric_detail_json={
                    "k": k,
                    "predicted_count": len(predicted_item_ids[:k]),
                    "relevant_count": len(relevant),
                },
            ),
            MetricScore(
                metric_name="recall_at_10",
                metric_value=recall_at_k(predicted_item_ids, relevant, k=k),
                metric_detail_json={"k": k, "relevant_count": len(relevant)},
            ),
            MetricScore(
                metric_name="ndcg_at_10",
                metric_value=ndcg_at_k(predicted_item_ids, relevant, k=k),
                metric_detail_json={"k": k},
            ),
            MetricScore(
                metric_name="mrr_at_10",
                metric_value=mrr_at_k(predicted_item_ids, relevant, k=k),
                metric_detail_json={"k": k},
            ),
        )
    except Exception as exc:  # noqa: BLE001 — GRS-EVAL-004 境界
        raise ValueError(f"metric calculation failed: {exc}") from exc

    names = tuple(s.metric_name for s in scores)
    if names != MVP_METRIC_NAMES:
        raise ValueError(f"unexpected metric set: {names}")
    return scores
