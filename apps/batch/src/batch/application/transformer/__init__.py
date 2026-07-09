"""Transformer phase scaffold."""

from __future__ import annotations

from batch.application.context import BatchJobContext


class TransformerStep:
    """Phase4a scaffold: map collected records into staging-shaped payloads."""

    phase = "transformer"

    def execute(self, context: BatchJobContext) -> BatchJobContext:
        source = context.collected_records or ()
        context.transformed_records = [
            {
                "item_code": record.get("item_code"),
                "normalized_name": record.get("item_name"),
                "source_phase": self.phase,
            }
            for record in source
        ]
        context.completed_phases.append(self.phase)
        return context
