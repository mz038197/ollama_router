# Ollama 多 Instance + 多 GPU（AMD ROCm）完整配置指南

本指南說明如何在 **Ubuntu Linux** 上部署 **多個 Ollama
instance**，並讓每個 instance 使用 **不同 GPU**，再透過 **Router API
分流學生請求**。

適用情境： - AI 教學伺服器 - 多學生同時使用 LLM - 多 GPU AMD ROCm 環境 -
Ollama API gateway 架構

------------------------------------------------------------------------

# 系統架構

    學生電腦
       ↓
    Router API (FastAPI / Node)
       ↓
    127.0.0.1:11434 → Ollama instance 0 → GPU0
    127.0.0.1:11435 → Ollama instance 1 → GPU1
    127.0.0.1:11436 → Ollama instance 2 → GPU2
    127.0.0.1:11437 → Ollama instance 3 → GPU3

優點： - 支援多人同時推論 - 每張 GPU 有獨立模型 - Router 可做 load
balancing - Ollama 不暴露在外網

------------------------------------------------------------------------

# Step 1 安裝 Ollama

官方安裝：

``` bash
curl -fsSL https://ollama.com/install.sh | sh
```

確認安裝：

``` bash
which ollama
```

通常會得到：

    /usr/bin/ollama

測試：

``` bash
ollama run llama3
```

------------------------------------------------------------------------

# Step 2 停用預設 Ollama service

``` bash
sudo systemctl stop ollama
sudo systemctl disable ollama
```

------------------------------------------------------------------------

# Step 3 建立設定資料夾

``` bash
sudo mkdir -p /etc/ollama
```

------------------------------------------------------------------------

# Step 4 建立 systemd template service

``` bash
sudo nano /etc/systemd/system/ollama@.service
```

內容：

    [Unit]
    Description=Ollama Instance %i
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=ollama
    Group=ollama
    WorkingDirectory=/usr/share/ollama
    EnvironmentFile=/etc/ollama/instance-%i.conf
    ExecStart=/usr/bin/ollama serve
    Restart=always
    RestartSec=3

    [Install]
    WantedBy=multi-user.target

------------------------------------------------------------------------

# Step 5 建立 instance 設定檔

## instance 0

``` bash
sudo nano /etc/ollama/instance-0.conf
```

    OLLAMA_HOST=127.0.0.1:11434
    HIP_VISIBLE_DEVICES=0
    OLLAMA_VULKAN=false
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1
    OLLAMA_CONTEXT_LENGTH=131072

> **Copilot 長對話**：若 `OLLAMA_CONTEXT_LENGTH=8192`，Copilot 送來的 prompt
> 常超過 8K（日誌 `truncating input prompt limit=8192 prompt=21663`），
> 短問題正常、長問題失敗。MI210 建議 **131072**（128K）；若 OOM 再改 **65536**。
> - **勿设** `OLLAMA_LLM_LIBRARY=rocm`（会跳过 GPU 库 → CPU，VRAM 不升）
> - 仅 `ROCR_VISIBLE_DEVICES` → Vulkan → `ErrorDeviceLost`
> - 0.30.8 尝试：`HIP_VISIBLE_DEVICES=N` + `OLLAMA_VULKAN=false`（不设 rocm）
> - 若仍 CPU / VRAM 不升 → 降级 0.20.3：`sudo bash scripts/downgrade-ollama.sh`

## instance 1

``` bash
sudo nano /etc/ollama/instance-1.conf
```

    OLLAMA_HOST=127.0.0.1:11435
    HIP_VISIBLE_DEVICES=1
    OLLAMA_VULKAN=false
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1
    OLLAMA_CONTEXT_LENGTH=131072

## instance 2

``` bash
sudo nano /etc/ollama/instance-2.conf
```

    OLLAMA_HOST=127.0.0.1:11436
    HIP_VISIBLE_DEVICES=2
    OLLAMA_VULKAN=false
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1
    OLLAMA_CONTEXT_LENGTH=131072

## instance 3

``` bash
sudo nano /etc/ollama/instance-3.conf
```

    OLLAMA_HOST=127.0.0.1:11437
    HIP_VISIBLE_DEVICES=3
    OLLAMA_VULKAN=false
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1
    OLLAMA_CONTEXT_LENGTH=131072

------------------------------------------------------------------------

# Step 6 重新載入 systemd

``` bash
sudo systemctl daemon-reload
```

------------------------------------------------------------------------

# Step 7 啟動所有 instance

``` bash
sudo systemctl enable --now ollama@0
sudo systemctl enable --now ollama@1
sudo systemctl enable --now ollama@2
sudo systemctl enable --now ollama@3
```

------------------------------------------------------------------------

# Step 8 確認 instance 運行

``` bash
systemctl list-units --type=service | grep ollama
```

應該看到：

    ollama@0.service
    ollama@1.service
    ollama@2.service
    ollama@3.service

------------------------------------------------------------------------

# Step 9 測試 API

``` bash
curl http://127.0.0.1:11434/api/tags
curl http://127.0.0.1:11435/api/tags
curl http://127.0.0.1:11436/api/tags
curl http://127.0.0.1:11437/api/tags
```

如果回 JSON，代表 instance 成功。

------------------------------------------------------------------------

# Step 10 測試推論

``` bash
curl http://127.0.0.1:11434/api/generate -d '{
"model":"gemma3:27b",
"prompt":"介紹台中",
"stream":false
}'
```

------------------------------------------------------------------------

# Step 11 確認 GPU 使用情況

開另一個 terminal：

``` bash
watch -n 1 rocm-smi
```

然後分別打不同 port：

    11434
    11435
    11436
    11437

觀察 GPU usage：

  port    GPU
  ------- ------
  11434   GPU0
  11435   GPU1
  11436   GPU2
  11437   GPU3

------------------------------------------------------------------------

# Step 12 Router 架構

學生不直接打 Ollama，而是打 Router。

    students
       ↓
    router API
       ↓
    127.0.0.1:11434
    127.0.0.1:11435
    127.0.0.1:11436
    127.0.0.1:11437

Router 可以做：

-   Load balance
-   Queue
-   Logging
-   API key
-   Rate limit

------------------------------------------------------------------------

# Router Backend Example

``` python
BACKENDS = [
"http://127.0.0.1:11434",
"http://127.0.0.1:11435",
"http://127.0.0.1:11436",
"http://127.0.0.1:11437",
]
```

------------------------------------------------------------------------

# 更新 Ollama（維護）

本環境使用 **多 instance（`ollama@0`～`ollama@3`）**，更新方式與一般單機不同。
官方安裝腳本會順便 **啟用並啟動預設 `ollama.service`（佔用 11434）**，
若未停用會與 `ollama@0` 衝突；且舊 instance 若未重啟，記憶體中仍是舊版程式。

## 更新前確認

``` bash
ollama --version
systemctl is-active ollama@0 ollama@1 ollama@2 ollama@3
```

## 標準更新流程

**建議順序：先停 instance → 更新 → 停用預設 service → 重啟 instance → 驗證。**

### Step A 停止所有 instance

``` bash
sudo systemctl stop ollama@0 ollama@1 ollama@2 ollama@3
```

### Step B 執行官方更新

``` bash
curl -fsSL https://ollama.com/install.sh | sh
```

安裝腳本會更新 `/usr/local/bin/ollama`（或 `/usr/bin/ollama`），
**不會刪除已下載的模型**（模型通常在 `~/.ollama/models`）。

### Step C 停用預設 Ollama service（必做）

安裝腳本每次都可能重新 enable 預設 service，必須再次停用：

``` bash
sudo systemctl stop ollama
sudo systemctl disable ollama
```

### Step D 重啟所有 instance

``` bash
sudo systemctl start ollama@0 ollama@1 ollama@2 ollama@3
```

或：

``` bash
sudo systemctl restart ollama@0 ollama@1 ollama@2 ollama@3
```

更新後請確認 `/etc/ollama/instance-*.conf`：

- **有** `OLLAMA_CONTEXT_LENGTH=131072`
- **没有** `OLLAMA_LLM_LIBRARY=rocm`（会导致 CPU 回退）

可执行：`sudo bash scripts/fix-ollama-gpu.sh`

### Step E 驗證版本與 API

各 port 的 server 版本應一致，且不應出現 client/server 版本不一致警告：

``` bash
for p in 11434 11435 11436 11437; do
  echo "=== port $p ==="
  OLLAMA_HOST=127.0.0.1:$p ollama --version
  curl -sf "http://127.0.0.1:$p/api/version" && echo
done
```

確認服務狀態：

``` bash
systemctl status ollama@0 ollama@1 ollama@2 ollama@3
```

### Step F 測試拉模型（可選）

若先前因版本過舊無法拉取新模型，更新後再試：

``` bash
ollama pull nemotron3:33b
```

## 一鍵更新（複製整段）

``` bash
sudo systemctl stop ollama@0 ollama@1 ollama@2 ollama@3 && \
curl -fsSL https://ollama.com/install.sh | sh && \
sudo systemctl stop ollama && \
sudo systemctl disable ollama && \
sudo systemctl start ollama@0 ollama@1 ollama@2 ollama@3 && \
sleep 3 && \
for p in 11434 11435 11436 11437; do
  echo "=== port $p ==="
  OLLAMA_HOST=127.0.0.1:$p ollama --version
  curl -sf "http://127.0.0.1:$p/api/version" && echo
done
```

## 更新後 Router 是否需要重啟？

一般 **不需要**。Ollama backend 位址不變（11434～11437）。
若 Router 連線異常，再重啟 Router 服務即可。

## 更新相關常見狀況

| 狀況 | 原因 | 處理 |
|------|------|------|
| `ollama --version` 顯示版本不一致警告 | instance 未重啟，仍在跑舊 process | 執行 Step D 重啟 `ollama@*` |
| 11434 被占用或行為異常 | 預設 `ollama.service` 與 `ollama@0` 衝突 | 執行 Step C 停用預設 service |
| `pull model` 提示需要更新 Ollama | 二進位尚未更新或 instance 仍為舊版 | 完成 Step B～D 後再 `ollama pull` |
| 權限錯誤 | 安裝需 root | 使用 `curl ... \| sh`（腳本內會 sudo） |

------------------------------------------------------------------------

# 常見錯誤

## 405 Method Not Allowed

代表用錯 HTTP 方法。\
`/api/generate` 必須 POST。

## GPU 都跑同一張

檢查各 instance 的 `HIP_VISIBLE_DEVICES` 是否為 0/1/2/3（勿只用
`ROCR_VISIBLE_DEVICES`，0.30.8 仍可能走 Vulkan）。

## HTTP 500 / `vk::Queue::submit: ErrorDeviceLost`

代表 **Vulkan 後端** 在 MI210 上初始化失敗（重開機通常無法自行修復）。

日誌特徵：`library=Vulkan`、`Vulkan0 KV buffer`、然後 `ErrorDeviceLost`。

修復：強制 ROCm 並關閉 Vulkan：

``` bash
sudo bash ~/Programs/ollama_router/scripts/fix-ollama-gpu.sh
```

各 instance 應含 `HIP_VISIBLE_DEVICES=N`、`OLLAMA_LLM_LIBRARY=rocm`、
`OLLAMA_VULKAN=false`。成功後日誌應為 `library=ROCm`，而非 `library=Vulkan`。

## 修改設定沒生效

修改 `.conf` 後必須：

    systemctl restart ollama@X

## 修改 service 沒生效

需要：

    systemctl daemon-reload

## GPU 沒反應 / VRAM 一直是 0%

Ollama 0.30+ 若設了 `ROCR_VISIBLE_DEVICES` + `OLLAMA_LLM_LIBRARY=rocm`（未用
`HIP_VISIBLE_DEVICES`），啟動日誌可能出現 `library=cpu`，模型在 **CPU**
跑（很慢，`rocm-smi` 無 VRAM 占用）。若只設 `ROCR_VISIBLE_DEVICES` 而不關
Vulkan，則可能 `library=Vulkan` 並觸發 `ErrorDeviceLost`。

修復：

``` bash
sudo bash ~/Programs/ollama_router/scripts/fix-ollama-gpu.sh
```

## Ollama 版本不一致 / pull 模型要求更新

若看到 `client version is X` 警告，或 pull 時提示需要新版 Ollama，
代表 **二進位已更新但 `ollama@*` instance 尚未重啟**。
請依上方 **「更新 Ollama（維護）」** 章節完成 Step C～E。

------------------------------------------------------------------------

# 完整完成架構

    Students
       ↓
    Router API
       ↓
    Ollama instances
       ↓
    Multi GPU

------------------------------------------------------------------------

# 延伸建議

建議再加入：

-   API Gateway
-   GPU scheduler
-   Streaming API
-   OpenAI compatible API
