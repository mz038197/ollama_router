#!/usr/bin/env bash
# 修复 Ollama 0.30.8 + AMD MI210 多 instance GPU 配置
#
# 已知问题（MI210 + 0.30.8）：
# - OLLAMA_LLM_LIBRARY=rocm → 跳过 rocm_v7_2，library=cpu（HTTP 200 但 VRAM 不升）
# - 仅 ROCR + 默认 Vulkan → ErrorDeviceLost
# - 正确：HIP_VISIBLE_DEVICES + OLLAMA_VULKAN=false，且不要设 OLLAMA_LLM_LIBRARY
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "请用 sudo 运行: sudo bash $0"
  exit 1
fi

write_conf() {
  local idx="$1" port="$2" hip="$3"
  local conf="/etc/ollama/instance-${idx}.conf"
  cat > "$conf" <<EOF
OLLAMA_HOST=127.0.0.1:${port}
OLLAMA_KEEP_ALIVE=30m
OLLAMA_MAX_QUEUE=64
OLLAMA_NUM_PARALLEL=1
OLLAMA_ORIGINS=*
HIP_VISIBLE_DEVICES=${hip}
OLLAMA_VULKAN=false
OLLAMA_CONTEXT_LENGTH=131072
EOF
  echo "=== $conf ==="
  cat "$conf"
  echo
}

write_conf 0 11434 0
write_conf 1 11435 1
write_conf 2 11436 2
write_conf 3 11437 3

systemctl stop ollama 2>/dev/null || true
systemctl disable ollama 2>/dev/null || true
systemctl daemon-reload
systemctl restart ollama@{0,1,2,3}
sleep 12

echo "=== GPU discovery (ollama@0) ==="
journalctl -u ollama@0 -n 50 --no-pager | grep -iE 'inference compute|discover|library|vulkan|rocm|cpu|warn|HIP|skipping' || true

if journalctl -u ollama@0 -n 50 --no-pager | grep -q 'inference compute.*library=cpu'; then
  echo
  echo "失败：仍在 CPU（library=cpu）。"
  echo "Ollama 0.30.8 在 MI210 上可能无法稳定用 GPU。"
  echo "请降级到 0.20.3："
  echo "  sudo bash $(dirname "$0")/downgrade-ollama.sh"
  exit 1
fi

if ! journalctl -u ollama@0 -n 50 --no-pager | grep -qE 'library=ROCm|library=Vulkan'; then
  echo
  echo "失败：未发现 GPU 后端（无 ROCm/Vulkan）。"
  exit 1
fi

echo
echo "=== VRAM (before) ==="
if command -v rocm-smi >/dev/null; then
  rocm-smi --showmeminfo vram | grep -E 'GPU\[|Used' || true
fi

echo
echo "=== quick inference test (11434, llama3.2:3b) ==="
resp=$(curl -s -m 120 -w '\nHTTP_CODE:%{http_code}' http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"hi"}],"stream":false,"think":false,"options":{"num_predict":10,"num_ctx":4096}}')
body="${resp%%HTTP_CODE:*}"
code="${resp##*HTTP_CODE:}"
echo "HTTP $code"

if [[ "$code" != "200" ]]; then
  echo "$body"
  exit 1
fi

echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',{}).get('content') or d.get('error',''))"

if journalctl -u ollama@0 -n 80 --no-pager | grep -q 'CPU model buffer'; then
  echo
  echo "失败：模型加载在 CPU（CPU model buffer）。请运行 downgrade 脚本。"
  exit 1
fi

echo
echo "=== VRAM (after) ==="
if command -v rocm-smi >/dev/null; then
  rocm-smi --showmeminfo vram | grep -E 'GPU\[|Used' || true
fi

echo
echo "完成。若 VRAM Used 仍 ~16MB，请运行：sudo bash $(dirname "$0")/downgrade-ollama.sh"
