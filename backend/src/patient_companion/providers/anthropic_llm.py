"""Anthropic-backed LLMProvider."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

logger = logging.getLogger(__name__)


class AnthropicLLM:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required (or set PC_LLM_PROVIDER=mock)")
        self._client = anthropic.Anthropic(api_key=api_key)

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
        tool = anthropic.types.ToolParam(
            name=tool_name, description=tool_description, input_schema=input_schema
        )
        for attempt in (1, 2):
            resp = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=[tool],
                tool_choice={"type": "tool", "name": tool_name},
                messages=[{"role": "user", "content": user}],
            )
            for block in resp.content:
                if block.type == "tool_use" and block.name == tool_name:
                    payload = block.input
                    return payload if isinstance(payload, dict) else {}
            logger.warning("No tool_use block from %s (attempt %d)", tool_name, attempt)
        return {}

    def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
    ) -> str:
        resp = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        for block in resp.content:
            if block.type == "text":
                return block.text.strip()
        return ""
