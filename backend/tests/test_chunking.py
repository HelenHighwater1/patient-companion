from patient_companion.rag.chunking import chunk_paragraphs, text_to_paragraphs


def test_marked_text_parses_sections():
    content = (
        "@@@SECTION||Intro > Basics@@@\nFirst paragraph about ALS.\n\n"
        "@@@SECTION||Care > Breathing@@@\nSecond paragraph about NIV."
    )
    paras = text_to_paragraphs(content)
    assert {p["section_path"] for p in paras} == {"Intro > Basics", "Care > Breathing"}


def test_plain_text_uses_document_section():
    paras = text_to_paragraphs("Para one.\n\nPara two.")
    assert len(paras) == 2
    assert all(p["section_path"] == "Document" for p in paras)


def test_mashed_text_splits_on_sentences():
    blob = "Sentence one is here. " * 200 + "Sentence two follows. " * 200
    paras = text_to_paragraphs(blob)
    assert len(paras) > 1


def test_joined_words_split_without_space():
    blob = "IntroductionThe principle of care matters." + ("More detail follows here. " * 200)
    paras = text_to_paragraphs(blob)
    assert len(paras) > 1


def test_chunks_respect_section_boundaries(settings=None):
    paras = [
        {"section_path": "A", "text": "alpha " * 50},
        {"section_path": "B", "text": "bravo " * 50},
    ]
    chunks = chunk_paragraphs(paras)
    assert len(chunks) == 2
    assert chunks[0]["section_path"] == "A" and "bravo" not in chunks[0]["document"]
    assert chunks[1]["section_path"] == "B"


def test_empty_input():
    assert text_to_paragraphs("") == []
    assert chunk_paragraphs([]) == []
