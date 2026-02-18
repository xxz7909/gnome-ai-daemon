from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

from agent.config import AgentConfig
from agent.daemon_client import DaemonClient
from agent.model_client import ModelClient
from agent.screen_capture import capture_jpeg_bytes, frame_diff_ratio


class DesktopAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.daemon = DaemonClient(config.daemon_base_url)
        self.model = ModelClient(
            api_base=config.model_api_base,
            model_name=config.model_name,
            api_key=config.model_api_key,
        )

    # ── normal one-shot mode ────────────────────────────────────────────────

    def run(self, goal: str) -> None:
        self._preflight()
        print(f"[agent] goal: {goal}")
        print(f"[agent] model: {self.config.model_name}")

        if self.config.realtime:
            self._run_realtime(goal)
        else:
            self._run_stepwise(goal)

    def _preflight(self) -> None:
        health = self.daemon.health()
        if health.get("status") != "ok":
            raise RuntimeError(f"daemon health check failed: {health}")

    # ── stepwise (original) ─────────────────────────────────────────────────

    def _run_stepwise(self, goal: str) -> None:
        for step in range(1, self.config.max_steps + 1):
            action = self._think_and_act(step, goal)
            if action.get("type") == "finish":
                print("[agent] task finished")
                return
            time.sleep(self.config.capture_interval_sec)
        print("[agent] max steps reached")

    # ── realtime low-latency mode ───────────────────────────────────────────

    def _run_realtime(self, goal: str) -> None:
        """0.5s 帧间隔 + 动作冷却 + 帧差跳过推理"""
        print(f"[agent] realtime mode ON  "
              f"(frame_interval={self.config.realtime_fps_interval}s, "
              f"action_cooldown={self.config.action_cooldown_sec}s, "
              f"idle_skip={self.config.idle_skip_threshold})")

        step = 0
        prev_frame: Optional[bytes] = None
        last_action_time: float = 0.0

        while step < self.config.max_steps:
            t0 = time.monotonic()

            # 1) capture
            screenshot = capture_jpeg_bytes(
                max_width=self.config.screenshot_max_width,
                quality=self.config.screenshot_quality,
            )

            # 2) frame diff — skip inference if screen barely changed
            diff = frame_diff_ratio(prev_frame, screenshot)
            prev_frame = screenshot

            if diff < self.config.idle_skip_threshold:
                self._sleep_until(t0, self.config.realtime_fps_interval)
                continue

            # 3) action cooldown — wait if last action was too recent
            since_last = time.monotonic() - last_action_time
            if since_last < self.config.action_cooldown_sec and last_action_time > 0:
                self._sleep_until(t0, self.config.realtime_fps_interval)
                continue

            # 4) think + act
            step += 1
            action = self._think_and_act(step, goal, screenshot_override=screenshot)
            if action.get("type") == "finish":
                print("[agent] task finished")
                return
            if action.get("type") != "wait":
                last_action_time = time.monotonic()

            # 5) keep fixed interval
            self._sleep_until(t0, self.config.realtime_fps_interval)

        print("[agent] max steps reached")

    # ── shared helpers ──────────────────────────────────────────────────────

    def _think_and_act(
        self,
        step: int,
        goal: str,
        screenshot_override: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        state = self.daemon.get_state()
        screenshot = screenshot_override or capture_jpeg_bytes(
            max_width=self.config.screenshot_max_width,
            quality=self.config.screenshot_quality,
        )

        t_infer = time.monotonic()
        decision = self.model.next_action(goal=goal, state=state, screenshot_jpeg=screenshot)
        latency_ms = (time.monotonic() - t_infer) * 1000

        action = decision.get("action", {"type": "wait"})
        reason = decision.get("reason", "")

        print(f"\n[step {step}] reason: {reason}")
        print(f"[step {step}] action: {json.dumps(action, ensure_ascii=False)}  ({latency_ms:.0f}ms)")

        if action.get("type") == "finish":
            return action

        try:
            result = self.daemon.run_action(action)
        except Exception as e:
            result = {"success": False, "detail": str(e)}

        print(f"[step {step}] result: {json.dumps(result, ensure_ascii=False)}")
        return action

    @staticmethod
    def _sleep_until(t0: float, interval: float) -> None:
        elapsed = time.monotonic() - t0
        remaining = interval - elapsed
        if remaining > 0:
            time.sleep(remaining)
