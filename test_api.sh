#!/bin/bash

# ====================================
# Ollama Router API 測試範例
# ====================================

BASE_URL="http://localhost:8000"

echo "=== Ollama Router API 測試 ==="
echo

# 1. 健康檢查
echo "1. 健康檢查"
curl -s "${BASE_URL}/health" | jq .
echo
echo

# 2. 獲取模型列表
echo "2. 獲取模型列表"
curl -s "${BASE_URL}/v1/models" | jq .
echo
echo

# 3. 聊天完成 - 有效的 API 金鑰
echo "3. 聊天完成 - 有效的 API 金鑰 (sk-test-key-001)"
curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [
      {
        "role": "user",
        "content": "你好，請自我介紹"
      }
    ],
    "api_key": "sk-test-key-001",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 256
  }' | jq .
echo
echo

# 4. 聊天完成 - 無效的 API 金鑰 (應返回 401)
echo "4. 聊天完成 - 無效的 API 金鑰 (應返回 401 錯誤)"
curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [
      {
        "role": "user",
        "content": "你好"
      }
    ],
    "api_key": "sk-invalid-key",
    "stream": false
  }' | jq .
echo
echo

# 5. 聊天完成 - 流式回應
echo "5. 聊天完成 - 流式回應"
curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama2",
    "messages": [
      {
        "role": "user",
        "content": "請用一句話描述人工智能"
      }
    ],
    "api_key": "sk-test-key-001",
    "stream": true
  }' | head -5
echo
echo "... (流式回應可能很長，這裡只顯示前 5 行)"
echo
echo

echo "=== 測試完成 ==="
echo "若要查看完整的日誌，請執行:"
echo "  cat ~/.ollama_router/log_\$(date +%Y%m%d).log"
