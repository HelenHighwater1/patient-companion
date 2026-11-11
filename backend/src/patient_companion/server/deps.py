"""Shared singletons: settings, providers, knowledge stores, retrievers."""

from __future__ import annotations

import json
import logging
from contextlib import suppress

from patient_companion.config import Settings, get_settings
from patient_companion.providers import get_embedder, get_llm
from patient_companion.rag.retrieve import Retriever
from patient_companion.rag.store import KnowledgeStore

logger = logging.getLogger(__name__)

DISEASE_LABELS = {
    "als": "ALS (amyotrophic lateral sclerosis)",
}

_stores: dict[str, KnowledgeStore] = {}
_retrievers: dict[str, Retriever] = {}


def get_store(disease: str, settings: Settings | None = None) -> KnowledgeStore:
    s = settings or get_settings()
    if disease not in _stores:
        store = KnowledgeStore(s.knowledge_dir / disease / "store")
        if not store.load():
            logger.warning("knowledge store for '%s' not built yet", disease)
        _stores[disease] = store
    return _stores[disease]


def get_retriever(disease: str | None = None, settings: Settings | None = None) -> Retriever:
    s = settings or get_settings()
    d = disease or s.default_disease
    if d not in _retrievers:
        _retrievers[d] = Retriever(
            get_store(d, s),
            get_embedder(s),
            get_llm(s),
            settings=s,
            disease_label=DISEASE_LABELS.get(d, d),
        )
    return _retrievers[d]


def list_diseases(settings: Settings | None = None) -> list[dict]:
    s = settings or get_settings()
    out = []
    if s.knowledge_dir.is_dir():
        for d in sorted(s.knowledge_dir.iterdir()):
            if (d / "raw").is_dir():
                store = get_store(d.name, s)
                out.append({"id": d.name, "label": DISEASE_LABELS.get(d.name, d.name), "chunks": store.size})
    return out


def corpus_summary(disease: str | None = None, settings: Settings | None = None) -> dict:
    """What's in the knowledge base: per-source chunk counts plus build metadata."""
    s = settings or get_settings()
    d = disease or s.default_disease
    store = get_store(d, s)
    by_source: dict[str, dict] = {}
    for row in store.rows:
        src = row.get("source", "?")
        entry = by_source.setdefault(
            src,
            {
                "source": src,
                "title": row.get("title") or src,
                "url": row.get("url"),
                "source_type": row.get("source_type"),
                "year": row.get("year"),
                "chunks": 0,
            },
        )
        entry["chunks"] += 1
    manifest: dict = {}
    manifest_path = store.dir / "manifest.json"
    if manifest_path.exists():
        with suppress(Exception):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "disease": d,
        "label": DISEASE_LABELS.get(d, d),
        "chunk_count": store.size,
        "built_at": manifest.get("built_at"),
        "embedding_model": manifest.get("embedding_model"),
        "sources": sorted(by_source.values(), key=lambda e: (e["source_type"] or "", e["title"])),
    }


def reset_state() -> None:
    """Drop cached stores/retrievers/providers/settings (tests)."""
    from patient_companion.providers import reset_providers

    _stores.clear()
    _retrievers.clear()
    get_settings.cache_clear()
    reset_providers()
