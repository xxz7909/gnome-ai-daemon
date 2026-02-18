from __future__ import annotations

import base64
import json
from typing import Any, Dict

import requests


SYSTEM_PROMPT = """你是一个桌面自动化代理。你会看到：
1) 当前屏幕截图（image）
2) 当前系统状态JSON（windows/workspaces/focus）
3) 用户目标

你必须只输出严格JSON，不要输出其他内容，格式如下：
{
  "reason": "一句简短中文解释",
  "action": {
    "type": "wait|finish|launch|focus_window|close_window|type_text|hotkey|mouse_click|mouse_double_click|mouse_drag",
    "...": "根据动作类型填写参数"
  }
}

要求：
- 每次只执行一个最小动作。
- 不确定时返回 wait。
- 当目标完成时返回 finish。
- 不要虚构窗口ID，必须使用 state.windows 里的 id。
"""


class ModelClient:
    def __init__(self, api_base: str, model_name: str, api_key: str = "EMPTY"):
        self.api_base = api_base.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key

    def next_action(self, goal: str, state: Dict[str, Any], screenshot_jpeg: bytes) -> Dict[str, Any]:
        image_b64 = base64.b64encode(screenshot_jpeg).decode("utf-8")
        payload = {
            "model": self.model_name,
            "temperature": 0.1,
            "max_tokens": 300,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"用户目标: {goal}"},
                        {"type": "text", "text": f"当前状态JSON: {json.dumps(state, ensure_ascii=False)}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        }

        r = requests.post(
            f"{self.api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]

        parsed = _safe_json_parse(content)
        if not isinstance(parsed, dict) or "action" not in parsed:
            return {"reason": "模型输出不可解析，降级wait", "action": {"type": "wait"}}
        return parsed


def _safe_json_parse(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)
