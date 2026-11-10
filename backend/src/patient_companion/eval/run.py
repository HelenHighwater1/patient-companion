"""Run the retrieval eval.

    python -m patient_companion.eval.run                # full eval, real providers
    python -m patient_companion.eval.run --mock         # fixture corpus, mock providers (CI)
    python -m patient_companion.eval.run --no-rewrite   # skip the LLM rewrite stage

Writes eval/results/<timestamp>.json and eval/results/latest.json under the
backend directory.
"""

from __future__ import annotations

import argparse
import json
import logging
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from patient_companion.config import get_settings
from patient_companion.eval.metrics import recall_at_k, reciprocal_rank
from patient_companion.providers import get_embedder, get_llm
from patient_companion.rag.retrieve import Retriever
from patient_companion.rag.store import KnowledgeStore

logger = logging.getLogger(__name__)

QUESTIONS_PATH = Path(__file__).parent / "questions.jsonl"
RESULTS_DIR = Path(__file__).resolve().parents[3] / "eval" / "results"

_FIXTURE_DOCS = [
    ("ninds_als", "ALS, or amyotrophic lateral sclerosis, is a disease of the motor "
     "neurons. Early symptoms include muscle weakness, twitching, cramps, and slurred "
     "speech. As ALS progresses it affects walking, speaking, swallowing, and breathing."),
    ("ncbi_als_care", "Non-invasive ventilation (NIV) improves quality of life and "
     "survival in ALS. Breathing function should be monitored regularly. Riluzole is an "
     "approved medication that modestly slows progression."),
    ("pmc_nutrition", "Weight loss and swallowing difficulty are common in ALS. "
     "Dietitian involvement and, when appropriate, a feeding tube help maintain "
     "nutrition and safety."),
]


def _load_questions() -> list[dict]:
    return [
        json.loads(line)
        for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _fixture_store(tmp: Path, embedder) -> KnowledgeStore:
    """Tiny in-memory corpus so --mock exercises the whole retrieval path."""
    from patient_companion.rag.chunking import chunk_paragraphs, text_to_paragraphs

    store = KnowledgeStore(tmp)
    rows = []
    docs = []
    for name, text in _FIXTURE_DOCS:
        chunks = chunk_paragraphs(text_to_paragraphs(text), settings=get_settings())
        for i, ch in enumerate(chunks):
            rows.append(
                {"document": ch["document"], "source": name, "chunk_index": i,
                 "title": name, "section": ch.get("section"), "section_path": ch.get("section_path")}
            )
            docs.append(ch["document"])
    import numpy as np

    store.rows = rows
    store.embeddings = np.asarray(embedder.embed(docs), dtype="float32")
    store.save()
    return store


def run_eval(*, mock: bool, skip_rewrite: bool) -> dict:
    settings = get_settings()
    if mock:
        settings = settings.model_copy(
            update={"llm_provider": "mock", "embed_provider": "mock"}
        )
    questions = _load_questions()
    tmp: tempfile.TemporaryDirectory | None = None
    if mock:
        tmp = tempfile.TemporaryDirectory()
        store = _fixture_store(Path(tmp.name), get_embedder(settings))
    else:
        store = KnowledgeStore(settings.store_dir)
        if not store.load():
            raise SystemExit("Store not built. Run python -m patient_companion.rag.ingest")

    retriever = Retriever(
        store, get_embedder(settings), get_llm(settings), settings=settings
    )

    records = []
    for q in questions:
        t0 = time.perf_counter()
        res = retriever.retrieve(q["question"], q.get("conversation_history"), skip_rewrite=skip_rewrite)
        expected = q.get("expected_sources") or []
        category = q.get("category", "factual")
        record = {
            "id": q["id"],
            "category": category,
            "question": q["question"],
            "refused": res.refused,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "recall@5": recall_at_k(res.chunks, expected, 5),
            "mrr": reciprocal_rank(res.chunks, expected),
            "sources": [c.source for c in res.chunks[:5]],
        }
        records.append(record)

    factual = [r for r in records if r["category"] == "factual"]
    refusal = [r for r in records if r["category"] == "refusal"]
    summary = {
        "ran_at": datetime.now(UTC).isoformat(),
        "mock": mock,
        "skip_rewrite": skip_rewrite,
        "n_questions": len(records),
        "mean_recall@5": round(sum(r["recall@5"] for r in factual) / max(1, len(factual)), 3),
        "mean_mrr": round(sum(r["mrr"] for r in factual) / max(1, len(factual)), 3),
        "refusal_accuracy": round(
            sum(1 for r in refusal if r["refused"]) / max(1, len(refusal)), 3
        ),
        "records": records,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS_DIR / f"{stamp}.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if tmp is not None:
        tmp.cleanup()
    return summary


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="fixture corpus + mock providers")
    parser.add_argument("--no-rewrite", action="store_true", help="skip the LLM rewrite stage")
    args = parser.parse_args()
    summary = run_eval(mock=args.mock, skip_rewrite=args.no_rewrite)
    print(
        f"recall@5={summary['mean_recall@5']}  mrr={summary['mean_mrr']}  "
        f"refusal={summary['refusal_accuracy']}  (n={summary['n_questions']})"
    )


if __name__ == "__main__":
    main()
