"""Markdown parser (I-02): frontmatter becomes metadata, headings are kept."""

from __future__ import annotations

import re

from ingestion.parsers.base import ParsedDocument, ParseError
from ingestion.parsers.frontmatter import split_frontmatter

_H1 = re.compile(r"^#[ \t]+(.+?)(?:[ \t]*\{#[^}]+\})?[ \t]*$", re.MULTILINE)


def parse_markdown(data: bytes, filename: str, source_url: str | None) -> ParsedDocument:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ParseError("file is not valid UTF-8 text") from exc
    meta, body = split_frontmatter(text)
    if not body.strip():
        raise ParseError("document is empty")
    h1 = _H1.search(body)
    title = str(meta.get("title") or (h1.group(1) if h1 else filename.rsplit(".", 1)[0]))
    source = str(meta.get("url") or source_url or filename)
    return ParsedDocument(title, source, "text/markdown", body)
