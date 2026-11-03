"""Main-article extraction for the Odoo documentation (Sphinx theme) (I-08)."""

from __future__ import annotations

from dataclasses import dataclass

from bs4 import Tag

from ingestion.scraper.html_to_md import html_to_markdown, parse_html


class ExtractionError(ValueError):
    """The page does not have the expected article container."""


@dataclass(frozen=True)
class Article:
    title: str
    markdown: str


def extract_article(html: str) -> Article:
    soup = parse_html(html)
    main = soup.select_one("article#o_content div[role=main]") or soup.select_one(
        "article#o_content"
    )
    if not isinstance(main, Tag):
        raise ExtractionError("article#o_content not found")
    h1 = main.find("h1")
    if not isinstance(h1, Tag):
        raise ExtractionError("page has no <h1>")
    title = " ".join(h1.get_text().replace("\u00b6", "").split())
    markdown = html_to_markdown(main)
    return Article(title=title, markdown=markdown)
