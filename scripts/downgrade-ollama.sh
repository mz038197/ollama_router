#!/usr/bin/env bash
# 降级 Ollama 到 0.20.3（本机 MI210 更新前可用版本）并恢复 ROCR 多 GPU 配置
set -euo pipefail

TARGET_VERSION="${OLLAMA_VERSION:-0.20.3}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "请用 sudo 运行: sudo bash $0"
  exit 1
fi

write_conf() {
  local idx="$1" port="$2" rocr="$3"
  local conf="/etc/ollama/instance-${idx}.conf"
  cat > "$conf" <<EOF
OLLAMA_HOST=127.0.0.1:${port}
OLLAMA_KEEP_ALIVE=30m
OLLAMA_MAX_QUEUE=64
OLLAMA_NUM_PARALLEL=1
OLLAMA_ORIGINS=*
ROCR_VISIBLE_DEVICES=${rocr}
OLLAMA_CONTEXT_LENGTH=131072
EOF
  echo "=== $conf ==="
  cat "$conf"
  echo
}

echo "=== 停止服务 ==="
systemctl stop ollama 2>/dev/null || true
systemctl stop ollama@{0,1,2,3} 2>/dev/null || true

echo "=== 安装 Ollama ${TARGET_VERSION} ==="
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION="${TARGET_VERSION}" sh

write_conf 0 11434 0
write_conf 1 11435 1
write_conf 2 11436 2
write_conf 3 11437 3

systemctl disable ollama 2>/dev/null || true
systemctl daemon-reload
systemctl restart ollama@{0,1,2,3}
sleep 10

echo "=== 版本 ==="
OLLAMA_HOST=127.0.0.1:11434 /usr/local/bin/ollama --version || ollama --version

echo
echo "=== GPU discovery (ollama@0) ==="
journalctl -u ollama@0 -n 40 --no-pager | grep -iE 'inference compute|library|rocm|vulkan|cpu|GPU' || true

echo
echo "=== 推理测试 ==="
curl -sf -m 120 http://127.0.0.1:11434/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.2:3b","messages":[{"role":"user","content":"hi"}],"stream":false,"options":{"num_predict":5}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',{}).get('content',''))"

echo
echo "请执行 watch -n1 rocm-smi 确认 VRAM 上升。"
