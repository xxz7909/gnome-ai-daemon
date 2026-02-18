#!/usr/bin/env python3
"""Run multimodal desktop agent loop.

Normal mode:
  .venv/bin/python run_agent.py "打开终端并输入 hello"

Realtime mode (0.5s frame, action cooldown):
  .venv/bin/python run_agent.py --realtime "打开终端并输入 hello"

Remote model server:
  MODEL_API_BASE=http://<gpu-server>:8000/v1 \
  .venv/bin/python run_agent.py --realtime "打开浏览器"
"""

import argparse

from agent.config import AgentConfig
from agent.loop import DesktopAgent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run multimodal GNOME desktop agent")
    parser.add_argument("goal", type=str, help="high-level task goal in Chinese or English")
    parser.add_argument("--realtime", action="store_true",
                        help="enable low-latency realtime mode (0.5s frame + action cooldown)")
    parser.add_argument("--fps-interval", type=float, default=None,
                        help="override realtime frame interval in seconds (default: 0.5)")
    parser.add_argument("--cooldown", type=float, default=None,
                        help="override action cooldown in seconds (default: 1.0)")
    args = parser.parse_args()

    cfg = AgentConfig()
    cfg.realtime = args.realtime
    if args.fps_interval is not None:
        cfg.realtime_fps_interval = args.fps_interval
    if args.cooldown is not None:
        cfg.action_cooldown_sec = args.cooldown

    DesktopAgent(cfg).run(args.goal)


if __name__ == "__main__":
    main()
