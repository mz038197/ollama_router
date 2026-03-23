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
    ROCR_VISIBLE_DEVICES=0
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1

## instance 1

``` bash
sudo nano /etc/ollama/instance-1.conf
```

    OLLAMA_HOST=127.0.0.1:11435
    ROCR_VISIBLE_DEVICES=1
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1

## instance 2

``` bash
sudo nano /etc/ollama/instance-2.conf
```

    OLLAMA_HOST=127.0.0.1:11436
    ROCR_VISIBLE_DEVICES=2
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1

## instance 3

``` bash
sudo nano /etc/ollama/instance-3.conf
```

    OLLAMA_HOST=127.0.0.1:11437
    ROCR_VISIBLE_DEVICES=3
    OLLAMA_KEEP_ALIVE=30m
    OLLAMA_MAX_QUEUE=64
    OLLAMA_NUM_PARALLEL=1

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

# 常見錯誤

## 405 Method Not Allowed

代表用錯 HTTP 方法。\
`/api/generate` 必須 POST。

## GPU 都跑同一張

檢查 `ROCR_VISIBLE_DEVICES` 是否設定正確。

## 修改設定沒生效

修改 `.conf` 後必須：

    systemctl restart ollama@X

## 修改 service 沒生效

需要：

    systemctl daemon-reload

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
