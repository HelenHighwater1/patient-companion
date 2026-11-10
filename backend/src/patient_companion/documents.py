"""Plain-text extraction from PDF, EML, and text files."""

from __future__ import annotations

import email
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        parts = [text for page in reader.pages if (text := page.extract_text())]
        return "\n\n".join(parts)
    except Exception as e:
        logger.warning("PDF extraction failed for %s: %s", path, e)
        return ""


def extract_email_text(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f)
        parts = []
        for header in ("Subject", "From", "Date"):
            if msg.get(header):
                parts.append(f"{header}: {msg[header]}")
        parts.append("")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if isinstance(payload, bytes):
                        body = payload.decode(errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if isinstance(payload, bytes):
                body = payload.decode(errors="replace")
        parts.append(body)
        return "\n".join(parts).strip()
    except Exception as e:
        logger.warning("Email extraction failed for %s: %s", path, e)
        return ""


def extract_document_text(path: Path) -> str:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in (".eml", ".email"):
        return extract_email_text(path)
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Text read failed for %s: %s", path, e)
        return ""


def extract_document_bytes(filename: str, contents: bytes) -> str:
    """Extract text from uploaded bytes via a temp file."""
    import tempfile

    suffix = Path(filename or "").suffix.lower()
    if suffix in (".pdf", ".eml", ".email"):
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(contents)
            tmp.flush()
            return extract_document_text(Path(tmp.name))
    return contents.decode("utf-8", errors="replace")
