"""Format parsers: every format is normalized to Markdown (D-06)."""

from __future__ import annotations

from pathlib import PurePath

from ingestion.parsers.base import ParsedDocument, ParseError, UnsupportedTypeError
from ingestion.parsers.markdown import parse_markdown
from ingestion.parsers.pdf import parse_pdf
from ingestion.parsers.txt import parse_text

SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt"}

__all__ = [
    "SUPPORTED_SUFFIXES",
    "ParseError",
    "ParsedDocument",
    "UnsupportedTypeError",
    "parse_document",
]


def parse_document(data: bytes, filename: str, source_url: str | None = None) -> ParsedDocument:
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".pdf":
        return parse_pdf(data, filename, source_url)
    if suffix in {".md", ".markdown"}:
        return parse_markdown(data, filename, source_url)
    if suffix == ".txt":
        return parse_text(data, filename, source_url)
    raise UnsupportedTypeError(f"unsupported file type {suffix or '(none)'}; use .pdf, .md, .txt")
