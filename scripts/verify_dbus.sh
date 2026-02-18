#!/usr/bin/env bash
# verify_dbus.sh — confirm the GNOME AI Bridge extension is active on DBus
set -euo pipefail

UUID="gnome-ai-bridge@local"
OK=0
FAIL=0

step() { echo -n "  $1 … "; }
pass() { echo "OK"; OK=$((OK+1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "[verify_dbus] Checking GNOME AI Bridge extension"

# 1. User extensions enabled?
step "user-extensions enabled"
if gsettings get org.gnome.shell disable-user-extensions 2>/dev/null | grep -q "false"; then
    pass
else
    fail "org.gnome.shell disable-user-extensions is true"
fi

# 2. Extension installed?
step "extension installed"
if gnome-extensions show "$UUID" &>/dev/null; then
    pass
else
    fail "gnome-extensions show $UUID failed"
fi

# 3. Extension active?
step "extension active"
STATE=$(gnome-extensions show "$UUID" 2>/dev/null | grep -oP '状态:\s+\K\S+' || echo "UNKNOWN")
if [[ "$STATE" == "ACTIVE" ]]; then
    pass
else
    fail "state is $STATE (expected ACTIVE)"
fi

# 4. DBus name registered?
step "DBus name org.gnome.AIBridge"
if gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.NameHasOwner 'org.gnome.AIBridge' 2>/dev/null | grep -q "true"; then
    pass
else
    fail "name not owned"
fi

# 5. GetWindows returns JSON array?
step "GetWindows returns data"
WINDOWS=$(gdbus call --session --dest org.gnome.AIBridge --object-path /org/gnome/AIBridge --method org.gnome.AIBridge.GetWindows 2>/dev/null || echo "ERROR")
if echo "$WINDOWS" | grep -q '"id"'; then
    pass
else
    fail "no window data: $WINDOWS"
fi

# 6. GetWorkspaces returns JSON?
step "GetWorkspaces returns data"
WS=$(gdbus call --session --dest org.gnome.AIBridge --object-path /org/gnome/AIBridge --method org.gnome.AIBridge.GetWorkspaces 2>/dev/null || echo "ERROR")
if echo "$WS" | grep -q '"index"'; then
    pass
else
    fail "no workspace data: $WS"
fi

echo
echo "  Result: $OK passed, $FAIL failed"
exit $FAIL
