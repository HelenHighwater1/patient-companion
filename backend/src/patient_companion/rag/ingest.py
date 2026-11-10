"""Build the vector store for a disease corpus.

    python -m patient_companion.rag.ingest            # ingest default disease
    python -m patient_companion.rag.ingest --disease als

Reads ``knowledge/<disease>/raw/*.txt``, chunks them, embeds with the
configured EmbeddingProvider, and writes ``knowledge/<disease>/store/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from patient_companion.config import Settings, get_settings
from patient_companion.providers import get_embedder
from patient_companion.providers.base import EmbeddingProvider
from patient_companion.rag.chunking import chunk_paragraphs, text_to_paragraphs
from patient_companion.rag.store import KnowledgeStore

logger = logging.getLogger(__name__)

_EMBED_BATCH = 96


def _load_source_metadata(raw_dir: Path) -> dict[str, dict]:
    meta_path = raw_dir.parent / "sources.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return {}


def _source_meta(stem: str, source_meta: dict[str, dict]) -> dict:
    """Resolve display metadata for a source file, with a PMC-aware fallback."""
    meta = dict(source_meta.get(stem, {}))
    import re

    pmc = re.fullmatch(r"pmc_(\d+)", stem)
    if pmc:
        meta.setdefault("title", f"PubMed Central article PMC{pmc.group(1)}")
        meta.setdefault("url", f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc.group(1)}/")
        meta.setdefault("type", "research-article")
    meta.setdefault("title", stem.replace("_", " "))
    return meta


def build_index(
    disease: str,
    *,
    settings: Settings | None = None,
    embedder: EmbeddingProvider | None = None,
) -> dict:
    s = settings or get_settings()
    raw_dir = s.knowledge_dir / disease / "raw"
    store_dir = s.knowledge_dir / disease / "store"
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"No raw corpus at {raw_dir}")
    files = sorted(p for p in raw_dir.iterdir() if p.suffix == ".txt")
    if not files:
        raise FileNotFoundError(f"No .txt sources under {raw_dir}")

    embedder = embedder or get_embedder(s)
    source_meta = _load_source_metadata(raw_dir)

    rows: list[dict] = []
    file_hashes: dict[str, str] = {}
    for path in files:
        content = path.read_text(encoding="utf-8", errors="replace")
        file_hashes[path.name] = hashlib.sha256(content.encode()).hexdigest()[:16]
        paragraphs = text_to_paragraphs(content)
        chunks = chunk_paragraphs(paragraphs, settings=s)
        meta = _source_meta(path.stem, source_meta)
        for i, ch in enumerate(chunks):
            rows.append(
                {
                    "id": f"{path.stem}:{i}",
                    "document": ch["document"],
                    "source": path.stem,
                    "chunk_index": i,
                    "section": ch.get("section"),
                    "section_path": ch.get("section_path"),
                    "token_count": ch.get("token_count"),
                    "title": meta.get("title"),
                    "url": meta.get("url"),
                    "year": meta.get("year"),
                    "source_type": meta.get("type"),
                }
            )

    embeddings: list[list[float]] = []
    for i in range(0, len(rows), _EMBED_BATCH):
        batch = [r["document"] for r in rows[i : i + _EMBED_BATCH]]
        embeddings.extend(embedder.embed(batch))
        logger.info("embedded %d/%d chunks", min(i + _EMBED_BATCH, len(rows)), len(rows))

    store = KnowledgeStore(store_dir)
    store.rows = rows
    store.embeddings = np.asarray(embeddings, dtype=np.float32)
    store.save()

    manifest = {
        "disease": disease,
        "built_at": datetime.now(UTC).isoformat(),
        "embedding_model": getattr(embedder, "_model", type(embedder).__name__),
        "chunk_count": len(rows),
        "sources": file_hashes,
    }
    (store_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("ingest complete: %d chunks from %d files -> %s", len(rows), len(files), store_dir)
    return manifest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Ingest a disease corpus into the vector store.")
    parser.add_argument("--disease", default=get_settings().default_disease)
    args = parser.parse_args()
    build_index(args.disease)


if __name__ == "__main__":
    main()
