"""Chunking calibration over the corpus snapshot (I-12, D-06).

    uv run python -m ingestion.calibrate data/corpus/odoo19-dev

Prints the real distribution of section sizes (H1-H3) and, for several size/overlap
candidates, how the chunker behaves (chunk count, size percentiles, tiny chunks, oversized
code blocks). No network or embedding service needed beyond the cached tokenizer.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from common.settings import get_settings

from ingestion.chunking.chunker import (
    Chunk,
    _build_sections,
    chunk_markdown,
)
from ingestion.chunking.tokenizer import HFTokenCounter, TokenCounter, load_token_counter
from ingestion.parsers import parse_document

CANDIDATES = [(256, 32), (384, 48), (512, 64), (768, 96), (1024, 128)]


def percentile(values: list[int], q: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def describe(label: str, values: list[int], limit: int | None = None) -> str:
    over = f", >{limit}: {sum(v > limit for v in values) / len(values):.0%}" if limit else ""
    return (
        f"{label:<28} n={len(values):<5} mean={statistics.mean(values):6.0f} "
        f"p50={percentile(values, 0.5):5d} p90={percentile(values, 0.9):5d} "
        f"p99={percentile(values, 0.99):5d} max={max(values):6d}{over}"
    )


def load_corpus(directory: Path) -> list[tuple[str, str, bool]]:
    docs = []
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in {".md", ".pdf", ".txt"}:
            parsed = parse_document(path.read_bytes(), path.name)
            docs.append((path.name, parsed.markdown, parsed.structured))
    return docs


def section_sizes(docs: list[tuple[str, str, bool]], counter: TokenCounter) -> list[int]:
    sizes: list[int] = []
    for _, md, structured in docs:
        # a huge `size` keeps sections whole, so we measure them as authored
        sizes += [s.tokens for s in _build_sections(md, counter, 10**9, structured)]
    return sizes


def evaluate(
    docs: list[tuple[str, str, bool]],
    counter: TokenCounter,
    size: int,
    overlap: int,
    min_tokens: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for _, md, structured in docs:
        chunks += chunk_markdown(
            md, counter, size=size, overlap=overlap, min_tokens=min_tokens, structured=structured
        )
    return chunks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    settings = get_settings()
    counter: HFTokenCounter = load_token_counter(
        settings.embeddings_model, settings.tokenizer_cache_dir
    )
    docs = load_corpus(args.directory)
    print(f"{len(docs)} documents")
    print(describe("sections (H1-H3, tokens)", section_sizes(docs, counter), 512))
    print()
    print("size/overlap  chunks   mean   p50   p90   p99   max  <100tok  >size")
    for size, overlap in CANDIDATES:
        chunks = evaluate(docs, counter, size, overlap, settings.chunk_min_tokens)
        toks = [c.n_tokens for c in chunks]
        tiny = sum(t < settings.chunk_min_tokens for t in toks) / len(toks)
        big = sum(t > size for t in toks)
        mark = " <- chosen" if (size, overlap) == (512, 64) else ""
        print(
            f"{size:>5}/{overlap:<4}  {len(chunks):>6} {statistics.mean(toks):6.0f} "
            f"{percentile(toks, 0.5):5d} {percentile(toks, 0.9):5d} {percentile(toks, 0.99):5d} "
            f"{max(toks):5d}  {tiny:6.0%}  {big:5d}{mark}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
