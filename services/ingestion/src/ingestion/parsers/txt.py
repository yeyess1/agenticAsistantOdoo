"""Plain-text parser (I-02): no structure, goes straight to the recursive splitter."""

from __future__ import annotations

from ingestion.parsers.base import ParsedDocument, ParseError


def parse_text(data: bytes, filename: str, source_url: str | None) -> ParsedDocument:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("file is not valid UTF-8 text") from exc
    if not text.strip():
        raise ParseError("document is empty")
    return ParsedDocument(
        filename.rsplit(".", 1)[0], source_url or filename, "text/plain", text, structured=False
    )
