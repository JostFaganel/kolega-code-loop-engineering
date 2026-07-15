#!/usr/bin/env bash
# install.sh — drop loop engineering into any Kolega Code project
#
# Usage:
#   ./install.sh                    # install into current directory
#   ./install.sh /path/to/project   # install into a specific project
#
# Everything runs from the repo's own .venv — no system-wide pip needed.
# After running, open Kolega Code in that project and just type:
#   /loop Build a new feature
#   /loop Fix a bug

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$(pwd)}"
VENV="$REPO_ROOT/.venv"

echo "=== Kolega Code Loop Engineering — Install ==="
echo "  Repo:    $REPO_ROOT"
echo "  Target:  $TARGET"
echo ""

# 1. Create the skills directory in the target project
mkdir -p "$TARGET/.kolega/skills"

# 2. Symlink the bridge skill into the target project
BRIDGE_SRC="$REPO_ROOT/.kolega/skills/loop.md"
BRIDGE_DST="$TARGET/.kolega/skills/loop.md"

if [ -e "$BRIDGE_DST" ] && [ ! -L "$BRIDGE_DST" ]; then
    echo "⚠️  $BRIDGE_DST already exists (not a symlink). Skipping."
else
    ln -sf "$BRIDGE_SRC" "$BRIDGE_DST"
    echo "✓  Symlinked bridge: .kolega/skills/loop.md → repo"
fi

# 3. Set up the repo's own virtual environment
echo ""
echo "Setting up Python environment..."
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -e "$REPO_ROOT"
echo "✓  kolega-loop-state installed in repo .venv"

# 4. Verify
echo ""
if "$VENV/bin/loop-state" --help &>/dev/null; then
    echo "✓  loop-state CLI ready"
    echo "   → $VENV/bin/loop-state"
else
    echo "✗  loop-state failed to install"
    exit 1
fi

echo ""
echo "=== Done ==="
echo ""
echo "The agent will auto-install on first use. Nothing else to do."
echo "Open Kolega Code in $TARGET and type: /loop Build something"
