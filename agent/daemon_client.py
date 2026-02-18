from typing import Any, Dict, List
import requests


class DaemonClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def health(self) -> Dict[str, Any]:
        return self._get("/health")

    def get_state(self) -> Dict[str, Any]:
        return self._get("/state")

    def _get(self, path: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}{path}", timeout=8)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, json_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}{path}", json=json_data, timeout=8)
        r.raise_for_status()
        return r.json()

    def run_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "wait")

        if action_type == "wait":
            return {"success": True, "detail": "wait"}
        if action_type == "finish":
            return {"success": True, "detail": "finish"}
        if action_type == "launch":
            return self._post("/apps/launch", {"command": action["command"]})
        if action_type == "focus_window":
            return self._post(f"/windows/{int(action['window_id'])}/focus")
        if action_type == "close_window":
            return self._post(f"/windows/{int(action['window_id'])}/close")
        if action_type == "type_text":
            return self._post("/input/keyboard/type", {
                "text": action["text"],
                "delay_ms": int(action.get("delay_ms", 12)),
            })
        if action_type == "hotkey":
            keys = action.get("keys", [])
            if not isinstance(keys, list) or not keys:
                raise ValueError("hotkey requires non-empty keys list")
            return self._post("/input/keyboard/key", {"keys": keys})
        if action_type == "mouse_click":
            return self._post("/input/mouse/click", {
                "x": int(action["x"]),
                "y": int(action["y"]),
                "button": int(action.get("button", 1)),
            })
        if action_type == "mouse_double_click":
            return self._post("/input/mouse/double_click", {
                "x": int(action["x"]),
                "y": int(action["y"]),
                "button": int(action.get("button", 1)),
            })
        if action_type == "mouse_drag":
            return self._post("/input/mouse/drag", {
                "x1": int(action["x1"]),
                "y1": int(action["y1"]),
                "x2": int(action["x2"]),
                "y2": int(action["y2"]),
            })

        raise ValueError(f"Unsupported action type: {action_type}")
