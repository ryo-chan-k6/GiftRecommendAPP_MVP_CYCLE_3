"""External AI client scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ExternalAiResponse:
    """External AI completion placeholder."""

    text: str
    model: str


class ExternalAiClient(Protocol):
    """External AI API boundary for embeddings and LLM calls (Phase4a protocol)."""

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse: ...


@dataclass
class ScaffoldExternalAiClient:
    """Phase4a placeholder client without outbound API calls."""

    model: str = "scaffold"
    generate_calls: list[dict[str, str]] = field(default_factory=list)

    def generate(self, prompt: str, *, purpose: str) -> ExternalAiResponse:
        self.generate_calls.append({"prompt": prompt, "purpose": purpose})
        return ExternalAiResponse(
            text=f"[scaffold:{purpose}]",
            model=self.model,
        )
