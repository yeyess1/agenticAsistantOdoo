"""Hierarchical, structure-aware chunker (I-03, I-04, D-06).

Pipeline: Markdown -> sections split by H1-H3 (path kept in `section`) -> greedy packing of
blocks up to `size` tokens with `overlap` carry-over -> recursive split (paragraph, line,
sentence, word) only for oversized TEXT blocks. Fenced code blocks are never split: a
block larger than `size` becomes a chunk of its own. Sections smaller than `min_tokens`
are merged with a neighbour. Headings H4+ stay inside the text and only move the anchor.

Page markers `<!-- page:N -->` (emitted by the PDF parser) set `Chunk.page`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ingestion.chunking.tokenizer import TokenCounter

PAGE_MARKER = re.compile(r"^<!-- page:(\d+) -->$")
HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
EXPLICIT_ANCHOR = re.compile(r"\s*\{#([^}\s]+)\}\s*$")
FENCE = re.compile(r"^(`{3,}|~{3,})")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
PRIMARY_MAX_LEVEL = 3
JOIN_TOKENS = 2


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    section: str | None
    anchor: str | None
    page: int | None
    n_tokens: int


@dataclass
class _Unit:
    kind: str  # "text" | "code"
    text: str
    tokens: int
    anchor: str | None
    page: int | None


@dataclass
class _Section:
    path: list[str]
    anchor: str | None
    units: list[_Unit] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(u.tokens for u in self.units)


def slugify(text: str) -> str:
    """GitHub-style slug, used when a heading has no explicit `{#anchor}`."""
    slug = re.sub(r"[^\w\s-]", "", text.lower().replace("`", ""))
    return re.sub(r"[\s]+", "-", slug.strip())


def split_heading(raw: str) -> tuple[str, str]:
    """`'Title {#id}'` -> `('Title', 'id')`; without explicit anchor, the slug of the title."""
    m = EXPLICIT_ANCHOR.search(raw)
    if m:
        return raw[: m.start()].strip(), m.group(1)
    title = raw.strip()
    return title, slugify(title)


def _parse_blocks(markdown: str, structured: bool = True) -> list[tuple[str, str, int]]:
    """Return `(kind, text, level)` blocks: heading | code | text | page (`level` = heading)."""
    blocks: list[tuple[str, str, int]] = []
    buf: list[str] = []
    fence: str | None = None

    def flush_text() -> None:
        if buf and any(line.strip() for line in buf):
            blocks.append(("text", "\n".join(buf).strip("\n"), 0))
        buf.clear()

    for line in markdown.splitlines():
        if fence is not None:
            buf.append(line)
            closing = line.strip()
            if set(closing) == {fence[0]} and len(closing) >= len(fence):
                blocks.append(("code", "\n".join(buf), 0))
                buf.clear()
                fence = None
            continue
        m_fence = FENCE.match(line.lstrip()) if structured else None
        if m_fence:
            flush_text()
            fence = m_fence.group(1)
            buf.append(line)
            continue
        if PAGE_MARKER.match(line.strip()):
            flush_text()
            blocks.append(("page", line.strip(), 0))
            continue
        m_h = HEADING.match(line) if structured else None
        if m_h:
            flush_text()
            blocks.append(("heading", m_h.group(2), len(m_h.group(1))))
            continue
        if not line.strip():
            flush_text()
            continue
        buf.append(line)
    if buf:  # unterminated fence is still kept whole
        kind = "code" if fence is not None else "text"
        blocks.append((kind, "\n".join(buf).strip("\n"), 0))
    return blocks


def _split_oversized(text: str, size: int, counter: TokenCounter) -> list[str]:
    """Recursive split of a text block: lines -> sentences -> words. Pieces are <= `size`."""
    if counter.count(text) <= size:
        return [text]
    for splitter in (
        lambda t: t.split("\n"),
        lambda t: SENTENCE_SPLIT.split(t),
        lambda t: t.split(" "),
    ):
        parts = [p for p in splitter(text) if p.strip()]
        if len(parts) > 1:
            out: list[str] = []
            cur: list[str] = []
            for part in parts:
                for piece in _split_oversized(part, size, counter):
                    candidate = "\n".join([*cur, piece]) if cur else piece
                    if cur and counter.count(candidate) > size:
                        out.append("\n".join(cur))
                        cur = [piece]
                    else:
                        cur.append(piece)
            if cur:
                out.append("\n".join(cur))
            return out
    # a single unbreakable token run: cut by characters
    step = max(1, len(text) // (counter.count(text) // size + 1))
    return [text[i : i + step] for i in range(0, len(text), step)]


def _tail(text: str, overlap: int, counter: TokenCounter) -> str:
    """Trailing sentences/lines of `text` that fit in `overlap` tokens."""
    pieces = [p for p in re.split(r"(?<=[.!?])\s+|\n", text) if p.strip()]
    kept: list[str] = []
    total = 0
    for piece in reversed(pieces):
        n = counter.count(piece)
        if total + n > overlap:
            break
        kept.append(piece)
        total += n
    return " ".join(reversed(kept))


def _build_sections(
    markdown: str, counter: TokenCounter, size: int, structured: bool
) -> list[_Section]:
    sections: list[_Section] = []
    stack: list[tuple[int, str]] = []
    current = _Section(path=[], anchor=None)
    active_anchor: str | None = None
    page: int | None = None

    for kind, text, level in _parse_blocks(markdown, structured):
        if kind == "page":
            m = PAGE_MARKER.match(text)
            page = int(m.group(1)) if m else page
        elif kind == "heading" and level <= PRIMARY_MAX_LEVEL:
            sections.append(current)
            title, anchor = split_heading(text)
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            current = _Section(path=[t for _, t in stack], anchor=anchor)
            active_anchor = anchor
        elif kind == "heading":
            title, anchor = split_heading(text)
            active_anchor = anchor
            current.units.append(
                _Unit("text", "#" * level + " " + title, counter.count(title) + 1, anchor, page)
            )
        elif kind == "code":
            current.units.append(_Unit("code", text, counter.count(text), active_anchor, page))
        else:
            for piece in _split_oversized(text, size, counter):
                current.units.append(
                    _Unit("text", piece, counter.count(piece), active_anchor, page)
                )
    sections.append(current)
    # Drop sections without body (heading-only parents); their path lives in the children.
    return [s for s in sections if any(u.text.strip() for u in s.units)]


def _merge_small(sections: list[_Section], size: int, min_tokens: int) -> list[_Section]:
    merged: list[_Section] = []
    i = 0
    while i < len(sections):
        sec = sections[i]
        if sec.tokens < min_tokens:
            if merged and merged[-1].tokens + sec.tokens <= size:
                merged[-1].units.extend(_with_heading(sec))
                i += 1
                continue
            if i + 1 < len(sections) and sec.tokens + sections[i + 1].tokens <= size:
                nxt = sections[i + 1]
                nxt.units = [*_with_heading(sec), *nxt.units]
                i += 1
                continue
        merged.append(sec)
        i += 1
    return merged


def _with_heading(sec: _Section) -> list[_Unit]:
    """Units of a merged section, led by its own title so the text is not lost."""
    if not sec.path:
        return sec.units
    title = _Unit("text", f"## {sec.path[-1]}", len(sec.path[-1]) // 4 + 2, sec.anchor, None)
    first = sec.units[0] if sec.units else None
    title.page = first.page if first else None
    return [title, *sec.units]


def _pack(sec: _Section, size: int, overlap: int, counter: TokenCounter) -> list[tuple[_Unit, str]]:
    """Greedy packing of units into chunks. Returns `(first new unit, text)` per chunk."""
    out: list[tuple[_Unit, str]] = []
    cur: list[_Unit] = []
    cur_tokens = 0
    carry = ""
    carry_tokens = 0

    def emit() -> None:
        nonlocal cur, cur_tokens, carry, carry_tokens
        if not cur:
            return
        body = "\n\n".join(u.text for u in cur)
        out.append((cur[0], f"{carry}\n\n{body}" if carry else body))
        last = cur[-1]
        carry = _tail(last.text, overlap, counter) if last.kind == "text" and overlap else ""
        carry_tokens = counter.count(carry) + JOIN_TOKENS if carry else 0
        cur, cur_tokens = [], 0

    for unit in sec.units:
        if unit.kind == "code" and unit.tokens > size:
            emit()  # an oversized code block stands alone and is never split
            carry, carry_tokens = "", 0
            out.append((unit, unit.text))
            continue
        cost = unit.tokens + JOIN_TOKENS  # blocks are joined with a blank line
        if cur and carry_tokens + cur_tokens + cost > size:
            emit()
        if not cur and carry and carry_tokens + cost > size:
            carry, carry_tokens = "", 0
        cur.append(unit)
        cur_tokens += cost
    emit()
    return out


def chunk_markdown(
    markdown: str,
    counter: TokenCounter,
    *,
    size: int = 512,
    overlap: int = 64,
    min_tokens: int = 100,
    structured: bool = True,
) -> list[Chunk]:
    """Split normalized Markdown into chunks with section path, anchor and page."""
    sections = _merge_small(_build_sections(markdown, counter, size, structured), size, min_tokens)
    chunks: list[Chunk] = []
    for sec in sections:
        path = " > ".join(sec.path) if sec.path else None
        for first, text in _pack(sec, size, overlap, counter):
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=text.strip(),
                    section=path,
                    anchor=first.anchor or sec.anchor,
                    page=first.page,
                    n_tokens=counter.count(text),
                )
            )
    return chunks
