"""
daemon/input_controller.py
Virtual keyboard + mouse input via xdotool (X11).

xdotool is a well-maintained CLI tool – using subprocess here is the
idiomatic way to drive it from Python without a C binding.
"""

import subprocess
import shlex
from typing import Tuple


def _xdo(*args: str) -> bool:
    """Run an xdotool command. Returns True on success."""
    try:
        subprocess.run(["xdotool", *args], check=True,
                       capture_output=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[input] xdotool error: {e}")
        return False


# ── mouse ────────────────────────────────────────────────────────────────────

def mouse_move(x: int, y: int) -> bool:
    """Move mouse to absolute screen coordinates."""
    return _xdo("mousemove", "--sync", str(x), str(y))

def mouse_click(x: int, y: int, button: int = 1) -> bool:
    """Click at absolute screen coordinates. button: 1=left, 2=middle, 3=right."""
    return (mouse_move(x, y) and
            _xdo("click", str(button)))

def mouse_double_click(x: int, y: int) -> bool:
    return (mouse_move(x, y) and
            _xdo("click", "--repeat", "2", "1"))

def mouse_down(button: int = 1) -> bool:
    return _xdo("mousedown", str(button))

def mouse_up(button: int = 1) -> bool:
    return _xdo("mouseup", str(button))

def mouse_drag(x1: int, y1: int, x2: int, y2: int) -> bool:
    """Click and drag from (x1,y1) to (x2,y2)."""
    return (mouse_move(x1, y1) and
            mouse_down(1) and
            mouse_move(x2, y2) and
            mouse_up(1))

def scroll(x: int, y: int, direction: str = "up", clicks: int = 3) -> bool:
    """Scroll at position. direction: 'up'|'down'|'left'|'right'."""
    btn = {"up": 4, "down": 5, "left": 6, "right": 7}.get(direction, 4)
    return (mouse_move(x, y) and
            _xdo("click", "--repeat", str(clicks), str(btn)))


# ── keyboard ─────────────────────────────────────────────────────────────────

def key_press(*keys: str) -> bool:
    """
    Simulate pressing a key or key combo.
    keys examples: "Return", "ctrl+c", "alt+F4", "super"
    """
    return _xdo("key", "--clearmodifiers", *keys)

def type_text(text: str, delay_ms: int = 12) -> bool:
    """
    Type a string of text.
    delay_ms controls inter-keystroke delay (avoids missed keys under load).
    """
    return _xdo("type", "--clearmodifiers",
                "--delay", str(delay_ms), "--", text)


# ── window focus + input ─────────────────────────────────────────────────────

def focus_and_type(xid: int, text: str) -> bool:
    """Focus window by X11 XID, then type text into it."""
    return (_xdo("windowfocus", "--sync", str(xid)) and
            type_text(text))

def focus_and_key(xid: int, *keys: str) -> bool:
    return (_xdo("windowfocus", "--sync", str(xid)) and
            key_press(*keys))


# ── screen geometry helpers ──────────────────────────────────────────────────

def get_screen_size() -> Tuple[int, int]:
    """Return (width, height) of the primary display."""
    try:
        out = subprocess.check_output(
            ["xdotool", "getdisplaygeometry"], text=True, timeout=3)
        w, h = out.strip().split()
        return int(w), int(h)
    except Exception:
        return (1920, 1080)
