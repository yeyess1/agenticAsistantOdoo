"""Domain allowlist for the forum tools (D-07, ARCHITECTURE §8)."""

from __future__ import annotations

from urllib.parse import urlparse

FORUM_PATH_PREFIX = "/forum/"


def is_allowed_url(url: str, domains: list[str]) -> bool:
    """Only https(s) URLs on an allowed host under `/forum/`.

    Search never touches the forum's internal search page (robots.txt, RK-03): a query
    string with `search=` is rejected as well.
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in {d.lower() for d in domains}:
        return False
    if not parsed.path.startswith(FORUM_PATH_PREFIX):
        return False
    return "search=" not in parsed.query
