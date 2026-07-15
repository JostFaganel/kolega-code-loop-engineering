#!/usr/bin/env bash
# install.sh — drop loop engineering into any Kolega Code project
#
# Usage:
#   ./install.sh                    # install into current directory
#   ./install.sh /path/to/project   # install into a specific project
#
# After running, open Kolega Code in that project and just type:
#   /loop Build a new feature
#   /loop Fix a bug

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-$(pwd)}"

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
    echo "✓  Symlinked bridge skill: .kolega/skills/loop.md → repo"
fi

# 3. Install the Python state manager
echo ""
echo "Installing kolega-loop-state..."
cd "$REPO_ROOT"
pip install -e . 2>/dev/null || pip install --break-system-packages -e . 2>/dev/null || {
    echo "⚠️  pip install failed. Try manually:"
    echo "   cd $REPO_ROOT && pip install -e ."
}

# 4. Verify
echo ""
if command -v loop-state &>/dev/null; then
    echo "✓  loop-state CLI ready"
    loop-state --help 2>&1 | head -1
else
    echo "⚠️  loop-state not on PATH. Use the repo's venv:"
    echo "   $REPO_ROOT/.venv/bin/loop-state"
fi

echo ""
echo "=== Done ==="
echo "Open Kolega Code in $TARGET and type: /loop Build something"
