# VS Code Copilot BYOK 使用指南（`/v1/responses`）

本指南說明如何透過 **Ollama Router** 的 **`POST /v1/responses`** 端點，在 VS Code 以 BYOK（Bring Your Own Key）方式使用本機 Ollama 模型（含 Copilot 思考 UI 與 reasoning effort 設定）。

適用對象：教師、學生、需在 VS Code Chat 使用本機 LLM 的使用者。

------------------------------------------------------------------------

# 1. 概述

## Router 提供兩種 OpenAI 相容 Chat 端點

| 端點 | 用途 | 思考（Thinking） |
|------|------|------------------|
| `POST /v1/chat/completions` | Streamlit 等舊 client | Router 強制 `think: false` |
| **`POST /v1/responses`** | **VS Code Copilot BYOK** | 支援 `reasoning.effort`，可顯示 Thinking UI |

**VS Code Copilot 請使用 `/v1/responses`**，才能正常顯示思考過程並控制 reasoning effort。

## 架構

    VS Code Copilot
           ↓
    Router（:8000/v1/responses）
           ↓
    Ollama instance（11434～11437，負載平衡）

------------------------------------------------------------------------

# 2. VS Code 設定

## 2.1 開啟設定檔

1. VS Code：**Chat → Manage Language Models**
2. 編輯 `chatLanguageModels.json`

常見路徑：

- Linux Stable：`~/.config/Code/User/chatLanguageModels.json`
- Linux Insiders：`~/.config/Code - Insiders/User/chatLanguageModels.json`

## 2.2 設定範例

將 `YOUR_ROUTER_HOST` 換成 Router 位址（例如教學伺服器 IP），`YOUR_API_KEY` 換成 Admin 面板核發的金鑰（若未啟用金鑰驗證可省略）：

```json
[
  {
    "name": "Ollama Router",
    "vendor": "customendpoint",
    "apiKey": "YOUR_API_KEY",
    "apiType": "responses",
    "models": [
      {
        "id": "gemma4:26b",
        "name": "Gemma 4 26B",
        "url": "http://YOUR_ROUTER_HOST:8000/v1/responses",
        "apiType": "responses",
        "toolCalling": true,
        "thinking": true,
        "supportsReasoningEffort": ["none", "low", "medium", "high"],
        "reasoningEffortFormat": "responses",
        "zeroDataRetentionEnabled": true,
        "maxInputTokens": 98304,
        "maxOutputTokens": 32768
      }
    ]
  }
]
```

## 2.3 重要欄位說明

| 欄位 | 必填 | 說明 |
|------|------|------|
| `apiType` | 是 | 設 `"responses"` |
| `url` | 是 | 指向 Router 的 `/v1/responses`，不是 Ollama 的 11434 |
| `thinking` | 是 | 設 `true` 以啟用 reasoning 能力 |
| `reasoningEffortFormat` | 是 | 設 `"responses"`，送出巢狀 `reasoning.effort` 物件 |
| `zeroDataRetentionEnabled` | **強烈建議** | 設 `true`：每輪送完整 history，不送 `previous_response_id` |
| `supportsReasoningEffort` | 建議 | 陣列需含 `"none"` 才可在模型選擇器選「關閉思考」；Ollama 接受 `none/low/medium/high/max` |
| `maxInputTokens` | 選填 | 輸入（history、@檔案、system）上限；見 **2.5 Token 預算** |
| `maxOutputTokens` | 選填 | 單次輸出（含 thinking + 程式碼）上限；見 **2.5 Token 預算** |

## 2.5 Token 預算（配合 `OLLAMA_CONTEXT_LENGTH=131072`）

伺服器 context 上限 **128K = 輸入 + 輸出合計**，兩欄不可各自拉滿。

**本指南預設定位：學生以 Coding 為主**（生成整檔、重構、debug 含長 code block）：

| 欄位 | 建議值 | 說明 |
|------|--------|------|
| `maxInputTokens` | **98304**（96K） | 保留 history + `@` 引用檔案的空間 |
| `maxOutputTokens` | **32768**（32K） | 約 1000+ 行程式碼量級，含 thinking 仍充裕 |
| 合計 | 131072 | 對齊 128K context |

**32K 輸出是否夠？** 對教學 Coding 通常夠：單檔作業、一個 class、中等規模 refactor。若常一次生成「整個專案多檔」，可改 **`maxOutputTokens: 40960`（40K）** 並將 `maxInputTokens` 降為 **90112（88K）**，合計仍須 ≤ 131072。

**其他組合（仍合計 128K）：**

| 場景 | maxInputTokens | maxOutputTokens |
|------|----------------|-----------------|
| Coding 高需求（**預設**） | 98304 | 32768 |
| 偏長回答、單檔超大 | 90112 | 40960 |
| 偏長 history、短回答 | 122880 | 8192 |

**Coding 實務建議：**

- 生成／改 code 求速度：Thinking Effort 選 **`none`** 或 **`low`**
- 複雜演算法、架構設計：再用 **`medium` / `high`**
- 新題目 **開新 Chat**，避免舊 code history 占滿 96K 輸入
- 精準 `@` 需要的檔案，不要依賴整段對話累積

## 2.6 在 VS Code 選擇 Thinking Effort

設定 `supportsReasoningEffort` 後，Chat 模型選擇器會出現 **Thinking Effort** 子選單。

常見等級：

- `none` — 關閉模型內部推理（見第 3 章）
- `low` / `medium` / `high` — 推理深度遞增，UI 會顯示 Thinking 區塊

> **注意**：勿在 `supportsReasoningEffort` 中使用 `"minimal"`。Ollama 不支援此值，會回傳 `400`。

------------------------------------------------------------------------

# 3. Reasoning Effort 說明

## 3.1 `none`  vs  `low` / `high`

| | `reasoning.effort: "none"` | `reasoning.effort: "low"` 以上 |
|---|---------------------------|--------------------------------|
| 模型內部是否推理 | **否**，直接生成答案 | **是**，先推理再回答 |
| 回應是否含 reasoning 區塊 | 否 | 是（Copilot Thinking UI） |
| 輸出 token | 少 | 多 |
| 典型延遲（短 prompt） | 較快（例如 ~1s） | 較慢（例如 ~3～5s） |

**`none` 不是「藏起推理過程」，而是關掉推理階段本身。**

## 3.2 為何選了 `none` 體感差異不大？

Copilot 每輪會送 **完整對話歷史**（含 system prompt、工具定義），常達 **數萬字符**。此時：

- 主要耗時在 **讀取長 history（prefill）**，常占 10～30+ 秒
- 思考階段通常只多 **2～4 秒**
- 簡單閒聊（「你好」）即使開 `high` 也不會想很久

**建議自測方式：**

1. **開新對話**（清空 history）再比較 `none` vs `high`
2. 觀察 UI：`high` 應先出現 **Thinking / Reasoning** 區塊；`none` 不應出現
3. 用推理題（非閒聊）測試，差異較明顯

## 3.3 直接測試 Ollama（略過 VS Code）

```bash
# none：無 reasoning 區塊、output_tokens 少
curl -s http://127.0.0.1:11434/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4:26b","input":"1+1=?","reasoning":{"effort":"none"},"max_output_tokens":50,"stream":false}' \
  | jq '{types:[.output[].type], out:.usage.output_tokens}'

# high：有 reasoning 區塊、output_tokens 多
curl -s http://127.0.0.1:11434/v1/responses \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4:26b","input":"1+1=?","reasoning":{"effort":"high"},"max_output_tokens":200,"stream":false}' \
  | jq '{types:[.output[].type], out:.usage.output_tokens}'
```

------------------------------------------------------------------------

# 4. 與 `/v1/chat/completions` 的差異

| 項目 | `/v1/chat/completions` | `/v1/responses` |
|------|------------------------|-----------------|
| 適用 client | Streamlit、一般 OpenAI SDK | VS Code Copilot BYOK |
| `think` / reasoning | Router 固定 `think: false` | 轉發 `reasoning.effort` |
| Copilot Thinking UI | 不支援 | 支援 |
| `previous_response_id` | 不適用 | **不支援**（見第 5 章） |

------------------------------------------------------------------------

# 5. 限制與已知行為

## 5.1 不支援 `previous_response_id`

Ollama 為 **stateless**，無法像 OpenAI 一樣用 `previous_response_id` 接續上一輪 response。

- 請設 **`zeroDataRetentionEnabled: true`**
- 若 client 仍送 `previous_response_id`，Router 回 **`400`**（code: `previous_response_not_found`）
- Copilot 通常會重試並改送 full history

## 5.2 非 Thinking 模型

若模型不支援 thinking（例如 `llama3.2:3b`），Router 會自動移除請求中的 `reasoning` 欄位再轉發，不會報錯。

## 5.3 API 金鑰

與 `/v1/chat/completions` 相同：

- Header：`Authorization: Bearer <token>` 或 `X-API-Key: <token>`
- 配置檔：`~/.ollama_router/apikeyConfig.json`
- 錯誤格式：OpenAI 風格 `{"error": {...}}`

------------------------------------------------------------------------

# 6. 與 Ollama 伺服器設定的關係

以下由伺服器管理員設定，使用者通常不需修改。詳見 [OLLAMA_MULTIPLE_GPU_SETUP.md](./OLLAMA_MULTIPLE_GPU_SETUP.md)。

| 設定 | 目前建議值 | 與 Copilot 的關係 |
|------|-----------|-------------------|
| `OLLAMA_CONTEXT_LENGTH` | **131072**（128K） | 輸入 history 上限；低於此值長對話會被截斷 |
| `OLLAMA_KEEP_ALIVE` | **30m** | 請求後模型留在 VRAM 的時間 |
| `OLLAMA_NUM_PARALLEL` | **1** | 每 GPU 同時 1 個推理；多人靠多 instance 分流 |

## Context 與 VRAM

- `OLLAMA_CONTEXT_LENGTH` 是 **上限**，不是固定占用
- **KV cache 會隨實際對話長度動態增長**，聊越久 VRAM 越高、速度越慢
- 長對話後某張 GPU VRAM 可能明顯高於其他卡（該卡處理過較長 context）
- 模型頁面若寫 256K context，**不代表 MI210 + gemma4:26b 適合改到 256K**；目前維持 128K

**使用者實用建議：**

- 對話變慢時，**開新 Chat** 比切換 reasoning effort 更有效
- 長時間不用可請管理員卸載模型以釋放 VRAM

------------------------------------------------------------------------

# 7. 故障排除

| 狀況 | 可能原因 | 處理 |
|------|----------|------|
| 回 `400` `previous_response_not_found` | 未設 `zeroDataRetentionEnabled` | 設為 `true` 並重開 VS Code |
| 沒有 Thinking UI | 用了 `/v1/chat/completions` 或 effort 為 `none` | 確認 url 為 `/v1/responses`；改 `low` 以上 |
| 長對話失敗、短問題正常 | context 超過上限 | 開新對話；請管理員確認 `OLLAMA_CONTEXT_LENGTH=131072` |
| 日誌出現 `truncating input prompt` | 同上 | 同上 |
| `invalid reasoning value: "minimal"` | VS Code 送了 Ollama 不支援的 effort | 改用 `none`，勿用 `minimal` |
| 整體很慢 | 長 history + 大模型 | 開新對話；可試 `reasoning.effort: "none"` |
| `401` | API 金鑰錯誤或未提供 | 檢查 Admin 面板金鑰與 Header |

## 查看 Router 請求日誌

```bash
tail -f ~/.ollama_router/logs/log_$(date +%Y%m%d).log
```

摘要檔含 `message_count`、`total_chars`，可確認 Copilot 是否送了過長 history。

------------------------------------------------------------------------

# 8. 相關文件

- [README.md](../README.md) — 專案概覽與快速開始
- [OLLAMA_MULTIPLE_GPU_SETUP.md](./OLLAMA_MULTIPLE_GPU_SETUP.md) — 多 GPU、Ollama instance、context / VRAM 伺服器設定
