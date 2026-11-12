from patient_companion.agents.guard import mechanical_scores
from patient_companion.providers import get_embedder
from patient_companion.schemas import Chunk, Citation


class _SpyEmbedder:
    """Wraps the real embedder and records every batch it is asked to embed."""

    def __init__(self, inner):
        self._inner = inner
        self.calls: list[list[str]] = []

    def embed(self, texts):
        self.calls.append(list(texts))
        return self._inner.embed(texts)


def test_retrieved_chunks_carry_stored_embedding(retriever):
    res = retriever.retrieve("How does ALS affect breathing?")
    assert res.chunks
    assert all(c.embedding for c in res.chunks)


def test_mechanical_scores_only_embeds_new_claim_text(retriever):
    res = retriever.retrieve("How does ALS affect breathing?")
    cited = res.chunks[0]
    spy = _SpyEmbedder(get_embedder())
    scores = mechanical_scores(
        [
            Citation(
                marker=1,
                claim="ALS affects breathing.",
                source=cited.source,
                chunk_index=cited.chunk_index,
            )
        ],
        res.chunks,
        embedder=spy,
    )
    # The cited chunk's vector came from the store — only the claim is embedded.
    assert spy.calls == [["ALS affects breathing."]]
    assert scores[0]["source"] == cited.source
    assert scores[0]["cosine"] > 0


def test_mechanical_scores_falls_back_to_embedding_chunk_text():
    chunk = Chunk(document="Riluzole modestly slows ALS progression.", source="doc")
    spy = _SpyEmbedder(get_embedder())
    scores = mechanical_scores(
        [Citation(marker=1, claim="Riluzole slows ALS.", source="doc", chunk_index=0)],
        [chunk],
        embedder=spy,
    )
    assert spy.calls == [["Riluzole slows ALS.", "Riluzole modestly slows ALS progression."]]
    assert scores[0]["cosine"] > 0
