"""YAML frontmatter for Markdown files (I-09)."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return `(metadata, body)`. Text without a valid frontmatter block is returned as-is."""
    m = _FM.match(text)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[m.end() :]


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    head = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True, width=1000).strip()
    return f"---\n{head}\n---\n\n{body}"
