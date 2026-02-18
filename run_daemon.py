#!/usr/bin/env python3
"""
gnome-ai-daemon  ·  main entry point
Starts the FastAPI server together with the DBus event listener.
"""

import asyncio
import threading
import uvicorn
from daemon.api import app          # FastAPI application
from daemon.dbus_client import AIBridgeClient


def _run_dbus_mainloop():
    """Run the GLib main loop in a background thread (for DBus signals)."""
    from gi.repository import GLib
    loop = GLib.MainLoop()
    loop.run()


def main():
    # Start GLib loop for DBus signal delivery
    t = threading.Thread(target=_run_dbus_mainloop, daemon=True)
    t.start()

    # Pre-connect to the GNOME extension (non-fatal if extension not installed)
    client = AIBridgeClient.instance()
    try:
        client.connect()
        print("[daemon] Connected to org.gnome.AIBridge")
    except Exception as e:
        print(f"[daemon] WARNING: Could not connect to org.gnome.AIBridge: {e}")
        print("[daemon] Install the GNOME extension first (run install.sh)")

    uvicorn.run(
        "daemon.api:app",
        host="127.0.0.1",
        port=7070,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
