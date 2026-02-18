#!/usr/bin/env bash
# scripts/start_vllm.sh — Launch vLLM model server for the desktop agent
#
# GPU 显存建议：
#   Qwen2.5-VL-7B-Instruct   → 至少 16 GB（BF16）/ 8 GB（AWQ 4-bit）
#   Qwen2.5-VL-3B-Instruct   → 至少  8 GB（BF16）/ 4 GB（AWQ 4-bit）
#
# 本机 MX450 仅 2GB，无法本地运行 VL 模型。
# 你可以在远程 GPU 服务器运行本脚本，然后让 Agent 指向远端：
#   MODEL_API_BASE=http://<server-ip>:8000/v1 .venv/bin/python run_agent.py "..."
#
# 用法：
#   bash scripts/start_vllm.sh                          # 默认 7B
#   MODEL=Qwen/Qwen2.5-VL-3B-Instruct bash scripts/start_vllm.sh  # 3B
#   QUANTIZATION=awq bash scripts/start_vllm.sh         # 4-bit 量化
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-VL-7B-Instruct}"
HOST="${VLLM_HOST:-0.0.0.0}"
PORT="${VLLM_PORT:-8000}"
QUANTIZATION="${QUANTIZATION:-}"           # 留空=不量化；"awq" | "gptq"
GPU_MEMORY_UTIL="${GPU_MEMORY_UTIL:-0.90}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"     # VL 模型 context 不需太长
TENSOR_PARALLEL="${TENSOR_PARALLEL:-1}"    # 多卡改大

echo "=== vLLM Model Server ==="
echo "  Model:           $MODEL"
echo "  Host:            $HOST:$PORT"
echo "  GPU mem util:    $GPU_MEMORY_UTIL"
echo "  Max model len:   $MAX_MODEL_LEN"
echo "  Tensor parallel: $TENSOR_PARALLEL"
[[ -n "$QUANTIZATION" ]] && echo "  Quantization:    $QUANTIZATION"
echo

# ── GPU preflight: avoid confusing OOM during model load ──────────────────
if command -v nvidia-smi &>/dev/null; then
    TOTAL_MIB=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -d ' ')
    USED_MIB=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits 2>/dev/null | head -n1 | tr -d ' ')
    if [[ -n "${TOTAL_MIB:-}" && -n "${USED_MIB:-}" ]]; then
        FREE_MIB=$((TOTAL_MIB - USED_MIB))
        echo "  GPU memory:      total=${TOTAL_MIB}MiB used=${USED_MIB}MiB free=${FREE_MIB}MiB"

        # For Qwen2.5-VL family, 2GB cards cannot run in vLLM.
        if [[ "$TOTAL_MIB" -lt 4000 ]]; then
            echo
            echo "[ERROR] 当前 GPU 总显存仅 ${TOTAL_MIB}MiB，无法运行 Qwen2.5-VL 系列（即使 3B + 4bit 也通常不够）。"
            echo "建议："
            echo "  1) 在远端 GPU 服务器运行此脚本（推荐 >=8GB 显存）"
            echo "  2) 本机仅运行 Agent，并设置 MODEL_API_BASE 指向远端"
            echo
            echo "本机运行示例："
            echo "  MODEL_API_BASE=http://<remote-ip>:8000/v1 .venv/bin/python run_agent.py --realtime \"打开终端并输入 hello world\""
            exit 2
        fi
    fi
fi

# 检查 vllm 是否安装
if ! python3 -m vllm.entrypoints.openai.api_server --help &>/dev/null; then
    echo "[ERROR] vllm 未安装，请先运行："
    echo "  pip install vllm"
    exit 1
fi

ARGS=(
    --model "$MODEL"
    --host "$HOST"
    --port "$PORT"
    --gpu-memory-utilization "$GPU_MEMORY_UTIL"
    --max-model-len "$MAX_MODEL_LEN"
    --tensor-parallel-size "$TENSOR_PARALLEL"
    --trust-remote-code
    --dtype auto
)

if [[ -n "$QUANTIZATION" ]]; then
    ARGS+=(--quantization "$QUANTIZATION")
fi

echo "Starting: python3 -m vllm.entrypoints.openai.api_server ${ARGS[*]}"
echo
exec python3 -m vllm.entrypoints.openai.api_server "${ARGS[@]}"
