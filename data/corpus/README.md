# Corpus: Odoo 19 Developer documentation (snapshot)

`odoo19-dev/` holds a curated snapshot (58 pages) of the Odoo 19.0 Developer documentation
plus one PDF, used as the knowledge base of the RAG assistant.

## Attribution and license

- Source: Odoo documentation, https://www.odoo.com/documentation/19.0/ (repository
  https://github.com/odoo/documentation), copyright Odoo S.A.
- License: [Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).
- Changes: each page was converted from rendered HTML to Markdown (navigation removed, code
  blocks and heading anchors kept). Every file carries its original `url`, `title`,
  `fetched_at` and `license` in its frontmatter. The derived files remain under CC BY-SA 4.0.
- `odoo19-dev/coding_guidelines.pdf` is the page
  https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html
  rendered to PDF with headless Chrome (`scripts/make_pdf.sh`): a PDF generated from the
  official documentation, used to exercise PDF ingestion with page numbers.

## Reproduce

```bash
uv run python -m ingestion.scraper.cli --out data/corpus/odoo19-dev   # page list: services/ingestion/config/odoo19_pages.yaml
scripts/make_pdf.sh                                                   # coding_guidelines.pdf
make seed                                                             # index everything through POST /documents
```

The scraper pauses between requests, sends an identifiable User-Agent and only touches the
listed `/documentation/19.0/` pages.
