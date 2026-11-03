"""Scraper CLI (I-08, I-09, D-11).

    uv run python -m ingestion.scraper.cli --out data/corpus/odoo19-dev

Fetches the curated page list politely (pause between requests, identifiable User-Agent,
retries with backoff) and writes one Markdown snapshot per page with frontmatter
(url, title, fetched_at, license).
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
import yaml

from ingestion.parsers.frontmatter import dump_frontmatter
from ingestion.scraper.extract import extract_article

log = logging.getLogger("scraper")

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "config" / "odoo19_pages.yaml"
DEFAULT_USER_AGENT = "odoo-rag-assistant/0.1 (educational RAG project; polite scraper)"
ALLOWED_PREFIX = "/documentation/19.0/"


def snapshot_name(url: str) -> str:
    """`.../19.0/developer/reference/backend/orm.html` -> `reference__backend__orm.md`."""
    path = urlparse(url).path.removeprefix(ALLOWED_PREFIX).removeprefix("developer/")
    return path.removesuffix(".html").replace("/", "__") + ".md"


def load_pages(config_path: Path) -> tuple[dict[str, str], list[str]]:
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    base = cfg["base_url"]
    urls = [urljoin(base, p) for p in cfg["pages"]]
    for u in urls:
        if not urlparse(u).path.startswith(ALLOWED_PREFIX):
            raise ValueError(f"URL outside {ALLOWED_PREFIX}: {u}")
    return {"license": cfg["license"], "license_url": cfg["license_url"]}, urls


def fetch(client: httpx.Client, url: str, retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            resp = client.get(url)
            if resp.status_code in {429, 500, 502, 503, 504}:
                raise httpx.HTTPStatusError("retryable", request=resp.request, response=resp)
            resp.raise_for_status()
            return resp.text
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if attempt == retries:
                raise
            wait = 5 * attempt
            log.warning("%s failed (%s); retry %d in %ds", url, exc, attempt, wait)
            time.sleep(wait)
    raise AssertionError("unreachable")


def run(
    config: Path, out_dir: Path, *, delay: float, user_agent: str, only: str | None = None
) -> tuple[int, int]:
    meta, urls = load_pages(config)
    if only:
        urls = [u for u in urls if only in u]
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = failed = 0
    with httpx.Client(
        headers={"User-Agent": user_agent}, timeout=30.0, follow_redirects=True
    ) as client:
        for i, url in enumerate(urls):
            if i:
                time.sleep(delay)
            try:
                article = extract_article(fetch(client, url))
            except Exception:
                log.exception("failed: %s", url)
                failed += 1
                continue
            front = {
                "url": url,
                "title": article.title,
                "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "license": meta["license"],
                "license_url": meta["license_url"],
            }
            (out_dir / snapshot_name(url)).write_text(
                dump_frontmatter(front, article.markdown), encoding="utf-8"
            )
            ok += 1
            log.info("[%d/%d] %s", i + 1, len(urls), url)
    return ok, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=Path("data/corpus/odoo19-dev"))
    parser.add_argument("--delay", type=float, default=1.5, help="seconds between requests (>=1)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--only", help="only URLs containing this substring (testing)")
    args = parser.parse_args(argv)
    if args.delay < 1.0:
        parser.error("--delay must be >= 1 second (be polite to odoo.com)")
    logging.basicConfig(level="INFO", format="%(asctime)s %(name)s %(message)s")
    ok, failed = run(
        args.config, args.out, delay=args.delay, user_agent=args.user_agent, only=args.only
    )
    log.info("done: %d written, %d failed", ok, failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
