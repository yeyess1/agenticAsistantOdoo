"""Parser output shared by every format (I-02)."""

from __future__ import annotations

from dataclasses import dataclass


class ParseError(ValueError):
    """The document is empty or cannot be parsed (HTTP 422)."""


class UnsupportedTypeError(ValueError):
    """The file type is not supported (HTTP 415)."""


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    source: str
    mime_type: str
    markdown: str
    structured: bool = True  # False for plain text: `#` lines are not headings
