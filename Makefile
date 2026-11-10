# Patient Companion — common tasks. Requires uv (backend) and npm (frontend).

.PHONY: setup api web test lint typecheck eval ingest

setup: ## One-time setup: venv, deps, ingest the ALS corpus
	cd backend && uv venv .venv && uv pip install -e '.[dev]'
	cd frontend && npm install
	cd backend && uv run python -m patient_companion.rag.ingest

api: ## Run the FastAPI backend on :8000
	cd backend && uv run uvicorn patient_companion.server.app:app --reload --port 8000

web: ## Run the Next.js frontend on :3000
	cd frontend && npm run dev

ingest: ## (Re)build the vector store from knowledge/als/raw
	cd backend && uv run python -m patient_companion.rag.ingest

test: ## All tests (backend pytest + frontend vitest) — no API keys needed
	cd backend && PC_LLM_PROVIDER=mock PC_EMBED_PROVIDER=mock uv run pytest
	cd frontend && npm test

lint: ## Ruff + ESLint
	cd backend && uv run ruff check src tests
	cd frontend && npm run lint

typecheck: ## mypy + tsc
	cd backend && uv run mypy
	cd frontend && npm run typecheck

eval: ## Real-provider retrieval eval (needs API keys)
	cd backend && uv run python -m patient_companion.eval.run

eval-mock: ## Offline eval on the fixture corpus
	cd backend && PC_LLM_PROVIDER=mock PC_EMBED_PROVIDER=mock uv run python -m patient_companion.eval.run --mock
