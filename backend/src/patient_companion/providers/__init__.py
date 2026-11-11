"""Provider factory — the single place vendor clients are constructed."""

from __future__ import annotations

from patient_companion.config import Settings, get_settings
from patient_companion.providers.base import EmbeddingProvider, LLMProvider
from patient_companion.providers.caching import CachingEmbedder

_llms: dict[str, LLMProvider] = {}
_embedders: dict[str, EmbeddingProvider] = {}


def get_llm(settings: Settings | None = None) -> LLMProvider:
    s = settings or get_settings()
    if s.llm_provider not in _llms:
        if s.llm_provider == "mock":
            from patient_companion.providers.mock import MockLLM

            _llms[s.llm_provider] = MockLLM()
        else:
            from patient_companion.providers.anthropic_llm import AnthropicLLM

            _llms[s.llm_provider] = AnthropicLLM(api_key=s.anthropic_api_key)
    return _llms[s.llm_provider]


def get_embedder(settings: Settings | None = None) -> EmbeddingProvider:
    s = settings or get_settings()
    key = f"{s.embed_provider}:{s.embedding_model}"
    if key not in _embedders:
        inner: EmbeddingProvider
        if s.embed_provider == "mock":
            from patient_companion.providers.mock import MockEmbedder

            inner = MockEmbedder()
        else:
            from patient_companion.providers.openai_embed import OpenAIEmbedder

            inner = OpenAIEmbedder(api_key=s.openai_api_key, model=s.embedding_model)
        _embedders[key] = CachingEmbedder(inner)
    return _embedders[key]


def reset_providers() -> None:
    """Drop cached clients (used by tests after swapping settings)."""
    _llms.clear()
    _embedders.clear()
