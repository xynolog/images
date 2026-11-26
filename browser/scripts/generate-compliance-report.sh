#!/bin/bash
set -e

# Thin wrapper for Browser compliance reporting
# Calls the SDK checkout's compliance scripts (SDK_REPO) with the Browser's paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC_DIR="$(cd "$SCRIPT_DIR/../src" && pwd)"
SYMBOLS_FILE="$SCRIPT_DIR/symbols.json"
REPORT_DIR="$REPO_ROOT/.compliance"
mkdir -p "$REPORT_DIR"
REPORT_FILE="$REPORT_DIR/BROWSER-COMPLIANCE.md"

# The SDK's compliance scripts
[[ -d "${SDK_REPO:?Set SDK_REPO to the SDK checkout whose compliance scripts audit the Browser.}/typescript/scripts/compliance" ]] || {
  echo "No compliance scripts at $SDK_REPO/typescript/scripts/compliance." >&2
  exit 2
}
DISCOVER="$SDK_REPO/typescript/scripts/compliance/discover-symbols.ts"
AUDIT="$SDK_REPO/typescript/scripts/compliance/batch-audit.ts"

echo "🔍 Discovering symbols in $SRC_DIR..."
npx tsx "$DISCOVER" "$SRC_DIR" "$SYMBOLS_FILE"

if command -v jq &> /dev/null; then
  SYMBOL_COUNT=$(jq length "$SYMBOLS_FILE")
  echo "✅ Found $SYMBOL_COUNT symbols"
else
  echo "✅ Symbols discovered"
fi

echo ""
echo "🔬 Running compliance audit..."
# The audit exits non-zero when a symbol fails. Its status is kept, so the
# report is still previewed below, and is this script's own.
audit_status=0
npx tsx "$AUDIT" "$SRC_DIR" "$SYMBOLS_FILE" > "$REPORT_FILE" || audit_status=$?

echo "📊 Compliance report generated: $REPORT_FILE"
echo ""

if [ -f "$REPORT_FILE" ]; then
  echo "Report preview:"
  echo "==============="
  head -n 20 "$REPORT_FILE"
  echo ""
  echo "Full report available at: $REPORT_FILE"
fi

exit "$audit_status"
