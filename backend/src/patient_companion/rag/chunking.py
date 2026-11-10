"""Structure-aware chunking.

Source documents may be either ``@@@SECTION||path@@@``-marked text (what the
fetch script writes) or plain text (paragraphs separated by blank lines).
Chunker output never merges paragraphs across section boundaries and splits
oversized paragraphs on sentence boundaries.
"""

from __future__ import annotations

import re

import tiktoken

from patient_companion.config import Settings, get_settings

_TOKENIZER = tiktoken.get_encoding("cl100k_base")
SECTION_MARKER_RE = re.compile(r"^@@@SECTION\|\|(.+?)@@@\s*$")
# Splits on normal sentence boundaries AND the "word.NextWord" joins left
# behind when markup is stripped without whitespace (common in scraped PMC text).
_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|(?<=[a-z])\.(?=[A-Z])|(?<=[a-z])(?=[A-Z][a-z]{2,})"
)


def count_tokens(text: str) -> int:
    return len(_TOKENIZER.encode(text))


def text_to_paragraphs(content: str) -> list[dict]:
    """Parse a raw source file into [{section_path, text}].

    Handles section-marked text; falls back to blank-line paragraphs under a
    generic "Document" section for plain files.
    """
    paragraphs: list[dict] = []
    current = "Document"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        text = " ".join(" ".join(buf).split())
        if text:
            paragraphs.append({"section_path": current, "text": text})
        buf = []

    saw_markers = False
    for line in content.splitlines():
        m = SECTION_MARKER_RE.match(line.strip())
        if m:
            flush()
            saw_markers = True
            current = m.group(1).strip() or "Document"
            continue
        if not line.strip():
            if not saw_markers:
                flush()
            continue
        buf.append(line.strip())
    flush()

    # Mashed text with no blank lines: split long blobs on sentence boundaries.
    out: list[dict] = []
    for p in paragraphs:
        text = p["text"]
        if count_tokens(text) <= 900:
            out.append(p)
            continue
        for sent in _SENTENCE_SPLIT_RE.split(text):
            sent = sent.strip()
            if sent:
                out.append({"section_path": p["section_path"], "text": sent})
    return [p for p in out if p["text"]]


def chunk_paragraphs(
    paragraphs: list[dict],
    *,
    settings: Settings | None = None,
) -> list[dict]:
    """Pack paragraphs into ~target-token chunks within section boundaries."""
    s = settings or get_settings()
    target = s.chunk_target_tokens
    overlap = s.chunk_paragraph_overlap
    if not paragraphs:
        return []

    groups: list[tuple[str, list[str]]] = []
    for p in paragraphs:
        sp = p.get("section_path", "Document")
        tx = p.get("text", "").strip()
        if not tx:
            continue
        if groups and groups[-1][0] == sp:
            groups[-1][1].append(tx)
        else:
            groups.append((sp, [tx]))

    chunks: list[dict] = []
    for sec_path, texts in groups:
        leaf = sec_path.split(">")[-1].strip() if ">" in sec_path else sec_path
        start = 0
        while start < len(texts):
            buf: list[str] = []
            j = start
            while j < len(texts):
                candidate = " ".join(buf + [texts[j]]) if buf else texts[j]
                if buf and count_tokens(f"[{sec_path}]\n{candidate}") > target:
                    break
                buf.append(texts[j])
                j += 1
            if not buf:
                buf, j = [texts[start]], start + 1
            document = f"[{sec_path}]\n{' '.join(buf)}"
            chunks.append(
                {
                    "document": document,
                    "section_path": sec_path,
                    "section": leaf,
                    "token_count": count_tokens(document),
                }
            )
            start += max(1, (j - start) - overlap)
    return chunks
