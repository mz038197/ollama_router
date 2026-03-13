# Ollama Router - OpenAI 相容負載平衡器

提供 OpenAI 相容 API（`/v1/chat/completions`、`/v1/models`），並支援多個 Ollama 後端負載平衡、API 金鑰驗證、日誌記錄與 Admin 管理面板。

## 快速開始

```bash
uv sync
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

管理面板：`http://localhost:8000/`

## API 端點

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /`
- `GET /api/admin/config`
- `POST /api/admin/teacher/add`
- `POST /api/admin/teacher/delete`
- `POST /api/admin/key/add`
- `POST /api/admin/key/status`
- `POST /api/admin/key/delete`

### Admin API 狀態碼（REST）

- `POST /api/admin/teacher/add`
  - `201 Created`：新增成功
  - `400 Bad Request`：教師名稱為空
- `POST /api/admin/teacher/delete`
  - `200 OK`：刪除成功
  - `400 Bad Request`：教師名稱為空
  - `404 Not Found`：教師不存在
- `POST /api/admin/key/add`
  - `201 Created`：新增成功
  - `400 Bad Request`：輸入欄位缺漏
- `POST /api/admin/key/status`
  - `200 OK`：更新成功
  - `400 Bad Request`：輸入欄位缺漏
  - `404 Not Found`：教師或金鑰不存在
- `POST /api/admin/key/delete`
  - `200 OK`：刪除成功
  - `400 Bad Request`：輸入欄位缺漏
  - `404 Not Found`：教師或金鑰不存在

### Admin 錯誤回應格式

```json
{
  "detail": {
    "code": "ADMIN_...",
    "message": "錯誤說明"
  }
}
```

## API 金鑰驗證

- 驗證路徑：`/v1/chat/completions`
- 讀取順序：
  1. `Authorization: Bearer <token>`
  2. `X-API-Key: <token>`
- 驗證規則：
  - 若未配置任何金鑰：允許所有請求
  - 若已配置金鑰：需提供有效且 `enabled=true` 的 key，否則回傳 `401`

配置檔路徑：`~/.ollama_router/apikeyConfig.json`

## Clean Architecture（Phase 1）

本專案已完成 Phase 1 分層，目標是「功能不變、依賴方向清楚」。

### 目錄結構

```text
.
├── app.py
├── src/
│   ├── bootstrap.py
│   ├── domain/
│   │   ├── entities/
│   │   └── ports/
│   ├── application/
│   │   ├── dto/
│   │   └── use_cases/
│   ├── infrastructure/
│   │   ├── gateways/
│   │   ├── logging/
│   │   └── repositories/
│   └── presentation/
│       └── fastapi/
│           ├── middleware/
│           ├── routers/
│           ├── schemas/
│           └── web/
│               └── admin.html
└── ...
```

### 分層責任

- `domain`：核心資料結構與抽象介面（ports）
- `application`：用例流程（chat/models/admin/auth）
- `infrastructure`：外部實作（httpx、JSON 檔案、log 檔）
- `presentation`：FastAPI 路由、middleware、request schema
- `app.py`：薄入口，只負責組裝與掛載

### 依賴方向

- `presentation -> application -> domain`
- `infrastructure -> domain(ports)`

## 主要設定

在 `app.py` 可調整：

```python
BACKENDS = [
    "http://127.0.0.1:11434",
    "http://127.0.0.1:11435",
]
REQUEST_TIMEOUT = 300.0
MAX_CONCURRENT_PER_BACKEND = 1
DEFAULT_NUM_PREDICT = 256
DEFAULT_TEMPERATURE = 0.7
```

## 日誌

日誌輸出路徑：`~/.ollama_router/log_YYYYMMDD.log`

內容包含：
- timestamp（UTC+8）
- teacher
- api_key（截斷）
- model
- validation_result
- message_preview

## 測試與檢查

```bash
# 語法檢查
python3 -m py_compile app.py

# 執行 Phase 2 測試分層（use case + API contract）
uv run pytest

# 僅執行 use case 單元測試
uv run pytest tests/application/use_cases

# 僅執行 API contract 測試
uv run pytest tests/presentation/fastapi/test_api_contract.py
```

### Phase 2 測試覆蓋

- Application use cases：
  - `AuthUseCase`
  - `AdminUseCase`
  - `ApiUseCase`（含 stream/non-stream 與記錄行為）
- FastAPI API contract：
  - `GET /health`
  - `GET /v1/models`
  - `POST /v1/chat/completions`（401 與成功路徑）
  - `GET /`
  - `GET /api/admin/config`
  - `POST /api/admin/teacher/add`
  - `POST /api/admin/teacher/delete`
  - `POST /api/admin/key/add`
  - `POST /api/admin/key/status`
  - `POST /api/admin/key/delete`

## Phase 2 規劃

- 補齊分層測試（application/use case、integration、API contract）
- 將錯誤模型標準化（domain/application error mapping）
- 強化 DI 與設定管理（多環境 config）
- 逐步清理舊模組相依（`auth.py`、`admin.py` 轉為相容層或移除）

## 系統需求

- Python 3.13+
- 一個或多個運行中的 Ollama 實例
