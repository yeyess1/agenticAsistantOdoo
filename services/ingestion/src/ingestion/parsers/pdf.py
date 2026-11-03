"""PDF parser (I-02): pymupdf4llm keeps headings and code; page numbers become markers.

Each page is prefixed with `<!-- page:N -->`, which the chunker turns into `Chunk.page`.
"""

from __future__ import annotations

import re

import pymupdf
import pymupdf4llm

from ingestion.parsers.base import ParsedDocument, ParseError

_PRIVATE_USE = re.compile("[-]")  # icon-font / ligature glyphs from the web render
_BOLD_HEADING = re.compile(r"^(#{1,6})[ \t]+\*\*(.+?)\*\*[ \t]*$", re.MULTILINE)


def _clean_page(text: str) -> str:
    text = _PRIVATE_USE.sub("", text)
    text = _BOLD_HEADING.sub(r"\1 \2", text)  # `### **Title**` -> `### Title`
    return text.replace("~~", "")


def parse_pdf(data: bytes, filename: str, source_url: str | None) -> ParsedDocument:
    if not data.startswith(b"%PDF"):
        raise ParseError("file is not a PDF")
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        pages = pymupdf4llm.to_markdown(doc, page_chunks=True, use_ocr=False)
    except Exception as exc:  # corrupted/encrypted files raise assorted pymupdf errors
        raise ParseError(f"cannot parse PDF: {exc}") from exc
    parts = []
    for i, page in enumerate(pages, start=1):
        number = int(page.get("metadata", {}).get("page_number", i))
        text = _clean_page(page["text"]).strip()
        if text:
            parts.append(f"<!-- page:{number} -->\n\n{text}")
    markdown = "\n\n".join(parts)
    if not markdown.strip():
        raise ParseError("PDF has no extractable text")
    title = (doc.metadata or {}).get("title") or filename.rsplit(".", 1)[0]
    return ParsedDocument(str(title), source_url or filename, "application/pdf", markdown)
