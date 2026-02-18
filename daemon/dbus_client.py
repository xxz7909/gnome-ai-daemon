"""
daemon/dbus_client.py
Singleton wrapper around the org.gnome.AIBridge DBus service
exposed by the GNOME Shell extension.

Falls back gracefully when the extension is not loaded.
"""

import json
import threading
from typing import Any, Callable, Dict, List, Optional

import dbus
import dbus.mainloop.glib

# One-time GLib main loop integration for dbus-python
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

DBUS_NAME   = "org.gnome.AIBridge"
DBUS_PATH   = "/org/gnome/AIBridge"
DBUS_IFACE  = "org.gnome.AIBridge"


class AIBridgeClient:
    """Thread-safe singleton DBus client for the GNOME AI Bridge extension."""

    _instance: Optional["AIBridgeClient"] = None
    _lock = threading.Lock()

    @classmethod
    def instance(cls) -> "AIBridgeClient":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._proxy: Optional[dbus.Interface] = None
        self._bus:   Optional[dbus.SessionBus] = None
        self._window_change_callbacks: List[Callable] = []

    # ── connection ──────────────────────────────────────────────────────────

    def connect(self) -> None:
        self._bus   = dbus.SessionBus()
        obj         = self._bus.get_object(DBUS_NAME, DBUS_PATH)
        self._proxy = dbus.Interface(obj, dbus_interface=DBUS_IFACE)

        # Subscribe to WindowsChanged signal
        self._bus.add_signal_receiver(
            self._on_windows_changed,
            signal_name="WindowsChanged",
            dbus_interface=DBUS_IFACE,
            bus_name=DBUS_NAME,
            path=DBUS_PATH,
        )

    @property
    def connected(self) -> bool:
        return self._proxy is not None

    def _require(self) -> dbus.Interface:
        if self._proxy is None:
            # Try lazy connect
            self.connect()
        return self._proxy  # type: ignore

    # ── window queries ──────────────────────────────────────────────────────

    def get_windows(self) -> List[Dict[str, Any]]:
        raw = str(self._require().GetWindows())
        return json.loads(raw)

    def get_focused_window(self) -> int:
        return int(self._require().GetFocusedWindow())

    # ── window actions ──────────────────────────────────────────────────────

    def focus_window(self, window_id: int) -> bool:
        return bool(self._require().FocusWindow(dbus.UInt32(window_id)))

    def close_window(self, window_id: int) -> bool:
        return bool(self._require().CloseWindow(dbus.UInt32(window_id)))

    def move_resize_window(
        self, window_id: int, x: int, y: int, width: int, height: int
    ) -> bool:
        return bool(self._require().MoveResizeWindow(
            dbus.UInt32(window_id),
            dbus.Int32(x), dbus.Int32(y),
            dbus.Int32(width), dbus.Int32(height),
        ))

    def minimize_window(self, window_id: int) -> bool:
        return bool(self._require().MinimizeWindow(dbus.UInt32(window_id)))

    def maximize_window(self, window_id: int, maximize: bool = True) -> bool:
        return bool(self._require().MaximizeWindow(
            dbus.UInt32(window_id), dbus.Boolean(maximize)))

    # ── workspace ───────────────────────────────────────────────────────────

    def get_workspaces(self) -> List[Dict[str, Any]]:
        raw = str(self._require().GetWorkspaces())
        return json.loads(raw)

    def switch_workspace(self, index: int) -> bool:
        return bool(self._require().SwitchWorkspace(dbus.Int32(index)))

    # ── app launch ──────────────────────────────────────────────────────────

    def launch_app(self, command: str) -> bool:
        return bool(self._require().LaunchApp(command))

    # ── signals ─────────────────────────────────────────────────────────────

    def on_windows_changed(self, cb: Callable[[List[Dict]], None]) -> None:
        self._window_change_callbacks.append(cb)

    def _on_windows_changed(self, windows_json: str) -> None:
        data = json.loads(str(windows_json))
        for cb in self._window_change_callbacks:
            try:
                cb(data)
            except Exception as e:
                print(f"[dbus_client] signal callback error: {e}")
