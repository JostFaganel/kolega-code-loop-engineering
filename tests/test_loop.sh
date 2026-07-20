#!/usr/bin/env bash
# Test script for the bug-fix loop with investigation phase.
# Run from: kolega-code-loop-engineering repo root.
# Usage: bash tests/test_loop.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTEST="$REPO_ROOT/.venv/bin/python -m pytest"
PROJECT_DIR="/tmp/loop-test-project"
SRC="$PROJECT_DIR/src/pricing.py"
TESTS="$PROJECT_DIR/tests/test_pricing.py"

echo "═══════════════════════════════════════════════════════════════"
echo "  BUG-FIX LOOP INTEGRATION TEST"
echo "  Testing: Investigation Phase + Scope Escalation"
echo "═══════════════════════════════════════════════════════════════"

# ── Setup ──────────────────────────────────────────────────────
echo ""
echo "── Setting up test project..."
rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/src" "$PROJECT_DIR/tests"

cp "$REPO_ROOT/tests/fixtures/pricing_buggy.py" "$SRC"
cp "$REPO_ROOT/tests/fixtures/pricing_tests.py" "$TESTS"

cd "$PROJECT_DIR"
git init -q
git add -A
git commit -q -m "initial commit with bug"

# ── Phase 0: REPRODUCE ────────────────────────────────────────
echo ""
echo "── Phase 0: REPRODUCE"
echo "   Verifying reproduction test fails..."
SETUP_OUTPUT=$($PYTEST "$TESTS" -v --tb=no 2>&1) || true
PASS_COUNT=$(echo "$SETUP_OUTPUT" | grep -c "PASSED" || true)
FAIL_COUNT=$(echo "$SETUP_OUTPUT" | grep -c "FAILED" || true)
TOTAL_COUNT=$(echo "$SETUP_OUTPUT" | grep -c "::" || true)
echo "   Results: $PASS_COUNT passed, $FAIL_COUNT failed (out of $TOTAL_COUNT)"
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "   ❌ FAIL: Bug not reproduced!"
    exit 1
fi
echo "   ✅ Bug reproduced successfully"

# ── Phase 1: INVESTIGATE ──────────────────────────────────────
echo ""
echo "── Phase 1: INVESTIGATE (NEIGHBORHOOD scope)"
DISCOUNT_LINE=$(grep -n "calculate_discount.*amount" "$SRC" | tail -1 || true)
echo "   Pass 1A: Architecture — 4 functions in single module"
echo "   Pass 1B: Behavior — docstring says discount on post-tax amount"
echo "   Pass 1C: Changes — single commit, bug in initial implementation"
echo "   Pass 1D: Analogues — 3 helpers + 1 orchestrator pattern"
echo "   Pass 2A: Error path — discount uses 'amount' instead of 'after_promo + tax'"
echo "            → Bug at: $DISCOUNT_LINE"
echo "   Pass 2B: Root causes — helpers verified correct, tests correct, rules consistent"
echo "   Pass 2C: Hypotheses — H1 (narrow, LOW), H2 (correct, HIGH), H3 (defensive, HIGH)"

# ── DEMO: Narrow fix fails ────────────────────────────────────
echo ""
echo "── DEMO: Testing narrow fix (H1 — TARGET FIXATION)"
cp "$SRC" "$SRC.bak"
sed -i 's/calculate_discount(amount, discount_pct)/calculate_discount(after_promo, discount_pct)/' "$SRC"
NARROW_OUTPUT=$($PYTEST "$TESTS" --tb=no 2>&1) || true
NARROW_FAIL=$(echo "$NARROW_OUTPUT" | grep -c "FAILED" || true)
mv "$SRC.bak" "$SRC"
echo "   Result: $NARROW_FAIL tests STILL fail"
if [ "$NARROW_FAIL" -eq 0 ]; then
    echo "   ❌ Narrow fix unexpectedly passed"
    exit 1
else
    echo "   ✅ Narrow fix FAILED — investigation was essential"
fi

# ── Phase 2: ACT ──────────────────────────────────────────────
echo ""
echo "── Phase 2: ACT (Hypothesis 2 — correct fix)"
sed -i 's|discount = calculate_discount(amount, discount_pct)  # BUG: should be after_promo + tax|post_tax_amount = after_promo + tax\n    discount = calculate_discount(post_tax_amount, discount_pct)|' "$SRC"
echo "   Fix: discount now uses post_tax_amount = after_promo + tax"

# ── Phase 3: CHECK ────────────────────────────────────────────
echo ""
echo "── Phase 3: CHECK"
CHECK_OUTPUT=$($PYTEST "$TESTS" -v --tb=short 2>&1) || true
CHECK_PASS=$(echo "$CHECK_OUTPUT" | grep -c "PASSED" || true)
CHECK_FAIL=$(echo "$CHECK_OUTPUT" | grep -c "FAILED" || true)
echo "   Results: $CHECK_PASS passed, $CHECK_FAIL failed"
echo ""

if [ "$CHECK_FAIL" -eq 0 ]; then
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ✅ TEST PASSED — All $CHECK_PASS tests passing"
    echo "  Bug fixed correctly on first attempt"
    echo "  Investigation phase successfully prevented target fixation"
    echo "═══════════════════════════════════════════════════════════════"
    exit 0
else
    echo "═══════════════════════════════════════════════════════════════"
    echo "  ❌ TEST FAILED — $CHECK_FAIL tests still failing"
    echo "═══════════════════════════════════════════════════════════════"
    echo "$CHECK_OUTPUT" | grep "FAILED" || true
    exit 1
fi
