# GNOME AI Daemon

让 AI Agent 通过 REST API 读取桌面状态并控制 GNOME 桌面（窗口、工作区、键盘、鼠标）。

## 架构

```
AI Agent  →  REST API (:7070)  →  Python Daemon  →  DBus  →  GNOME 扩展  →  Shell
                                                     ↓
                                               xdotool (输入注入)
```

## 环境要求

- Ubuntu 24.04 / GNOME Shell 46+ / X11
- `xdotool`、`python3`、`python3-dbus`、`python3-gi`

## 多模态模型选型（推荐）

针对“实时监测屏幕 + 桌面动作决策”，当前默认推荐：

- 模型：`Qwen/Qwen2.5-VL-7B-Instruct`
- 原因：开源可本地部署、视觉理解稳定、对 GUI 元素识别能力较均衡
- 部署方式：vLLM 提供 OpenAI 兼容接口（`/v1/chat/completions`）

| 模型 | 显存需求（BF16） | 显存需求（AWQ 4-bit） | 适用场景 |
|------|-----------------|---------------------|---------|
| Qwen2.5-VL-7B-Instruct | ~16 GB | ~8 GB | 推荐；复杂 GUI 操作 |
| Qwen2.5-VL-3B-Instruct | ~8 GB | ~4 GB | 低显存 / 更低延迟 |

> **注意**：本机 MX450 仅 2GB 显存，无法本地推理。请在远端 GPU 服务器运行 vLLM，
> 本机 Agent 通过 `MODEL_API_BASE=http://<server>:8000/v1` 指向远端。

### 启动 vLLM 模型服务

```bash
# 默认 7B（需 ≥16GB 显存）
bash scripts/start_vllm.sh

# 3B 版本（需 ≥8GB 显存）
MODEL=Qwen/Qwen2.5-VL-3B-Instruct bash scripts/start_vllm.sh

# 4-bit 量化（AWQ，减半显存）
QUANTIZATION=awq bash scripts/start_vllm.sh
```

## 安装

```bash
chmod +x install.sh && ./install.sh
```

安装脚本会自动完成：
1. 检查并安装系统依赖（`xdotool`、`python3-dbus` 等）
2. 复制 GNOME 扩展并启用
3. X11 下自动重启 GNOME Shell（安全的 SIGHUP 重启，不会注销）
4. 创建 Python 虚拟环境，安装 FastAPI / uvicorn
5. 安装 systemd 用户服务（开机自启）

## 启动

```bash
systemctl --user start gnome-ai-daemon
```

## 验证

```bash
./scripts/verify_dbus.sh   # 6 项检查：扩展 + DBus 服务
./scripts/verify_api.sh    # 6 项检查：REST API 端点
./scripts/smoke_loop.sh    # 持续冒烟测试（Ctrl-C 停止）
```

## 接入多模态 Agent

仓库已包含闭环 Agent（截图 → VLM 推理 → 调用 GNOME API 执行动作）：

- 入口：`run_agent.py`
- 模块：`agent/`

先保证 daemon 已启动：

```bash
systemctl --user start gnome-ai-daemon
```

示例（本地模型服务运行在 `127.0.0.1:8000`）：

```bash
MODEL_API_BASE=http://127.0.0.1:8000/v1 \
MODEL_NAME=Qwen/Qwen2.5-VL-7B-Instruct \
.venv/bin/python run_agent.py "打开终端并输入 hello world"
```

可调环境变量：

- `CAPTURE_INTERVAL_SEC`：截图与决策间隔（默认 `1.0` 秒）
- `AGENT_MAX_STEPS`：最大动作步数（默认 `40`）
- `SCREENSHOT_MAX_WIDTH`：截图缩放宽度（默认 `1280`）
- `SCREENSHOT_QUALITY`：JPEG 质量（默认 `80`）

### 实时模式（低延迟）

加 `--realtime` 启用，自动启用：

- **0.5s 帧间隔**：每 500ms 截一次屏
- **帧差跳过**：屏幕无变化时跳过推理（节省 GPU）
- **动作冷却**：执行动作后等待 1s 再执行下一个（防止连点）

```bash
# 实时模式
.venv/bin/python run_agent.py --realtime "打开浏览器搜索天气"

# 自定义帧间隔和冷却
.venv/bin/python run_agent.py --realtime --fps-interval 0.3 --cooldown 0.8 "..."
```

实时模式相关环境变量：

- `REALTIME_FPS_INTERVAL`：帧间隔秒数（默认 `0.5`）
- `ACTION_COOLDOWN_SEC`：动作冷却秒数（默认 `1.0`）
- `IDLE_SKIP_THRESHOLD`：帧差低于此比例时跳过推理（默认 `0.02`）

## 本地执行 + 远端 vLLM 调试手册（推荐）

你的目标是：**在本地桌面执行 Agent，并把模型推理放到远端 GPU 服务器**。

### 0）先确认本地桌面控制层正常

```bash
systemctl --user start gnome-ai-daemon
./scripts/verify_dbus.sh
./scripts/verify_api.sh
```

这三步必须全部通过，否则先不要接模型。

### 1）在远端 GPU 服务器启动 vLLM

在远端机器（不是本机 MX450）运行：

```bash
bash scripts/start_vllm.sh
```

显存不足时建议：

```bash
MODEL=Qwen/Qwen2.5-VL-3B-Instruct QUANTIZATION=awq bash scripts/start_vllm.sh
```

### 2）本地连通性检查（非常重要）

先替换 `<远端IP>` 为真实 IP（例如 `192.168.1.50`），然后执行：

```bash
curl http://<远端IP>:8000/v1/models
```

如果这条不通，Agent 一定跑不起来。请先排查防火墙 / 端口映射 / 监听地址。

### 3）本地运行 Agent（你这条命令的正确写法）

你给的命令里出现了 Markdown 链接形式 `[run_agent.py](...)`，这是文档格式，不是终端命令。

请在终端直接运行：

```bash
MODEL_API_BASE=http://<远端IP>:8000/v1 \
MODEL_NAME=Qwen/Qwen2.5-VL-7B-Instruct \
.venv/bin/python run_agent.py "打开终端并输入 hello world"
```

实时低延迟模式：

```bash
MODEL_API_BASE=http://<远端IP>:8000/v1 \
MODEL_NAME=Qwen/Qwen2.5-VL-7B-Instruct \
.venv/bin/python run_agent.py --realtime --fps-interval 0.5 --cooldown 1.0 "打开终端并输入 hello world"
```

### 4）建议的最小调试任务

先从这类稳定任务开始：

- `打开终端并输入 hello world`
- `打开设置并返回桌面`
- `切换到 VS Code 窗口`

不要一开始就给复杂多步骤任务（比如“打开浏览器登录某网站并下载文件”）。

### 5）如何判断“正在正常工作”

运行后你会看到每一步日志：

- `[step N] reason: ...`
- `[step N] action: ... (xxxms)`
- `[step N] result: {"success": true ...}`

这表示：截图成功、模型返回成功、动作调用 daemon 成功。

### 6）常见报错与处理

1. **连接模型失败 / 超时**
      - 检查 `MODEL_API_BASE` 是否可达：`curl http://<远端IP>:8000/v1/models`
      - 检查远端 vLLM 是否仍在运行。

1. **vLLM 启动时报 CUDA OOM（你当前遇到的错误）**
                  - 现象：日志包含 `Failed to load model - not enough GPU memory` / `torch.OutOfMemoryError`。
                  - 原因：本机 MX450 只有约 2GB 显存，无法承载 Qwen2.5-VL-3B/7B。
                  - 处理：
                        - 不要在本机起 VL 模型；改为远端 GPU（推荐 >=8GB）运行 `scripts/start_vllm.sh`。
                        - 本机只跑 Agent：
                              `MODEL_API_BASE=http://<远端IP>:8000/v1 .venv/bin/python run_agent.py --realtime "打开终端并输入 hello world"`
                  - 快速确认：
                        `curl http://<远端IP>:8000/v1/models`

2. **daemon 不可用**
      - 执行：`systemctl --user status gnome-ai-daemon`
      - 执行：`./scripts/verify_api.sh`

3. **扩展已安装但动作无响应**
      - 执行：`./scripts/verify_dbus.sh`
      - 执行：`gnome-extensions show gnome-ai-bridge@local`（应为 ACTIVE）

4. **动作太频繁或抖动**
      - 增大冷却：`--cooldown 1.2`
      - 增大帧间隔：`--fps-interval 0.7`
      - 提高跳过阈值：`IDLE_SKIP_THRESHOLD=0.03`

5. **中文任务效果不稳定**
      - 改成更短、更明确的指令（一次只做一件事）。
      - 例如把“打开终端并输入 hello world 后截图保存”拆成两次执行。

### 7）推荐调试顺序（一次成功率最高）

```bash
# 1) 本地控制层
systemctl --user start gnome-ai-daemon && ./scripts/verify_dbus.sh && ./scripts/verify_api.sh

# 2) 远端模型连通
curl http://<远端IP>:8000/v1/models

# 3) 先普通模式，再实时模式
MODEL_API_BASE=http://<远端IP>:8000/v1 .venv/bin/python run_agent.py "打开终端并输入 hello world"
MODEL_API_BASE=http://<远端IP>:8000/v1 .venv/bin/python run_agent.py --realtime "打开终端并输入 hello world"
```

## 云端模型服务商 API Key 调试手册（无本地 GPU 推荐）

适用场景：你只有轻薄本 / 老笔记本（例如 2GB 显存），无法本地运行多模态模型。

核心思路：

- 本地只运行：GNOME 扩展 + daemon + agent（截图和动作执行）
- 模型推理走：云端服务商的多模态 API（通过 `API Key`）

### 1）前置条件

先确认本地控制层没问题：

```bash
systemctl --user start gnome-ai-daemon
./scripts/verify_dbus.sh
./scripts/verify_api.sh
```

### 2）配置云端 API Key

把下面占位符替换成真实值：

```bash
export MODEL_API_BASE="https://<服务商OpenAI兼容地址>/v1"
export MODEL_API_KEY="<你的API_KEY>"
export MODEL_NAME="<服务商支持的多模态模型名>"
```

说明：

- 你的 Agent 走 OpenAI 兼容接口（`/v1/chat/completions`）
- `MODEL_NAME` 必须是支持图像输入的模型

### 3）连通性测试（建议先做）

```bash
curl -s -H "Authorization: Bearer $MODEL_API_KEY" "$MODEL_API_BASE/models" | head
```

如果服务商不开放 `/models`，可直接进行第 4 步实测。

### 4）运行简单任务（普通模式）

```bash
.venv/bin/python run_agent.py "打开终端并输入 hello world"
```

### 5）运行低延迟实时模式（推荐）

```bash
.venv/bin/python run_agent.py --realtime --fps-interval 0.5 --cooldown 1.0 "打开终端并输入 hello world"
```

### 6）省钱和稳定性参数（建议）

```bash
export SCREENSHOT_MAX_WIDTH=960
export SCREENSHOT_QUALITY=65
export IDLE_SKIP_THRESHOLD=0.03
```

说明：

- 降低截图分辨率和质量可显著减少上传带宽与 API 成本
- `IDLE_SKIP_THRESHOLD` 变大后，屏幕变化小就不发请求，更省钱

### 7）常见错误与处理

1. **401 Unauthorized**
      - API Key 错误、过期或无该模型权限

2. **404 Not Found**
      - `MODEL_API_BASE` 写错（通常需要以 `/v1` 结尾）

3. **429 Too Many Requests**
      - 触发服务商限流；增大 `--fps-interval` 或降低并发频率

4. **连接超时 / 网络不稳定**
      - 优先测试：`curl https://<服务商域名>`
      - 网络差时建议普通模式先跑通，再开实时模式

5. **任务执行抖动 / 连点**
      - 提高冷却：`--cooldown 1.2`
      - 提高帧间隔：`--fps-interval 0.7`

### 8）一条命令快速开始（示例模板）

```bash
MODEL_API_BASE="https://<服务商OpenAI兼容地址>/v1" \
MODEL_API_KEY="<你的API_KEY>" \
MODEL_NAME="<多模态模型名>" \
.venv/bin/python run_agent.py --realtime --fps-interval 0.5 --cooldown 1.0 "打开终端并输入 hello world"
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/state` | 完整桌面快照（窗口 + 工作区 + 屏幕分辨率） |
| GET | `/windows` | 列出所有窗口 |
| POST | `/windows/{id}/focus` | 聚焦窗口 |
| POST | `/windows/{id}/close` | 关闭窗口 |
| POST | `/windows/{id}/minimize` | 最小化窗口 |
| POST | `/windows/maximize` | 最大化 / 取消最大化 |
| POST | `/windows/move_resize` | 移动和调整窗口大小 |
| GET | `/workspaces` | 列出工作区 |
| POST | `/workspaces/{index}/switch` | 切换工作区 |
| POST | `/apps/launch` | 启动应用程序 |
| POST | `/input/mouse/move` | 移动鼠标 |
| POST | `/input/mouse/click` | 鼠标点击 |
| POST | `/input/mouse/double_click` | 鼠标双击 |
| POST | `/input/mouse/drag` | 鼠标拖拽 |
| POST | `/input/mouse/scroll` | 滚轮滚动 |
| POST | `/input/keyboard/key` | 按键 / 组合键 |
| POST | `/input/keyboard/type` | 输入文本 |
| POST | `/input/keyboard/focus_type` | 聚焦窗口并输入文本 |
| POST | `/input/keyboard/focus_key` | 聚焦窗口并按键 |

交互式文档：http://127.0.0.1:7070/docs

## 窗口字段说明

每个 `WindowInfo` 包含：
- `id` — GNOME Meta 窗口 ID（用于聚焦、关闭、移动等操作）
- `xid` — X11 窗口 ID（用于 xdotool 的 focus_type / focus_key；Wayland 下为 0）
- `title` — 窗口标题
- `wm_class` — 窗口类名（如 `Code`、`Gnome-terminal`）
- `pid` — 进程 ID
- `focused` / `minimized` / `maximized` — 窗口状态
- `workspace` — 所在工作区索引
- `x`、`y`、`width`、`height` — 窗口位置和尺寸

## 故障排查

```bash
# 查看扩展状态
gnome-extensions show gnome-ai-bridge@local

# 查看守护进程日志
journalctl --user -u gnome-ai-daemon -f

# 扩展不稳定时禁用
gnome-extensions disable gnome-ai-bridge@local

# 重启守护进程
systemctl --user restart gnome-ai-daemon
```
