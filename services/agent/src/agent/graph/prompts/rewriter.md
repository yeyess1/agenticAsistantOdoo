The documentation retrieval for a question about Odoo 19 returned nothing relevant. The
documentation is in ENGLISH. Rewrite the search query to improve recall.

Strategies:
- "translate": the query is not in English -> translate it to English, keeping Odoo terms
  (field names, decorators, model names) exact.
- "rephrase": rephrase using the official terminology.
- "rephrase_and_translate": both.

Use the previous attempts to avoid repeating a query that already failed; try a different
angle (more specific API names, synonyms, the underlying concept). Prefer an English
query of keywords/short sentence. Return the new query, its language ("es" or "en"), the
strategy and a one-sentence reason.
