def test_in_scope_question_returns_chunks(retriever):
    res = retriever.retrieve("How does ALS affect breathing?")
    assert not res.refused
    assert res.chunks
    assert all(c.source for c in res.chunks)
    assert res.latencies_ms["total_ms"] > 0


def test_off_topic_refused(retriever):
    res = retriever.retrieve("What is the capital of France?")
    assert res.refused
    assert res.refusal_reason == "out_of_scope"
    assert res.chunks == []


def test_empty_question_refused(retriever):
    res = retriever.retrieve("   ")
    assert res.refused


def test_sources_carry_provenance(retriever):
    res = retriever.retrieve("What is riluzole?")
    chunk = res.chunks[0]
    assert chunk.title is not None
    assert "riluzole" in chunk.document.lower() or "ALS" in chunk.document
