#!/usr/bin/env bash
# install.sh  –  Install the GNOME AI Bridge extension + daemon
# Run as the desktop user (not sudo for most steps).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EXT_UUID="gnome-ai-bridge@local"
EXT_SRC="$SCRIPT_DIR/gnome_extension"
EXT_DEST="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

echo "=== GNOME AI Daemon installer ==="
echo

# ── 0. system deps ──────────────────────────────────────────────────────────
echo "[0/5] Checking system dependencies"
MISSING=()
for cmd in xdotool gdbus python3 curl; do
    if ! command -v "$cmd" &>/dev/null; then
        MISSING+=("$cmd")
    fi
done
# python3-dbus and python3-gi are needed; check importability
if ! python3 -c "import dbus" &>/dev/null; then
    MISSING+=("python3-dbus")
fi
if ! python3 -c "from gi.repository import GLib" &>/dev/null; then
    MISSING+=("python3-gi")
fi

if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo "      Missing: ${MISSING[*]}"
    echo "      Installing via apt (needs sudo)…"
    # Map command names to package names
    PKGS=()
    for m in "${MISSING[@]}"; do
        case "$m" in
            xdotool)     PKGS+=("xdotool") ;;
            gdbus)       PKGS+=("libglib2.0-bin") ;;
            python3)     PKGS+=("python3") ;;
            curl)        PKGS+=("curl") ;;
            python3-dbus) PKGS+=("python3-dbus") ;;
            python3-gi)  PKGS+=("python3-gi" "gir1.2-glib-2.0") ;;
        esac
    done
    sudo apt-get update -qq
    sudo apt-get install -y -qq "${PKGS[@]}"
    echo "      System deps installed."
else
    echo "      All system deps present."
fi

# ── 1. copy extension ───────────────────────────────────────────────────────
echo
echo "[1/5] Installing GNOME extension to $EXT_DEST"
mkdir -p "$EXT_DEST"
cp -v "$EXT_SRC/metadata.json" "$EXT_DEST/"
cp -v "$EXT_SRC/extension.js"  "$EXT_DEST/"

# ── 2. enable extension ─────────────────────────────────────────────────────
echo
echo "[2/5] Enabling extension"

# Make sure user extensions are allowed globally
if gsettings get org.gnome.shell disable-user-extensions 2>/dev/null | grep -q "true"; then
    echo "      Enabling user extensions (was disabled globally)…"
    gsettings set org.gnome.shell disable-user-extensions false
fi

gnome-extensions enable "$EXT_UUID" 2>/dev/null || true

# On X11, restart the shell so the extension loads immediately.
# This is safe: SIGHUP triggers in-place re-exec, no logout needed.
if [[ "$XDG_SESSION_TYPE" == "x11" ]]; then
    echo "      Restarting GNOME Shell (X11)…"
    killall -HUP gnome-shell 2>/dev/null || true
    sleep 3
    echo "      Shell restarted."
else
    echo "      Wayland detected — log out and back in to activate."
fi

# ── 3. venv + Python deps ───────────────────────────────────────────────────
echo
echo "[3/5] Setting up Python venv"
if [[ ! -d "$SCRIPT_DIR/.venv" ]]; then
    # --system-site-packages lets the venv see python3-dbus / python3-gi
    python3 -m venv --system-site-packages "$SCRIPT_DIR/.venv"
fi
"$SCRIPT_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "      venv ready"

# Quick sanity import check
"$SCRIPT_DIR/.venv/bin/python" -c "
import dbus, fastapi, uvicorn, pydantic, requests, mss
from PIL import Image
from gi.repository import GLib
print('      All Python imports OK')
"

# ── 4. make helper scripts executable ────────────────────────────────────────
echo
echo "[4/5] Preparing helper scripts"
chmod +x "$SCRIPT_DIR"/scripts/*.sh 2>/dev/null || true
echo "      Scripts ready"

# ── 5. install systemd user service ─────────────────────────────────────────
echo
echo "[5/5] Installing systemd user service"
SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_DIR/gnome-ai-daemon.service" <<EOF
[Unit]
Description=GNOME AI Daemon (REST bridge for AI agents)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/run_daemon.py
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
EOF

systemctl --user daemon-reload
systemctl --user enable gnome-ai-daemon.service
echo "      Service installed."

echo
echo "=== Installation complete ==="
echo
echo "Next steps:"
echo "  1. Log out and back in (activates extension)"
echo "  2. Verify DBus bridge:  ./scripts/verify_dbus.sh"
echo "  3. Start daemon:        systemctl --user start gnome-ai-daemon"
echo "  4. Verify REST API:     ./scripts/verify_api.sh"
echo "  5. Interactive docs:    http://127.0.0.1:7070/docs"
