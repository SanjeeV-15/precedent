#!/bin/sh
# One-time setup for native vault mode: Relate opens the notes folder itself as the store.
# Needs the Relate command-line tool (https://relatedb.ai, installs to ~/.local/bin).
#
# Relate rewrites every note into its own canonical format when it first opens a folder (same content, different key order
# and quoting), so this works on a COPY of the vault (vault_native/), not on the committed notes.
#   sh scripts/native_init.sh [copy-folder]
set -e
cd "$(dirname "$0")/.."
VAULT=${1:-vault_native}
RELATE=$(command -v relate || echo "$HOME/.local/bin/relate")
[ -x "$RELATE" ] || { echo "relate CLI not found; install it from https://relatedb.ai first"; exit 1; }
[ -d "$VAULT" ] || cp -R vault "$VAULT"
"$RELATE" --snapshot-format markdown --markdown-body-properties text --database "$VAULT" \
  -c "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY n DESC" 2>&1 | grep -v "usage metrics"
echo "Native vault ready. Try:  python -m precedent --store $VAULT conflicts"
