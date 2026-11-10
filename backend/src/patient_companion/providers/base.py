"""Provider protocols.

The pipeline never touches vendor SDKs directly — it asks for an
``LLMProvider`` / ``EmbeddingProvider`` from ``providers.get_*``. That is
what lets the mock provider run the entire pipeline in CI with no keys.
"""

from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    """Structured-output-first LLM interface.

    ``complete_tool`` forces a named tool call, so the model *must* return
    data matching ``input_schema`` — this is what makes the staged-card
    output structurally incapable of being malformed.
    """

    def complete_tool(
        self,
        *,
        system: str,
        user: str,
        tool_name: str,
        tool_description: str,
        input_schema: dict[str, Any],
        model: str,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        """Return the parsed tool-input dict from a forced tool call."""
        ...

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
    ) -> str:
        """Plain-text completion (used sparingly; prefer complete_tool)."""
        ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """One embedding vector per input text."""
        ...
