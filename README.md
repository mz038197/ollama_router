# Ollama Router - OpenAI 相容的負載平衡器

一個 OpenAI 相容的 API 路由器，提供 Ollama 後端的負載平衡、API 金鑰驗證和日誌記錄功能。

## 功能

- ✅ **OpenAI 相容** - 支持 `/v1/chat/completions` 和 `/v1/models` 端點
- ✅ **負載平衡** - 自動分配請求到多個 Ollama 後端
- ✅ **API 金鑰驗證** - 支持多教師、多班級的 API 金鑰管理
- ✅ **日誌記錄** - 完整的請求日誌，包含時間戳和教師資訊
- ✅ **流式回應** - 支持 OpenAI 風格的流式回應 (SSE)
- ✅ **健康檢查** - `/health` 端點用於監控後端狀態

## 快速開始

### 安裝依賴

```bash
uv sync
```

### 啟動服務

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

### 初始化 API 金鑰配置

```bash
uv run python init_config.py
```

## API 端點

### 1. 獲取可用模型列表

```
GET /v1/models
```

### 2. 聊天完成

```
POST /v1/chat/completions
```

**請求格式:**

```json
{
    "model": "llama2",
    "messages": [
        {
            "role": "user",
            "content": "你好"
        }
    ],
    "api_key": "sk-xxxxx",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 256
}
```

### 3. 健康檢查

```
GET /health
```

## API 金鑰管理

詳細資訊請參考 [API_KEY_AUTH_GUIDE.md](./API_KEY_AUTH_GUIDE.md)

### 快速配置

配置檔案位於 `~/.ollama_router/apikeyConfig.json`：

```json
{
    "老師A": {
        "api_keys": [
            {
                "name": "三年甲班",
                "key": "sk-teacher-a-class-1",
                "enabled": true
            }
        ]
    }
}
```

### 驗證行為

- **未配置任何金鑰**: 允許全部請求通過
- **已配置金鑰但未提供**: 拒絕請求 (401)
- **提供的金鑰已禁用**: 拒絕請求 (401)
- **提供有效且啟用的金鑰**: 允許請求通過

## 日誌

日誌檔案位於 `~/.ollama_router/log_YYYYMMDD.log`

每個日誌條目包含：
- 時間戳 (UTC+8)
- 教師名稱
- API 金鑰 (摘要)
- 模型
- 驗證結果
- 訊息預覽

## 測試

執行測試腳本以驗證所有功能：

```bash
uv run python test_auth.py
```

## 配置

編輯 `app.py` 中的以下變數以自訂行為：

```python
BACKENDS = [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11435",
    # ...
]

REQUEST_TIMEOUT = 300.0
MAX_CONCURRENT_PER_BACKEND = 1
DEFAULT_NUM_PREDICT = 256
DEFAULT_TEMPERATURE = 0.7
```

## 檔案結構

```
.
├── app.py                      # 主應用程式
├── auth.py                     # API 金鑰驗證和日誌管理
├── init_config.py              # 初始化配置腳本
├── test_auth.py                # 測試腳本
├── API_KEY_AUTH_GUIDE.md       # API 金鑰使用指南
├── README.md                   # 本檔案
└── pyproject.toml              # 專案配置
```

## 系統需求

- Python 3.13+
- 一個或多個運行中的 Ollama 實例

## 許可證

MIT
