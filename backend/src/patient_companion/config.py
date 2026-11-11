"""Application settings.

Every knob in one place, loaded from ``.env`` at the repo root. Plain
``ANTHROPIC_API_KEY`` / ``OPENAI_API_KEY`` env vars work; everything else uses
the ``PC_`` prefix to avoid collisions.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = PACKAGE_ROOT.parent.parent
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", ".env"),
        env_prefix="PC_",
        extra="ignore",
    )

    # --- Providers -------------------------------------------------------
    anthropic_api_key: str = Field(
        default="", validation_alias=AliasChoices("PC_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    )
    openai_api_key: str = Field(
        default="", validation_alias=AliasChoices("PC_OPENAI_API_KEY", "OPENAI_API_KEY")
    )
    llm_provider: Literal["anthropic", "mock"] = "anthropic"
    embed_provider: Literal["openai", "mock"] = "openai"

    # --- Models ------------------------------------------------------------
    llm_model_strong: str = "claude-sonnet-4-6"  # intake, answer, prep
    llm_model_fast: str = "claude-haiku-4-5-20251001"  # rewrite, grounding judge
    embedding_model: str = "text-embedding-3-small"
    reranker_backend: Literal["none", "fastembed"] = "none"
    reranker_model: str = "BAAI/bge-reranker-base-v2.0"

    # --- Knowledge base ----------------------------------------------------
    knowledge_dir: Path = REPO_ROOT / "knowledge"
    default_disease: str = "als"

    # --- Chunking ----------------------------------------------------------
    chunk_target_tokens: int = 500
    chunk_paragraph_overlap: int = 1

    # --- Retrieval ---------------------------------------------------------
    top_k: int = 5
    rrf_k: int = 60
    dense_candidates: int = 30
    bm25_candidates: int = 30
    fusion_pool_size: int = 30
    # Refuse when the best candidate's dense cosine is below this floor.
    # The LLM scope check in the rewrite step catches most off-topic
    # questions before retrieval; this is the safety net.
    gate_min_dense_cosine: float = 0.28
    # With the optional reranker enabled, refuse on weak top-vs-tail margin.
    gate_min_rerank_margin: float = 0.35

    # --- Server -------------------------------------------------------------
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    sample_documents_dir: Path = REPO_ROOT / "sample-documents"
    rate_limit_per_hour: int = 60
    upload_limit_per_hour: int = 20
    max_upload_bytes: int = 10 * 1024 * 1024
    # Stop serving LLM calls after N requests per process (0 = unlimited).
    demo_spend_cap_requests: int = 0

    @property
    def store_dir(self) -> Path:
        return self.knowledge_dir / self.default_disease / "store"

    @property
    def raw_dir(self) -> Path:
        return self.knowledge_dir / self.default_disease / "raw"


@lru_cache
def get_settings() -> Settings:
    return Settings()
