# Patient Companion

**Prepare for your next appointment.** A demo that translates dense medical
documents into kind, plain language — then answers your questions from a
vetted knowledge base, with every claim checked against its source.

> ⚠️ **This is an independent demo project.** It is **not HIPAA compliant**,
> does not store or protect patient data, and is **not safe for real medical
> information**. All included sample documents are entirely fictional.

---

## What it does

1. **Upload a document** — a consultation report, a specialist email, a test
   result — and get five staged cards, one at a time: what the document is,
   the main finding, what the tests showed, what happens next, and four
   questions specific to *your* document to bring to your appointment.
2. **Ask questions.** Answers come *only* from the knowledge base (currently
   ALS: NINDS, NCBI GeneReviews, PubMed Central articles) — never from the
   model's general knowledge. Citations are shown per-claim.
3. **Prep sheet.** One click builds a printable sheet for your appointment:
   your own questions first, then suggested questions, topics worth raising,
   and a jargon glossary.

## The pipeline

Every question flows through a multi-agent chain:

```
question
  → scope check + query rewrite        (Haiku, forced tool call)
  → hybrid retrieval                   (dense + BM25 → RRF fusion → gate)
  → grounded answer with citations     (Sonnet, forced tool call)
  → claim-by-claim grounding audit     (embedding cosine + Haiku judge)
  → warm rewrite at your reading level (Sonnet, forced tool call)
  → patient response + sources + flags
```

**Why the cards can't break:** every LLM call uses *forced tool-use* — the
model must emit data matching a strict schema, so malformed card output is
structurally impossible. (The previous version parsed free-text JSON with
regex; this replaces that failure mode entirely.)

**Two-layer safety net for off-topic questions:** the scope check refuses
before any retrieval spend, and a retrieval-confidence gate catches anything
that slips through. Refusals say so kindly and point back to the care team.

## Project layout

```
patient-companion/
├── frontend/                  Next.js 15 + TypeScript + Tailwind
│   ├── app/                   page, layout, globals
│   ├── components/            UI incl. components/chat/*
│   └── lib/                   API client (SSE), types, tests
├── backend/
│   ├── src/patient_companion/
│   │   ├── server/            FastAPI app, SSE, singletons
│   │   ├── agents/            intake, answer, guard, tone, prep, pipeline, prompts
│   │   ├── rag/               chunking, store, ingest, rewrite, rerank, retrieve
│   │   ├── providers/         LLM/embedder protocols + anthropic/openai/mock
│   │   ├── eval/              eval harness (recall@k, MRR, refusal accuracy)
│   │   ├── config.py          all settings (pydantic, .env-driven)
│   │   └── schemas.py         shared pydantic models
│   └── tests/                 pytest — runs fully offline via mock providers
├── knowledge/als/             raw corpus (committed) + store/ (built, gitignored)
├── sample-documents/          fictional sample docs
├── .github/workflows/ci.yml   ruff, mypy, pytest, eslint, tsc, vitest, build, eval
├── greptile.json              Greptile review config + repo-specific rules
├── deploy/                    Dockerfile.api, Dockerfile.web, render.yaml
└── docker-compose.yml
```

## Setup

```bash
cp .env.example .env          # add ANTHROPIC_API_KEY + OPENAI_API_KEY
make setup                    # venv + deps + ingest the ALS corpus (~893 chunks)
```

Or manually:

```bash
cd backend && uv venv .venv && uv pip install -e '.[dev]'
cd frontend && npm install
cd backend && uv run python -m patient_companion.rag.ingest
```

## Run

```bash
make api    # FastAPI on :8000   (uvicorn --reload)
make web    # Next.js on :3000
```

or `docker compose up --build` for both at once.

## Testing & CI

```bash
make test        # pytest + vitest — mock providers, zero API keys needed
make lint        # ruff + eslint
make typecheck   # mypy + tsc --noEmit
make eval        # real retrieval eval (needs keys): recall@5, MRR, refusal
make eval-mock   # same harness on a fixture corpus, fully offline
```

GitHub Actions runs all of the above on every PR (`ci.yml`), including an
eval smoke test that asserts the refusal safety property. Greptile review is
configured in `greptile.json` — connect the repo at
[app.greptile.com](https://app.greptile.com) to enable it.

## Deployment

- **Frontend** → Vercel free tier. Set `NEXT_PUBLIC_API_URL` to the API's URL.
- **Backend** → any Python host; `deploy/render.yaml` is a ready blueprint,
  or `deploy/Dockerfile.api` for Fly.io/etc. The store is built at startup
  (`ingest`), so the service is stateless.
- **Cost**: $0 on free tiers; only real spend is a few cents of API usage.

## Optional knobs (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PC_LLM_PROVIDER` | `anthropic` | `mock` runs the whole pipeline offline |
| `PC_EMBED_PROVIDER` | `openai` | `mock` hash-embeddings for tests/demo |
| `PC_RERANKER_BACKEND` | `none` | `fastembed` adds an ONNX cross-encoder (`pip install '.[rerank]'`) |
| `PC_LLM_MODEL_STRONG` / `_FAST` | sonnet / haiku | model IDs per tier |
| `PC_GATE_MIN_DENSE_COSINE` | `0.28` | retrieval confidence floor |
| `PC_DEMO_SPEND_CAP_REQUESTS` | `0` | stop serving LLM calls after N requests |

## Adding another disease

```
knowledge/
└── <disease>/
    ├── raw/          *.txt source documents
    ├── sources.json  optional title/url/type per source stem
    └── store/        built by ingest
```

`python -m patient_companion.rag.ingest --disease <name>` builds it; the API
already exposes `/api/diseases`. The architecture is per-disease-namespaced
so ALS is the first of many.

## Honest limitations

This demo shows the *shape* of a safe system — grounded retrieval, audited
claims, structured outputs, gentle pacing — but a production version would
still need: a BAA + HIPAA-compliant infrastructure, clinical review,
crisis escalation to humans, and much deeper eval coverage. The distance
between this and something safe for real patients is large, and deliberately
acknowledged rather than hidden.
