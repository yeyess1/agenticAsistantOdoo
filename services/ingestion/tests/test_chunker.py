from __future__ import annotations

import re

from ingestion.chunking.chunker import chunk_markdown, slugify, split_heading
from ingestion.chunking.tokenizer import CharTokenCounter


def para(word: str, n: int) -> str:
    return " ".join(f"{word}{i}." for i in range(n))


def code(lines: int, lang: str = "python") -> str:
    body = "\n".join(f"    value_{i} = compute({i})  # step {i}" for i in range(lines))
    return f"```{lang}\n{body}\n```"


def fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```[a-z]*\n.*?\n```", text, flags=re.DOTALL)


def test_split_heading_and_slug() -> None:
    assert split_heading("Fields {#odoo.fields}") == ("Fields", "odoo.fields")
    assert split_heading("Computed Fields") == ("Computed Fields", "computed-fields")
    assert slugify("What's `new`?") == "whats-new"


def test_sections_get_path_and_anchor(counter: CharTokenCounter) -> None:
    md = (
        f"# Guide {{#guide}}\n\n## Models {{#models}}\n\n{para('m', 60)}\n\n"
        f"### Fields {{#fields}}\n\n{para('f', 60)}\n\n## Views {{#views}}\n\n{para('v', 60)}\n"
    )
    chunks = chunk_markdown(md, counter, size=512, overlap=32, min_tokens=20)
    by_section = {c.section: c for c in chunks}
    assert set(by_section) == {"Guide > Models", "Guide > Models > Fields", "Guide > Views"}
    assert by_section["Guide > Models > Fields"].anchor == "fields"
    assert by_section["Guide > Views"].anchor == "views"
    assert all(c.page is None for c in chunks)
    # heading-only parent (H1 "Guide") produces no chunk of its own
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_code_block_is_never_split(counter: CharTokenCounter) -> None:
    blocks = [code(12, "python"), code(15, "xml"), code(9, "javascript")]
    md = "# Doc\n\n## Section\n\n" + "\n\n".join(f"{para('p', 40)}\n\n{b}" for b in blocks)
    chunks = chunk_markdown(md, counter, size=120, overlap=16, min_tokens=10)
    assert len(chunks) > 3  # the section really was split
    found = [b for c in chunks for b in fenced_blocks(c.text)]
    for block in blocks:
        # every original block appears whole at least once (overlap never carries code)
        assert block in found
    for c in chunks:  # no chunk contains a dangling, unbalanced fence
        assert c.text.count("```") % 2 == 0


def test_oversized_code_block_stands_alone(counter: CharTokenCounter) -> None:
    big = code(80)
    assert counter.count(big) > 200
    md = f"# Doc\n\n## S\n\n{para('a', 30)}\n\n{big}\n\n{para('b', 30)}\n"
    chunks = chunk_markdown(md, counter, size=200, overlap=16, min_tokens=10)
    holders = [c for c in chunks if "value_0 =" in c.text]
    assert len(holders) == 1
    assert holders[0].text == big  # alone, untouched, even though > size
    assert holders[0].n_tokens > 200


def test_headings_inside_code_are_not_sections(counter: CharTokenCounter) -> None:
    md = "# Doc\n\n## Real\n\ntext before\n\n```python\n# not a heading\n## neither\nx = 1\n```\n"
    chunks = chunk_markdown(md, counter, size=512, overlap=0, min_tokens=1)
    assert [c.section for c in chunks] == ["Doc > Real"]
    assert "## neither" in chunks[0].text


def test_long_section_is_split_with_overlap(counter: CharTokenCounter) -> None:
    paragraphs = [para(f"w{i}x", 25) for i in range(12)]
    md = "# Doc\n\n## Long\n\n" + "\n\n".join(paragraphs)
    chunks = chunk_markdown(md, counter, size=150, overlap=30, min_tokens=10)
    assert len(chunks) >= 3
    assert all(c.section == "Doc > Long" for c in chunks)
    assert all(c.n_tokens <= 150 + 4 for c in chunks)
    # overlap: the tail of chunk i reappears at the start of chunk i+1
    tail = chunks[0].text.split()[-1]
    assert tail in chunks[1].text.split()[:15]


def test_oversized_paragraph_is_recursively_split(counter: CharTokenCounter) -> None:
    md = "# Doc\n\n## Wall\n\n" + para("s", 400)
    chunks = chunk_markdown(md, counter, size=100, overlap=10, min_tokens=5)
    assert len(chunks) > 3
    assert all(c.n_tokens <= 100 + 4 for c in chunks)


def test_small_sections_are_merged_with_neighbour(counter: CharTokenCounter) -> None:
    md = (
        f"# Doc\n\n## Big\n\n{para('b', 40)}\n\n## Tiny\n\nshort note.\n\n"
        f"## Other\n\n{para('o', 40)}\n"
    )
    chunks = chunk_markdown(md, counter, size=512, overlap=0, min_tokens=30)
    assert [c.section for c in chunks] == ["Doc > Big", "Doc > Other"]
    assert "short note." in chunks[0].text  # kept, not lost
    assert "## Tiny" in chunks[0].text


def test_h4_headings_move_the_anchor(counter: CharTokenCounter) -> None:
    entries = "\n\n".join(f"#### `api_{i}()` {{#api.{i}}}\n\n{para('e', 30)}" for i in range(8))
    md = f"# Ref {{#ref}}\n\n## API {{#api}}\n\n{entries}\n"
    chunks = chunk_markdown(md, counter, size=120, overlap=0, min_tokens=10)
    anchors = [c.anchor for c in chunks]
    assert anchors[0] == "api.0"  # first chunk starts at the first entry
    assert len(set(anchors)) > 1  # deep entries are addressable, not just the section
    assert all(c.section == "Ref > API" for c in chunks)


def test_page_markers_set_chunk_page(counter: CharTokenCounter) -> None:
    md = (
        f"<!-- page:1 -->\n\n# Doc\n\n## A\n\n{para('a', 40)}\n\n"
        f"<!-- page:2 -->\n\n## B\n\n{para('b', 40)}\n"
    )
    chunks = chunk_markdown(md, counter, size=512, overlap=0, min_tokens=10)
    assert [(c.section, c.page) for c in chunks] == [("Doc > A", 1), ("Doc > B", 2)]


def test_plain_text_is_not_structured(counter: CharTokenCounter) -> None:
    text = "# not a heading\n\n" + "\n\n".join(para(f"t{i}", 30) for i in range(6))
    chunks = chunk_markdown(text, counter, size=100, overlap=10, min_tokens=5, structured=False)
    assert len(chunks) > 2
    assert all(c.section is None and c.anchor is None for c in chunks)
    assert chunks[0].text.startswith("# not a heading")


def test_empty_markdown_yields_no_chunks(counter: CharTokenCounter) -> None:
    assert chunk_markdown("\n\n", counter) == []
    assert chunk_markdown("# Only a title\n", counter) == []
