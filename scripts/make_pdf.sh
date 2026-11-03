#!/usr/bin/env bash
# Render the Odoo "Coding guidelines" page to PDF with headless Chrome/Chromium (I-10, D-11).
# The PDF is versioned in data/corpus/odoo19-dev/, so Chromium is not needed in any image.
#
#   scripts/make_pdf.sh [output.pdf]
set -euo pipefail

URL="https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html"
OUT="${1:-data/corpus/odoo19-dev/coding_guidelines.pdf}"
CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || command -v chromium-browser || true)}"

if [[ -z "$CHROME" ]]; then
  echo "google-chrome/chromium not found (set CHROME=/path/to/binary)" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUT")"
"$CHROME" --headless=new --disable-gpu --no-sandbox \
  --user-agent="odoo-rag-assistant/0.1 (educational RAG project; polite scraper)" \
  --no-pdf-header-footer --print-to-pdf="$OUT" "$URL" 2>/dev/null
echo "wrote $OUT"
