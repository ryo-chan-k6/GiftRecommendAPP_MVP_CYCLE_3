"""Collector phase scaffold."""

from __future__ import annotations

from batch.application.context import BatchJobContext
from batch.infrastructure.rakuten import RakutenApiClient, ScaffoldRakutenApiClient


class CollectorStep:
    """Phase4a scaffold: fetch placeholder records via infrastructure boundary."""

    phase = "collector"

    def __init__(self, rakuten_client: RakutenApiClient | None = None) -> None:
        self._rakuten_client = rakuten_client or ScaffoldRakutenApiClient()

    def execute(self, context: BatchJobContext) -> BatchJobContext:
        items = self._rakuten_client.search_items(keyword="gift", page=1)
        context.collected_records = [
            {"item_code": item.item_code, "item_name": item.item_name} for item in items
        ]
        context.completed_phases.append(self.phase)
        return context
