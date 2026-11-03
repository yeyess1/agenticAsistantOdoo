from __future__ import annotations

import pymupdf
import pytest
from ingestion.parsers import ParseError, UnsupportedTypeError, parse_document
from ingestion.parsers.frontmatter import dump_frontmatter, split_frontmatter


def make_pdf(pages: list[str]) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 100), text.split("\n")[0], fontsize=22)
        page.insert_textbox(pymupdf.Rect(72, 120, 520, 700), text.split("\n", 1)[1], fontsize=11)
    return bytes(doc.tobytes())


def test_frontmatter_roundtrip() -> None:
    text = dump_frontmatter({"url": "https://x/y", "title": "T: colon"}, "# Body\n")
    meta, body = split_frontmatter(text)
    assert meta == {"url": "https://x/y", "title": "T: colon"}
    assert body.strip() == "# Body"
    assert split_frontmatter("no front matter") == ({}, "no front matter")


def test_markdown_uses_frontmatter_url_as_source() -> None:
    data = b"---\nurl: https://odoo.test/doc.html\ntitle: My Doc\n---\n\n# Heading\n\ntext\n"
    doc = parse_document(data, "doc.md")
    assert (doc.title, doc.source, doc.mime_type) == (
        "My Doc",
        "https://odoo.test/doc.html",
        "text/markdown",
    )
    assert doc.markdown.startswith("# Heading")


def test_markdown_without_frontmatter_uses_h1_and_filename() -> None:
    doc = parse_document(b"# Hello {#h}\n\nbody", "notes.md")
    assert (doc.title, doc.source) == ("Hello", "notes.md")
    assert parse_document(b"# Hello\n\nbody", "notes.md", "https://u/n").source == "https://u/n"


def test_txt_is_unstructured() -> None:
    doc = parse_document(b"line one\n\nline two", "plain.txt")
    assert (doc.title, doc.mime_type, doc.structured) == ("plain", "text/plain", False)


def test_pdf_keeps_page_numbers() -> None:
    pdf = make_pdf(["First page title\nbody one", "Second page title\nbody two"])
    doc = parse_document(pdf, "guide.pdf")
    assert doc.mime_type == "application/pdf"
    assert doc.source == "guide.pdf"
    assert "<!-- page:1 -->" in doc.markdown and "<!-- page:2 -->" in doc.markdown
    assert doc.markdown.index("body one") < doc.markdown.index("<!-- page:2 -->")


@pytest.mark.parametrize(
    ("data", "name", "exc"),
    [
        (b"", "e.md", ParseError),
        (b"   \n", "e.txt", ParseError),
        (b"\xff\xfe\x00bad", "b.txt", ParseError),
        (b"not a pdf", "x.pdf", ParseError),
        (b"x", "x.docx", UnsupportedTypeError),
        (b"x", "noext", UnsupportedTypeError),
    ],
)
def test_invalid_documents(data: bytes, name: str, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        parse_document(data, name)
