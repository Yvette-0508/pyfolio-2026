#!/bin/sh
# Render the HTML report to PDF with headless Chrome.
# Usage: ./render_pdf.sh [out.pdf]
set -e

REPORT="$(cd "$(dirname "$0")/.." && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC="$REPORT/output/ibkr_results.html"
OUT="${1:-$REPORT/output/ibkr_report_$(date +%Y-%m-%d).pdf}"

# Expand collapsed <details> sections so the tear sheet prints too.
TMP="$(mktemp -t ibkr_report).html"
sed 's/<details>/<details open>/' "$SRC" > "$TMP"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$TMP"
rm -f "$TMP"
echo "wrote $OUT"
