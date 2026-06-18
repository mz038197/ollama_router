# Ollama Router - OpenAI 相容負載平衡器

提供 OpenAI 相容 API（`/v1/chat/completions`、`/v1/responses`、`/v1/models`），並支援多個 Ollama 後端負載平衡、API 金鑰驗證、日誌記錄與 Admin 管理面板。

## 快速開始

```bash
uv sync
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

管理面板：`http://localhost:8000/`
Portal：`http://localhost:8000/portal`

使用自訂設定檔：

```powershell
$env:OLLAMA_ROUTER_CONFIG="D:\path\router.yaml"
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

範本見 [`config/router.example.yaml`](config/router.example.yaml)。

## API 端點

- `GET /health`
- `GET /v1/models`
- `POST /v1/chat/completions`
- `POST /v1/responses`
- `GET /`
- `GET /api/admin/config`
- `GET /api/admin/logs`
- `GET /api/admin/logs/{request_id}`
- `POST /api/admin/teacher/add`
- `POST /api/admin/teacher/delete`
- `POST /api/admin/key/add`
- `POST /api/admin/key/status`
- `POST /api/admin/key/delete`
- `GET /portal`
- `POST /auth/google`
- `GET /auth/me`
- `POST /sessions/redeem`
- `POST /teacher/classes`
- `POST /teacher/classes/{id}/sessions`
- `GET /teacher/classes/{id}/prompt-logs`
- `GET /admin/users`
- `GET /admin/classes`
- `GET /admin/settings`

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

- 驗證路徑：所有 `/v1/*`，包含 `/v1/models`、`/v1/chat/completions`、`/v1/responses`
- 讀取順序：
  1. `Authorization: Bearer <token>`
  2. `X-API-Key: <token>`
- 驗證規則：
  - 需提供有效且 `enabled=true` 的 key，否則回傳 `401`
  - Student key 需綁定有效上課 session，session 或班級過期後會失效
  - Teacher/Admin key 為長期 key，可由 Portal 手動重設

新 Portal 使用 SQLite：預設 `~/.ollama_router/router.db`。Legacy admin.html 仍保留舊 JSON 維運：`~/.ollama_router/apikeyConfig.json`。

## Pegasi Portal MVP

- Google 登入開發端點：`POST /auth/google`，傳入 `email`、`name` 後建立 HTTP-only session cookie。正式 OAuth client 設定由 `router.yaml` 保留。
- Role 指派：`auth.teacher_domain` 的信箱為 teacher；`auth.admin_emails` 為 admin teacher。
- Student：登入 `/portal` 後輸入老師提供的本節邀請碼，取得個人 `or_sk_...` API Key。
- Teacher/Admin：可建立班級、開本節 session、查看領取名單與 prompt logs。Admin 另可看使用者、全系統班級與設定摘要。
- 每筆 `/v1/chat/completions` 會寫入 SQLite `prompt_logs`，含 `user_id`、`class_id`、`session_id`、`raw_prompt`、`model`、`client_ip`。
- Prompt 監控支援班級、session、關鍵字與 ISO 時間範圍篩選。
- Admin 可停用/啟用使用者、調整 role、結束班級、觸發 prompt log 封存，並可寫回非機密設定：`prompt_logs.retention_days`、`student_default_ttl_hours`、`auth.open_registration`。
- 封存會將 ended 班級或超過 retention 的 `prompt_logs` 搬至 `archive_YYYY.db`，並由每日背景工作定期執行。

### Chat Completions 錯誤回應

- `/v1/chat/completions` 與 `/v1/responses` 錯誤時回 **OpenAI 格式**：`{"error": {"message", "type", "param", "code"}}`
- 串流錯誤以 SSE 送出：`data: {"error": ...}`
- Admin API 仍使用 FastAPI 風格：`{"detail": ...}`

### VS Code Copilot BYOK（`/v1/responses`）

Copilot 請使用 **`POST /v1/responses`**（非 `/v1/chat/completions`），並在 `chatLanguageModels.json` 設 `zeroDataRetentionEnabled: true`（Ollama 不支援 `previous_response_id`）。

完整設定、reasoning effort 說明與故障排除：**[guide/VSCODE_COPILOT_BYOK.md](guide/VSCODE_COPILOT_BYOK.md)**

`/v1/chat/completions` 仍保留給 Streamlit 等舊 client（預設 `think: false`）。

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
REQUEST_TIMEOUT = 900.0
MAX_CONCURRENT_PER_BACKEND = 1
DEFAULT_NUM_PREDICT = 200000
DEFAULT_TEMPERATURE = 0.7
```

## 日誌

採用**摘要檔 + 完整備份檔**雙檔架構：

| 檔案 | 用途 |
|------|------|
| `~/.ollama_router/logs/log_YYYYMMDD.log` | 日常查看（`tail -f`、admin 列表） |
| `~/.ollama_router/logs/full/log_YYYYMMDD.log` | 除錯用完整 `messages` 備份 |

兩檔以 `request_id` 對應。摘要檔欄位：

- `request_id`、`timestamp`、`client_ip`
- `teacher`、`api_key`（截斷）、`model`
- `validation_result`、`message_count`、`total_chars`
- `message_preview`（精簡預覽，優先抽取 `<userRequest>` / `<user_query>`）

完整檔含完整 `messages`（僅請求輸入，不含模型回覆）。

```bash
# 日常監控
tail -f ~/.ollama_router/logs/log_$(date +%Y%m%d).log

# 除錯完整內容
grep '<request_id>' ~/.ollama_router/logs/full/log_$(date +%Y%m%d).log | jq .
```

Admin API：`GET /api/admin/logs/{request_id}?date=YYYYMMDD`

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
