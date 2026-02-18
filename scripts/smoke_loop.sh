#!/usr/bin/env bash
# smoke_loop.sh — continuous smoke test (Ctrl-C to stop)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL="${INTERVAL_SEC:-5}"

echo "Smoke loop — Ctrl-C to stop (interval: ${INTERVAL}s)"
echo

while true; do
    echo "── $(date -Iseconds) ──"
    bash "$SCRIPT_DIR/verify_dbus.sh" || true
    bash "$SCRIPT_DIR/verify_api.sh"  || true
    echo
    sleep "$INTERVAL"
done
