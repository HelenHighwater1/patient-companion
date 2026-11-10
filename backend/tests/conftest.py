"""Test fixtures: a real pipeline against a fixture corpus with mock providers.

Environment variables are set BEFORE importing patient_companion modules so
settings pick up mock providers — the whole suite runs with zero API keys.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="pc-test-"))
_KNOWLEDGE = _TMP / "knowledge"
_SAMPLES = _TMP / "sample-documents"

os.environ["PC_LLM_PROVIDER"] = "mock"
os.environ["PC_EMBED_PROVIDER"] = "mock"
os.environ["PC_KNOWLEDGE_DIR"] = str(_KNOWLEDGE)
os.environ["PC_SAMPLE_DOCUMENTS_DIR"] = str(_SAMPLES)

from patient_companion.config import get_settings  # noqa: E402
from patient_companion.providers import get_embedder, get_llm  # noqa: E402
from patient_companion.rag.ingest import build_index  # noqa: E402
from patient_companion.rag.retrieve import Retriever  # noqa: E402
from patient_companion.server.deps import get_store  # noqa: E402

FIXTURE_SOURCES = {
    "ninds_als": (
        "Amyotrophic lateral sclerosis (ALS), also called Lou Gehrig's disease, "
        "affects motor neurons.\n\n"
        "Early symptoms include muscle weakness, twitching, cramps, and slurred speech. "
        "As ALS progresses it affects walking, speaking, swallowing, and breathing."
    ),
    "ncbi_als_care": (
        "Non-invasive ventilation (NIV) improves quality of life for people with ALS. "
        "Breathing function should be monitored regularly.\n\n"
        "Riluzole is an approved medication that modestly slows the progression of ALS."
    ),
    "pmc_nutrition": (
        "Weight loss and swallowing difficulty are common in ALS. "
        "A dietitian can help, and when appropriate a feeding tube maintains nutrition."
    ),
}


@pytest.fixture(scope="session", autouse=True)
def built_store():
    """Ingest the fixture corpus once per test session."""
    raw = _KNOWLEDGE / "als" / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name, text in FIXTURE_SOURCES.items():
        (raw / f"{name}.txt").write_text(text, encoding="utf-8")
    _SAMPLES.mkdir(parents=True, exist_ok=True)
    (_SAMPLES / "sample_note.txt").write_text(
        "Clinic note: findings consistent with ALS. Follow up in 4 weeks.",
        encoding="utf-8",
    )
    return build_index("als", settings=get_settings(), embedder=get_embedder())


@pytest.fixture
def store(built_store):
    return get_store("als", get_settings())


@pytest.fixture
def retriever(store):
    return Retriever(store, get_embedder(), get_llm(), settings=get_settings())
