"""
daemon/api.py
FastAPI application – REST interface for AI agents.

All endpoints return structured JSON.  The daemon wraps two sources:
  1. org.gnome.AIBridge DBus (window list, workspace, app launch)
  2. xdotool           (mouse, keyboard, window geometry)

Base URL: http://127.0.0.1:7070
"""

from typing import List

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from daemon.dbus_client import AIBridgeClient
from daemon import input_controller as ic
from daemon.models import (
    FocusKeyRequest, FocusTypeRequest, KeyPressRequest,
    LaunchAppRequest, MaximizeRequest, MouseClickRequest,
    MouseDragRequest, MoveResizeRequest, ScreenState,
    ScrollRequest, SuccessResponse, TypeTextRequest,
    WindowInfo, WorkspaceInfo,
)

app = FastAPI(
    title="GNOME AI Daemon",
    version="1.0.0",
    description=(
        "REST API that lets AI agents read screen state and control "
        "the GNOME desktop (windows, workspaces, keyboard, mouse)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _client() -> AIBridgeClient:
    c = AIBridgeClient.instance()
    if not c.connected:
        try:
            c.connect()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"GNOME AI Bridge extension not reachable: {e}",
            )
    return c


# ── state ─────────────────────────────────────────────────────────────────────

@app.get(
    "/state",
    response_model=ScreenState,
    summary="Full desktop state snapshot",
    description=(
        "Returns all open windows, the focused window id, workspace list, "
        "and screen resolution in a single call.  Ideal as context for an LLM."
    ),
)
def get_state() -> ScreenState:
    c = _client()
    w, h = ic.get_screen_size()
    return ScreenState(
        windows=[WindowInfo(**win) for win in c.get_windows()],
        focused_window_id=c.get_focused_window(),
        workspaces=[WorkspaceInfo(**ws) for ws in c.get_workspaces()],
        screen_width=w,
        screen_height=h,
    )


# ── windows ───────────────────────────────────────────────────────────────────

@app.get("/windows", response_model=List[WindowInfo], summary="List open windows")
def list_windows() -> List[WindowInfo]:
    return [WindowInfo(**w) for w in _client().get_windows()]


@app.post("/windows/{window_id}/focus", response_model=SuccessResponse)
def focus_window(window_id: int) -> SuccessResponse:
    ok = _client().focus_window(window_id)
    return SuccessResponse(success=ok)


@app.post("/windows/{window_id}/close", response_model=SuccessResponse)
def close_window(window_id: int) -> SuccessResponse:
    ok = _client().close_window(window_id)
    return SuccessResponse(success=ok)


@app.post("/windows/{window_id}/minimize", response_model=SuccessResponse)
def minimize_window(window_id: int) -> SuccessResponse:
    ok = _client().minimize_window(window_id)
    return SuccessResponse(success=ok)


@app.post("/windows/maximize", response_model=SuccessResponse)
def maximize_window(req: MaximizeRequest) -> SuccessResponse:
    ok = _client().maximize_window(req.window_id, req.maximize)
    return SuccessResponse(success=ok)


@app.post("/windows/move_resize", response_model=SuccessResponse)
def move_resize_window(req: MoveResizeRequest) -> SuccessResponse:
    ok = _client().move_resize_window(
        req.window_id, req.x, req.y, req.width, req.height)
    return SuccessResponse(success=ok)


# ── workspaces ────────────────────────────────────────────────────────────────

@app.get("/workspaces", response_model=List[WorkspaceInfo])
def list_workspaces() -> List[WorkspaceInfo]:
    return [WorkspaceInfo(**ws) for ws in _client().get_workspaces()]


@app.post("/workspaces/{index}/switch", response_model=SuccessResponse)
def switch_workspace(index: int) -> SuccessResponse:
    ok = _client().switch_workspace(index)
    return SuccessResponse(success=ok)


# ── app launch ────────────────────────────────────────────────────────────────

@app.post("/apps/launch", response_model=SuccessResponse)
def launch_app(req: LaunchAppRequest) -> SuccessResponse:
    ok = _client().launch_app(req.command)
    return SuccessResponse(success=ok)


# ── mouse ─────────────────────────────────────────────────────────────────────

@app.post("/input/mouse/move", response_model=SuccessResponse)
def mouse_move(x: int, y: int) -> SuccessResponse:
    return SuccessResponse(success=ic.mouse_move(x, y))


@app.post("/input/mouse/click", response_model=SuccessResponse)
def mouse_click(req: MouseClickRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.mouse_click(req.x, req.y, req.button))


@app.post("/input/mouse/double_click", response_model=SuccessResponse)
def mouse_double_click(req: MouseClickRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.mouse_double_click(req.x, req.y))


@app.post("/input/mouse/drag", response_model=SuccessResponse)
def mouse_drag(req: MouseDragRequest) -> SuccessResponse:
    return SuccessResponse(
        success=ic.mouse_drag(req.x1, req.y1, req.x2, req.y2))


@app.post("/input/mouse/scroll", response_model=SuccessResponse)
def scroll(req: ScrollRequest) -> SuccessResponse:
    return SuccessResponse(
        success=ic.scroll(req.x, req.y, req.direction, req.clicks))


# ── keyboard ──────────────────────────────────────────────────────────────────

@app.post("/input/keyboard/key", response_model=SuccessResponse)
def key_press(req: KeyPressRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.key_press(*req.keys))


@app.post("/input/keyboard/type", response_model=SuccessResponse)
def type_text(req: TypeTextRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.type_text(req.text, req.delay_ms))


@app.post("/input/keyboard/focus_type", response_model=SuccessResponse)
def focus_and_type(req: FocusTypeRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.focus_and_type(req.xid, req.text))


@app.post("/input/keyboard/focus_key", response_model=SuccessResponse)
def focus_and_key(req: FocusKeyRequest) -> SuccessResponse:
    return SuccessResponse(success=ic.focus_and_key(req.xid, *req.keys))


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    c = AIBridgeClient.instance()
    return {"status": "ok", "dbus_connected": c.connected}
