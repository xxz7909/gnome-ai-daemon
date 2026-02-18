"""
daemon/models.py
Pydantic request/response models for the FastAPI layer.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ── window ────────────────────────────────────────────────────────────────────

class WindowInfo(BaseModel):
    id:        int
    xid:       Optional[int] = None
    title:     str
    wm_class:  str
    pid:       int
    focused:   bool
    minimized: bool
    maximized: bool
    workspace: int
    x:         int
    y:         int
    width:     int
    height:    int


class MoveResizeRequest(BaseModel):
    window_id: int
    x:         int
    y:         int
    width:     int  = Field(..., gt=0)
    height:    int  = Field(..., gt=0)


class MaximizeRequest(BaseModel):
    window_id: int
    maximize:  bool = True


# ── workspace ─────────────────────────────────────────────────────────────────

class WorkspaceInfo(BaseModel):
    index:  int
    active: bool


# ── input ─────────────────────────────────────────────────────────────────────

class MouseClickRequest(BaseModel):
    x:      int
    y:      int
    button: int  = Field(1, ge=1, le=3)

class MouseDragRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

class ScrollRequest(BaseModel):
    x:         int
    y:         int
    direction: str = Field("down", pattern=r"^(up|down|left|right)$")
    clicks:    int = Field(3, ge=1, le=20)

class KeyPressRequest(BaseModel):
    keys: List[str] = Field(..., min_length=1)
    """e.g. ["ctrl+c"] or ["Return"] or ["alt", "F4"]"""

class TypeTextRequest(BaseModel):
    text:     str
    delay_ms: int = Field(12, ge=0, le=500)

class FocusTypeRequest(BaseModel):
    xid:      int   # X11 window XID (from WindowInfo.id on X11)
    text:     str

class FocusKeyRequest(BaseModel):
    xid:  int
    keys: List[str]


# ── app launch ────────────────────────────────────────────────────────────────

class LaunchAppRequest(BaseModel):
    command: str


# ── generic response ──────────────────────────────────────────────────────────

class SuccessResponse(BaseModel):
    success: bool
    detail:  Optional[str] = None

class ScreenState(BaseModel):
    windows:          List[WindowInfo]
    focused_window_id: int
    workspaces:       List[WorkspaceInfo]
    screen_width:     int
    screen_height:    int
