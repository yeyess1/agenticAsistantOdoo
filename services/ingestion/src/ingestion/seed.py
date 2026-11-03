"""Seed the index from the corpus snapshot through the HTTP endpoint (I-11, D-11).

    python -m ingestion.seed /data/corpus/odoo19-dev [--url http://localhost:8001] [--force]

Deliberately goes through `POST /documents` (not an internal shortcut). Re-running is
idempotent: unchanged documents answer `action=unchanged` without being re-embedded.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import httpx

from ingestion.parsers import SUPPORTED_SUFFIXES

log = logging.getLogger("seed")


def corpus_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)


def seed(
    directory: Path, url: str, *, force: bool, timeout: float
) -> tuple[int, int, dict[str, int]]:
    files = corpus_files(directory)
    counts: dict[str, int] = {"created": 0, "updated": 0, "unchanged": 0}
    chunks = failed = 0
    started = time.perf_counter()
    with httpx.Client(base_url=url, timeout=timeout) as client:
        for i, path in enumerate(files, start=1):
            t0 = time.perf_counter()
            try:
                resp = client.post(
                    "/documents",
                    files={"file": (path.name, path.read_bytes())},
                    data={"force": str(force).lower()},
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                failed += 1
                log.error("[%d/%d] %s FAILED: %s", i, len(files), path.name, exc)
                continue
            body = resp.json()
            counts[body["action"]] += 1
            chunks += body["n_chunks"]
            log.info(
                "[%d/%d] %-62s %-9s %4d chunks %6.1fs",
                i,
                len(files),
                path.name,
                body["action"],
                body["n_chunks"],
                time.perf_counter() - t0,
            )
    log.info(
        "done in %.0fs: %d files, %d chunks, %s, %d failed",
        time.perf_counter() - started,
        len(files),
        chunks,
        counts,
        failed,
    )
    return len(files), failed, counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a corpus folder via POST /documents")
    parser.add_argument("directory", type=Path)
    parser.add_argument("--url", default="http://localhost:8001")
    parser.add_argument("--force", action="store_true", help="reindex unchanged documents too")
    parser.add_argument("--timeout", type=float, default=1800.0, help="per-file HTTP timeout (s)")
    args = parser.parse_args(argv)
    logging.basicConfig(level="INFO", format="%(asctime)s %(message)s")
    if not args.directory.is_dir():
        parser.error(f"not a directory: {args.directory}")
    _, failed, _ = seed(args.directory, args.url, force=args.force, timeout=args.timeout)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
