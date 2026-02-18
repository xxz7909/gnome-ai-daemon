from dataclasses import dataclass, field
import os


@dataclass
class AgentConfig:
    daemon_base_url: str = os.getenv("GNOME_DAEMON_BASE_URL", "http://127.0.0.1:7070")
    model_api_base: str = os.getenv("MODEL_API_BASE", "http://127.0.0.1:8000/v1")
    model_name: str = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-VL-7B-Instruct")
    model_api_key: str = os.getenv("MODEL_API_KEY", "EMPTY")
    capture_interval_sec: float = float(os.getenv("CAPTURE_INTERVAL_SEC", "1.0"))
    max_steps: int = int(os.getenv("AGENT_MAX_STEPS", "40"))
    screenshot_max_width: int = int(os.getenv("SCREENSHOT_MAX_WIDTH", "1280"))
    screenshot_quality: int = int(os.getenv("SCREENSHOT_QUALITY", "80"))

    # ── realtime mode ────────────────────────────────────────────────────
    realtime: bool = False
    realtime_fps_interval: float = float(os.getenv("REALTIME_FPS_INTERVAL", "0.5"))
    action_cooldown_sec: float = float(os.getenv("ACTION_COOLDOWN_SEC", "1.0"))
    idle_skip_threshold: float = float(os.getenv("IDLE_SKIP_THRESHOLD", "0.02"))
    # idle_skip_threshold: 如果两帧之间像素差异比例低于此值，跳过推理
