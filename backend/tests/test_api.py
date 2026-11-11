import json

import pytest
from fastapi.testclient import TestClient

from patient_companion.server.app import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


def _sse_events(resp) -> list[dict]:
    events = []
    for line in resp.text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["store_built"] is True


def test_diseases(client):
    r = client.get("/api/diseases")
    assert r.status_code == 200
    assert any(d["id"] == "als" and d["chunks"] > 0 for d in r.json())


def test_corpus_summary(client):
    r = client.get("/api/corpus")
    assert r.status_code == 200
    body = r.json()
    assert body["chunk_count"] > 0
    assert sum(src["chunks"] for src in body["sources"]) == body["chunk_count"]
    assert any(src["source"] == "ninds_als" for src in body["sources"])


def test_documents_list(client):
    docs = client.get("/api/documents").json()
    assert any(d["filename"] == "sample_note.txt" for d in docs)


def test_document_served_inline(client):
    r = client.get("/api/documents/sample_note.txt")
    assert r.status_code == 200
    assert r.headers["content-disposition"].startswith("inline")


def test_document_text_and_traversal(client):
    r = client.get("/api/documents/sample_note.txt/text")
    assert r.status_code == 200
    assert "ALS" in r.text
    assert client.get("/api/documents/../config.py").status_code in (400, 404)


def test_chat_question_streams_answer(client):
    r = client.post(
        "/api/chat",
        json={"input_type": "question", "message": "How does ALS affect breathing?"},
    )
    assert r.status_code == 200
    events = _sse_events(r)
    answer = next(e for e in events if e["type"] == "answer")
    assert answer["patient_response"]
    assert answer["disclaimer"]
    assert events[-1]["type"] == "done"


def test_chat_refusal(client):
    r = client.post("/api/chat", json={"message": "Who won the world cup?"})
    events = _sse_events(r)
    assert any(e["type"] == "refusal" for e in events)


def test_chat_document_by_filename(client):
    r = client.post(
        "/api/chat",
        json={"input_type": "document", "filename": "sample_note.txt"},
    )
    assert r.status_code == 200
    events = _sse_events(r)
    assert sum(1 for e in events if e["type"] == "card") == 5


def test_chat_requires_message(client):
    r = client.post("/api/chat", json={"input_type": "question"})
    assert r.status_code == 400


def test_upload_txt(client):
    r = client.post(
        "/api/chat/upload",
        files={"file": ("note.txt", b"Clinic note about ALS findings and care plan.")},
    )
    assert r.status_code == 200
    events = _sse_events(r)
    assert sum(1 for e in events if e["type"] == "card") == 5


def test_prep_sheet_endpoint(client):
    r = client.post(
        "/api/prep-sheet",
        json={
            "conversation_history": [{"question": "q?", "patient_response": "a"}],
            "document_context": "summary",
            "patient_concerns": ["side effects"],
        },
    )
    assert r.status_code == 200
    assert r.json()["suggested_questions"]
