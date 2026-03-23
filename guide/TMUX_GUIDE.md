# Ubuntu tmux 使用完整指南（SSH 斷線程式仍持續執行）

作者：Vans AI Server 教學整理

------------------------------------------------------------------------

## 1. tmux 是什麼

tmux 是一個 **terminal multiplexer（終端多工工具）**，可以讓你：

-   在 SSH 斷線後程式仍然繼續執行
-   建立多個 terminal 視窗
-   隨時重新連回正在執行的工作

這在以下情境非常重要：

-   AI server
-   GPU training
-   Ollama server
-   長時間 Python 任務

------------------------------------------------------------------------

# 2. 安裝 tmux

在 Ubuntu 執行：

``` bash
sudo apt update
sudo apt install tmux -y
```

確認版本：

``` bash
tmux -V
```

如果看到類似

    tmux 3.x

代表安裝成功。

------------------------------------------------------------------------

# 3. 建立 tmux session

建立一個新的 session：

``` bash
tmux new -s mysession
```

例如：

``` bash
tmux new -s training
```

現在你已經在 tmux 裡面。

------------------------------------------------------------------------

# 4. 在 tmux 裡執行程式

例如執行 Python 程式：

``` bash
python train.py
```

或啟動 Ollama：

``` bash
ollama serve
```

------------------------------------------------------------------------

# 5. 離開 tmux（程式仍然繼續跑）

按鍵順序：

    Ctrl + B
    然後按 D

你會看到：

    [detached]

這代表：

-   tmux 還在
-   程式還在執行
-   你只是離開畫面

這時候你可以安全：

-   關閉 PuTTY
-   關閉 SSH
-   斷線

------------------------------------------------------------------------

# 6. 重新連回 tmux

重新 SSH 回 server：

``` bash
ssh user@server-ip
```

然後輸入：

``` bash
tmux attach -t mysession
```

你就會回到剛剛的畫面。

------------------------------------------------------------------------

# 7. 查看有哪些 tmux session

``` bash
tmux ls
```

例如：

    training: 1 windows
    ollama: 1 windows

------------------------------------------------------------------------

# 8. 關閉某個 session

``` bash
tmux kill-session -t training
```

------------------------------------------------------------------------

# 9. 完全關閉 tmux

``` bash
tmux kill-server
```

------------------------------------------------------------------------

# 10. AI Server 推薦架構

建議分不同 session：

    tmux
     ├─ ollama
     ├─ router
     ├─ training
     └─ logs

範例：

``` bash
tmux new -s ollama
ollama serve
```

``` bash
tmux new -s router
python server.py
```

``` bash
tmux new -s training
python train.py
```

------------------------------------------------------------------------

# 11. 最短記憶版

開 tmux

``` bash
tmux new -s test
```

離開但不中斷

    Ctrl + B
    D

回到 session

``` bash
tmux attach -t test
```

------------------------------------------------------------------------

# 12. 建議練習

測試 tmux：

``` bash
tmux new -s test
```

執行：

``` bash
for i in {1..1000}; do echo $i; sleep 1; done
```

離開

    Ctrl+B D

再連回

``` bash
tmux attach -t test
```

如果數字還在增加，代表成功。
