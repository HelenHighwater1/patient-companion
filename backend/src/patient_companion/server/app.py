"""FastAPI application factory + routes.

Thin HTTP layer: every endpoint delegates to the pipeline and serializes
events as SSE. Run with::

    uvicorn patient_companion.server.app:app --reload
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from patient_companion.agents.pipeline import (
    build_prep_sheet,
    stream_answer,
    stream_document_summary,
)
from patient_companion.config import get_settings
from patient_companion.documents import extract_document_bytes, extract_document_text
from patient_companion.providers import get_embedder, get_llm
from patient_companion.schemas import (
    ChatRequest,
    PrepSheetRequest,
    SampleDocument,
)
from patient_companion.server.deps import corpus_summary, get_retriever, list_diseases
from patient_companion.server.sse import sse_response

logger = logging.getLogger("patient_companion")
logging.basicConfig(level=logging.INFO, format="%(message)s")

limiter = Limiter(key_func=get_remote_address)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Patient Companion API", version="0.1.0")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _spend = {"count": 0}

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        rid = str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    def _spend_exhausted() -> bool:
        cap = settings.demo_spend_cap_requests
        if cap and _spend["count"] >= cap:
            return True
        _spend["count"] += 1
        return False

    # -- meta -----------------------------------------------------------------

    @app.get("/api/health")
    def health():
        store_dir = settings.store_dir
        manifest = store_dir / "manifest.json"
        info = {"status": "ok", "store_built": manifest.exists()}
        if manifest.exists():
            with suppress(Exception):
                info["manifest"] = json.loads(manifest.read_text(encoding="utf-8"))
        return info

    @app.get("/api/diseases")
    def diseases():
        return list_diseases(settings)

    @app.get("/api/corpus")
    def corpus():
        return corpus_summary(settings=settings)

    # -- sample documents -------------------------------------------------------

    @app.get("/api/documents")
    def documents() -> list[SampleDocument]:
        d = settings.sample_documents_dir
        if not d.is_dir():
            return []
        out = []
        for path in sorted(d.iterdir()):
            if path.is_file() and not path.name.startswith("."):
                ext = path.suffix.lower()
                ftype = {".pdf": "PDF", ".eml": "EMAIL", ".email": "EMAIL"}.get(
                    ext, ext.lstrip(".").upper() or "FILE"
                )
                out.append(
                    SampleDocument(
                        filename=path.name,
                        title=path.stem.replace("_", " "),
                        file_type=ftype,
                    )
                )
        return out

    def _sample_path(filename: str) -> Path:
        # Prevent path traversal — only plain filenames inside the sample dir.
        if Path(filename).name != filename:
            raise HTTPException(400, "Invalid filename")
        path = settings.sample_documents_dir / filename
        if not path.is_file():
            raise HTTPException(404, "Document not found")
        return path

    @app.get("/api/documents/{filename}")
    def serve_document(filename: str):
        path = _sample_path(filename)
        return FileResponse(path, filename=filename, content_disposition_type="inline")

    @app.get("/api/documents/{filename}/text", response_class=PlainTextResponse)
    def document_text(filename: str):
        return extract_document_text(_sample_path(filename))

    # -- chat / document pipeline ------------------------------------------------

    @app.post("/api/chat")
    @limiter.limit(f"{settings.rate_limit_per_hour}/hour")
    def chat(request: Request, body: ChatRequest):
        rid = getattr(request.state, "request_id", "-")
        logger.info(json.dumps({"event": "chat", "request_id": rid, "input_type": body.input_type}))
        if _spend_exhausted():
            raise HTTPException(429, "Demo request limit reached. Try again later.")

        llm = get_llm(settings)

        if body.input_type == "document":
            text = (body.document_text or "").strip()
            if not text and body.filename:
                text = extract_document_text(_sample_path(body.filename))
            if not text.strip():
                raise HTTPException(400, "Please upload or select a document first.")
            return sse_response(stream_document_summary(text, llm=llm, settings=settings))

        question = (body.message or "").strip()
        if not question:
            raise HTTPException(400, "Message required for question input")
        return sse_response(
            stream_answer(
                question,
                body.conversation_history,
                body.document_context,
                body.reading_level,
                retriever=get_retriever(None, settings),
                llm=llm,
                embedder=get_embedder(settings),
                settings=settings,
            )
        )

    @app.post("/api/chat/upload")
    @limiter.limit(f"{settings.upload_limit_per_hour}/hour")
    async def chat_upload(request: Request, file: UploadFile = File(...)):  # noqa: B008
        if _spend_exhausted():
            raise HTTPException(429, "Demo request limit reached. Try again later.")
        contents = await file.read()
        if len(contents) > settings.max_upload_bytes:
            raise HTTPException(413, "File too large (10 MB max)")
        text = extract_document_bytes(file.filename or "", contents)
        if not text.strip():
            raise HTTPException(400, "Could not extract text from that file")
        return sse_response(stream_document_summary(text, llm=get_llm(settings), settings=settings))

    @app.post("/api/prep-sheet")
    @limiter.limit(f"{settings.upload_limit_per_hour}/hour")
    def prep_sheet(request: Request, body: PrepSheetRequest):
        if _spend_exhausted():
            raise HTTPException(429, "Demo request limit reached. Try again later.")
        sheet = build_prep_sheet(
            body.conversation_history,
            body.document_context,
            body.patient_concerns,
            llm=get_llm(settings),
            settings=settings,
        )
        return sheet.model_dump()

    return app


app = create_app()
