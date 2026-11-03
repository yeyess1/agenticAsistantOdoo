from __future__ import annotations

import pytest
from ingestion.scraper.extract import ExtractionError, extract_article

PAGE = """
<html><body><nav>menu</nav>
<main><article id="o_content"><div role="main">
<section id="orm-api">
<h1>ORM API<a class="headerlink" href="#orm-api" title="Permalink">¶</a></h1>
<p>Intro with <code class="o_code literal"><span class="pre">api.depends</span></code>
and a <a class="reference internal" href="#fields">link</a> and
<a class="reference external" href="https://example.com/x">external</a>.</p>
<section id="fields">
<h2>Fields<a class="headerlink" href="#fields" title="Permalink">¶</a></h2>
<div class="highlight-python notranslate"><div class="highlight"><pre><span></span><span class="k">def</span> <span class="nf">f</span><span class="p">():</span>
    <span class="k">return</span> <span class="mi">1</span>
</pre></div></div>
<div class="highlight-default notranslate"><div class="highlight"><pre>&lt;record id="x"/&gt;
</pre></div></div>
<ul><li><p>first</p></li><li><p>second</p><ul><li>nested</li></ul></li></ul>
<div class="admonition note alert alert-secondary"><p class="admonition-title">Note</p><p>Careful.</p></div>
<table><thead><tr><th>A</th><th>B</th></tr></thead><tbody><tr><td>1</td><td>2</td></tr></tbody></table>
<dl class="py class"><dt class="sig sig-object py" id="odoo.fields.Char">
<em class="property">class</em> <span class="sig-name">Char</span>
<a class="reference external" href="https://github.com/x"><span class="viewcode-link">[source]</span></a>
<a class="headerlink" href="#odoo.fields.Char">¶</a></dt>
<dd><p>Basic string field.</p>
<dl class="field-list simple"><dt class="field-odd">Parameters</dt><dd class="field-odd"><p>size</p></dd></dl>
</dd></dl>
</section></section>
</div></article></main><script>evil()</script></body></html>
"""


def test_extracts_title_and_structure() -> None:
    article = extract_article(PAGE)
    md = article.markdown
    assert article.title == "ORM API"
    assert "menu" not in md and "evil" not in md and "¶" not in md
    assert md.startswith("# ORM API {#orm-api}")
    assert "## Fields {#fields}" in md


def test_code_blocks_keep_language() -> None:
    md = extract_article(PAGE).markdown
    assert "```python\ndef f():\n    return 1\n```" in md
    assert '```xml\n<record id="x"/>\n```' in md  # unlabeled block, XML guessed


def test_inline_lists_tables_admonitions() -> None:
    md = extract_article(PAGE).markdown
    assert "Intro with `api.depends` and a link and [external](https://example.com/x)." in md
    assert "- first\n- second\n  - nested" in md
    assert "| A | B |\n|---|---|\n| 1 | 2 |" in md
    assert "> Note\n>\n> Careful." in md


def test_api_signature_becomes_anchored_heading() -> None:
    md = extract_article(PAGE).markdown
    assert "#### `class Char` {#odoo.fields.Char}" in md
    assert "**Parameters**" in md  # field-list label is not a heading
    assert "[source]" not in md


def test_page_without_article_fails() -> None:
    with pytest.raises(ExtractionError):
        extract_article("<html><body><p>hi</p></body></html>")
