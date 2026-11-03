"""Sphinx HTML -> Markdown (I-08, D-06, D-11).

Keeps what the chunker and the citations need:
- headings H1..H6 with their `#id` anchor written as ``# Title {#anchor}``;
- fenced code blocks tagged with their language;
- Sphinx API signatures (`<dt id=...>`) as H4 headings with their own anchor, so deep
  entries of the autodoc-generated reference pages stay addressable.
Everything else (lists, tables, admonitions, inline markup) is flattened to plain Markdown.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString, PageElement, Tag

_WS = re.compile(r"\s+")
_LANG_CLASS = re.compile(r"highlight-([\w+-]+)")
_LANG_ALIASES = {
    "python3": "python",
    "pycon": "python",
    "js": "javascript",
    "console": "bash",
    "shell": "bash",
    "sh": "bash",
    "text": "",
    "none": "",
    "default": "",
}
_DROP_CLASSES = {"headerlink", "viewcode-link", "toctree-wrapper", "linenos"}
_SKIP_TAGS = {"script", "style", "nav", "img", "svg", "button", "form"}
_ADMONITION_CLASSES = {"admonition", "alert"}


def _classes(tag: Tag) -> set[str]:
    raw = tag.get("class")
    if isinstance(raw, str):
        return set(raw.split())
    return set(raw or [])


def _drop(tag: Tag) -> bool:
    return tag.name in _SKIP_TAGS or bool(_classes(tag) & _DROP_CLASSES)


def _clean(text: str) -> str:
    return _WS.sub(" ", text).strip()


def inline(node: PageElement) -> str:
    """Flatten a node to a single line of inline Markdown."""
    if isinstance(node, NavigableString):
        return _WS.sub(" ", str(node))
    if not isinstance(node, Tag) or _drop(node):
        return ""
    name = node.name
    inner = "".join(inline(c) for c in node.children)
    if name == "code":
        text = _clean(node.get_text())
        return f"`{text}`" if text else ""
    if name in {"strong", "b"}:
        return f"**{inner.strip()}**" if inner.strip() else ""
    if name in {"em", "i"}:
        return f"*{inner.strip()}*" if inner.strip() else ""
    if name == "a":
        href = str(node.get("href", ""))
        if href.startswith("http") and "odoo.com/documentation" not in href and inner.strip():
            return f"[{inner.strip()}]({href})"
        return inner
    if name == "br":
        return " "
    return inner


def _language(pre: Tag) -> str:
    for parent in pre.parents:
        if not isinstance(parent, Tag):
            continue
        for cls in _classes(parent):
            m = _LANG_CLASS.fullmatch(cls)
            if m:
                lang = m.group(1)
                if lang == "default":
                    return _guess_language(pre.get_text())
                return _LANG_ALIASES.get(lang, lang)
    return _guess_language(pre.get_text())


def _guess_language(code: str) -> str:
    """Sphinx tags unlabeled blocks `default`; Odoo's default highlighter is Python."""
    stripped = code.lstrip()
    if stripped.startswith("<"):
        return "xml"
    if stripped.startswith(("$", "./", "odoo-bin", "pip ", "sudo ")):
        return "bash"
    return "python"


def code_block(pre: Tag) -> str:
    code = pre.get_text().strip("\n").rstrip()
    fence = "```"
    while fence in code:
        fence += "`"
    return f"{fence}{_language(pre)}\n{code}\n{fence}"


def _anchor(tag: Tag) -> str | None:
    link = tag.find("a", class_="headerlink")
    if isinstance(link, Tag):
        href = str(link.get("href", ""))
        if href.startswith("#") and len(href) > 1:
            return href[1:]
    own = tag.get("id")
    if isinstance(own, str) and own:
        return own
    parent = tag.parent
    if isinstance(parent, Tag) and parent.name == "section":
        pid = parent.get("id")
        if isinstance(pid, str) and pid:
            return pid
    return None


def _heading(level: int, text: str, anchor: str | None) -> str:
    suffix = f" {{#{anchor}}}" if anchor else ""
    return f"{'#' * level} {text}{suffix}"


def _quote(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.split("\n"))


def _prefix(lines: str, first: str, rest: str) -> str:
    parts = lines.split("\n")
    return "\n".join([first + parts[0], *(rest + p if p else p for p in parts[1:])])


def _list(tag: Tag, ordered: bool) -> str:
    items: list[str] = []
    n = 0
    for li in tag.find_all("li", recursive=False):
        n += 1
        body = ""
        for block in blocks(li):
            tight = block.startswith(("- ", "1. ")) and body  # nested list right under its item
            body += ("\n" if tight else "\n\n" if body else "") + block
        if not body:
            continue
        marker = f"{n}. " if ordered else "- "
        items.append(_prefix(body, marker, " " * len(marker)))
    return "\n".join(items)


def _table(tag: Tag) -> str:
    rows: list[list[str]] = []
    for tr in tag.find_all("tr"):
        cells = [_clean(inline(c)).replace("|", "\\|") for c in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    lines += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(lines)


def _dt_text(dt: Tag) -> str:
    parts = []
    for c in dt.children:
        if isinstance(c, Tag) and (_drop(c) or "viewcode-link" in str(c.get("class", ""))):
            continue
        parts.append(c.get_text() if isinstance(c, Tag) else str(c))
    text = _clean("".join(parts)).replace("[source]", "").replace("¶", "")
    return _clean(text)


def blocks(node: Tag) -> list[str]:
    """Render the block-level children of `node` as Markdown chunks."""
    out: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        text = _clean("".join(pending))
        pending.clear()
        if text:
            out.append(text)

    for child in node.children:
        if isinstance(child, NavigableString):
            pending.append(str(child))
            continue
        if not isinstance(child, Tag) or _drop(child):
            continue
        name = child.name
        cls = _classes(child)
        if name in {"strong", "b", "em", "i", "code", "a", "span"}:
            pending.append(inline(child))
            continue
        flush()
        if name and re.fullmatch(r"h[1-6]", name):
            text = _clean(inline(child)).replace("¶", "")
            if text:
                out.append(_heading(int(name[1]), text, _anchor(child)))
        elif name == "p":
            text = _clean(inline(child))
            if text:
                out.append(text)
        elif name == "pre":
            out.append(code_block(child))
        elif name in {"ul", "ol"}:
            text = _list(child, ordered=name == "ol")
            if text:
                out.append(text)
        elif name == "table":
            text = _table(child)
            if text:
                out.append(text)
        elif name == "blockquote":
            inner = "\n\n".join(blocks(child))
            if inner:
                out.append(_quote(inner))
        elif name == "dl":
            out.extend(_definition_list(child))
        elif name == "div" and cls & _ADMONITION_CLASSES:
            inner = "\n\n".join(blocks(child))
            if inner:
                out.append(_quote(inner))
        elif name == "div" and any(_LANG_CLASS.fullmatch(c) for c in cls):
            pre = child.find("pre")
            if isinstance(pre, Tag):
                out.append(code_block(pre))
        else:  # div, section, article, dd, li, ... : transparent containers
            out.extend(blocks(child))
    flush()
    return out


def _definition_list(dl: Tag) -> list[str]:
    out: list[str] = []
    for child in dl.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "dt":
            text = _dt_text(child)
            anchor = child.get("id")
            if text and isinstance(anchor, str) and anchor:
                out.append(_heading(4, f"`{text}`", anchor))
            elif text:  # field-list labels ("Parameters", "Returns", ...): not headings
                out.append(f"**{text}**")
        elif child.name == "dd":
            out.extend(blocks(child))
    return out


def html_to_markdown(root: Tag) -> str:
    return "\n\n".join(blocks(root)).strip() + "\n"


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
