#!/usr/bin/env bash
# verify_api.sh — confirm the REST API daemon is running and functional
set -euo pipefail

BASE="${1:-http://127.0.0.1:7070}"
OK=0
FAIL=0

step() { echo -n "  $1 … "; }
pass() { echo "OK"; OK=$((OK+1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "[verify_api] Checking REST API at $BASE"

# 1. Health
step "GET /health"
H=$(curl -fsS "$BASE/health" 2>/dev/null || echo "UNREACHABLE")
if echo "$H" | grep -q '"ok"'; then
    pass
else
    fail "$H"
fi

# 2. DBus connected?
step "dbus_connected == true"
if echo "$H" | grep -q '"dbus_connected":true'; then
    pass
else
    fail "dbus not connected"
fi

# 3. State
step "GET /state"
S=$(curl -fsS "$BASE/state" 2>/dev/null || echo "ERROR")
if echo "$S" | grep -q '"screen_width"'; then
    pass
else
    fail "$S"
fi

# 4. Windows
step "GET /windows"
W=$(curl -fsS "$BASE/windows" 2>/dev/null || echo "ERROR")
if echo "$W" | python3 -c "import sys,json;json.load(sys.stdin)" 2>/dev/null; then
    pass
else
    fail "invalid JSON"
fi

# 5. Workspaces
step "GET /workspaces"
WS=$(curl -fsS "$BASE/workspaces" 2>/dev/null || echo "ERROR")
if echo "$WS" | grep -q '"index"'; then
    pass
else
    fail "$WS"
fi

# 6. Keyboard endpoint reachable (just check 422 for missing body, not 404)
step "POST /input/keyboard/key reachable"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE/input/keyboard/key" 2>/dev/null || echo "000")
if [[ "$CODE" == "422" || "$CODE" == "200" ]]; then
    pass
else
    fail "HTTP $CODE"
fi

echo
echo "  Result: $OK passed, $FAIL failed"
exit $FAIL
