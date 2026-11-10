import numpy as np

from patient_companion.rag.store import KnowledgeStore


def test_save_load_roundtrip(tmp_path):
    store = KnowledgeStore(tmp_path)
    store.rows = [
        {"document": "ALS affects breathing.", "source": "a", "chunk_index": 0},
        {"document": "Cats sleep a lot.", "source": "b", "chunk_index": 0},
    ]
    store.embeddings = np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype="float32")
    store.save()

    loaded = KnowledgeStore(tmp_path)
    assert loaded.load()
    assert loaded.size == 2
    hits = loaded.dense_search([1.0, 0.0], 1)
    assert hits[0][0] == 0
    assert hits[0][1] > 0.99


def test_bm25_search(store):
    idxs = store.bm25_search("riluzole progression", 3)
    assert idxs
    row = store.rows[idxs[0]]
    assert "riluzole" in row["document"].lower()


def test_empty_store_load(tmp_path):
    assert not KnowledgeStore(tmp_path).load()
