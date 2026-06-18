# Google OAuth 實作與現況交接文件

> 最後更新：2026-06-18  
> 目的：讓下一次接手的 agent 能快速理解 Portal Google 登入的實作狀態、設定位置、已解決問題與待處理阻塞。

---

## 1. 背景

使用者要求將 Pegasi Router Portal 的「Google 登入」從**開發用 stub**（手動填 email/name）改為**真正的 Google OAuth 驗證**。

### 實作前（舊行為）

- `POST /auth/google` 直接信任客戶端傳入的 `email`、`name`
- `router.yaml` 的 `google_client_id` / `google_client_secret` 僅預留，程式未使用
- `portal.html` 有 bug：`name` 變數撞到 `window.name`，導致 422（已修）

### 實作後（現行設計）

- **Authorization Code Flow**（伺服器端換 token + 驗證 `id_token`）
- OAuth 已設定時：Portal 顯示「使用 Google 帳號登入」按鈕
- OAuth 未設定時：保留開發模式手動登入
- `open_registration: false` 時，新使用者無法透過 OAuth 註冊（既有使用者可登入）

---

## 2. 架構與端點

```text
使用者 → GET /auth/google/login
       → Google 授權頁
       → GET /auth/google/callback?code=...&state=...
       → 伺服器 POST https://oauth2.googleapis.com/token
       → 驗證 id_token（google-auth）
       → upsert 使用者 + 設定 session cookie
       → redirect /portal
```

| 端點 | 用途 |
|------|------|
| `GET /auth/config` | 回傳 `oauth_enabled`、`redirect_uri` |
| `GET /auth/google/login` | 產生 state cookie，302 導向 Google |
| `GET /auth/google/callback` | 驗證 state、交換 code、建立 session |
| `POST /auth/google` | 僅在 OAuth **未**設定時可用（開發模式） |
| `GET /auth/me` | 讀取 session cookie |

### 關鍵原始碼

| 檔案 | 說明 |
|------|------|
| `src/infrastructure/auth/google_oauth.py` | OAuth 服務：state 簽章、authorize URL、code 交換、id_token 驗證 |
| `src/presentation/fastapi/routers/portal_router.py` | Portal 路由與 callback 處理 |
| `src/presentation/fastapi/web/portal.html` | 依 `/auth/config` 切換 OAuth 按鈕 / 開發模式表單 |
| `src/application/use_cases/portal_use_case.py` | `google_login()` 含 `open_registration` 檢查 |
| `src/infrastructure/repositories/sqlite_router_repository.py` | 新增 `get_user_by_email()` |
| `app.py` / `src/bootstrap.py` | 傳入 `router_settings` 給 portal router |

### 相依套件（已加入 `pyproject.toml`）

- `google-auth`
- `requests`（google-auth 驗證 id_token 時需要）

---

## 3. 設定檔位置

### 正式設定（程式讀這個）

```text
~/.ollama_router/router.yaml
```

**注意**：程式**不讀**專案根目錄的 `.env`。`.env` 內雖有 `client_id` / `client_secret`，但僅供使用者手動參考，必須寫入 `router.yaml` 才生效。

### 環境變數（可選）

```text
OLLAMA_ROUTER_CONFIG=/path/to/router.yaml
```

未設定時預設讀 `~/.ollama_router/router.yaml`（見 `src/infrastructure/config.py`）。

### 目前 `router.yaml` 摘要（2026-06-18）

```yaml
public_url: "http://203-71-78-31.nip.io:8000"

auth:
  teacher_domain: "school.edu"
  admin_emails:
    - "mz038197@gmail.com"
  google_client_id: "<已設定，見 router.yaml>"
  google_client_secret: "<已設定，見 router.yaml>"
  session_secret: "<已從 change-me 改為隨機字串>"
  open_registration: true
```

**Google Console Authorized redirect URI 必須為：**

```text
http://203-71-78-31.nip.io:8000/auth/google/callback
```

**勿將 client_secret / session_secret 提交 git 或寫進此文件的公開副本。**

---

## 4. nip.io 與 public_url 規則

Google OAuth **不接受**純 IP（如 `192.168.7.16`）作為 redirect URI。

| 情境 | public_url 建議 |
|------|-----------------|
| 區網使用（伺服器 LAN IP `192.168.7.16`） | `http://192-168-7-16.nip.io:8000` |
| 公網 IP `203.71.78.31` | `http://203-71-78-31.nip.io:8000`（目前設定） |
| 僅伺服器本機測試 | `http://127.0.0.1:8000` 或 `http://localhost:8000` |

**三者必須一致**：使用者開 Portal 的網址、`public_url`、Google Console redirect URI。

目前使用者從 `192.168.7.16` 存取伺服器，但 `public_url` 設為 `203-71-78-31.nip.io`（公網 nip.io）。若只在區網使用，建議改為 `192-168-7-16.nip.io` 並同步更新 Google Console。

---

## 5. 已解決的問題

### 5.1 Portal 登入 422

- **原因**：`portal.html` 中 `name.value` 解析到 `window.name`，JSON body 缺少 `name`
- **修復**：改用 `document.getElementById('name')`（後續 OAuth UI 改為 `displayName`）

### 5.2 session_secret 為預設值

- **原因**：`session_secret: "change-me"`
- **修復**：已產生隨機 `session_secret` 寫入 `~/.ollama_router/router.yaml`

### 5.3 OAuth 錯誤訊息太籠統

- **原因**：callback 中 `except Exception` 吞掉細節
- **修復**：`google_oauth.py` 對 `httpx.HTTPStatusError`、`TimeoutException`、`HTTPError` 與 id_token 驗證失敗拋出可讀的 `ValueError`，Portal 以 `?login_error=` 顯示

---

## 6. 目前阻塞問題（最重要）

### 症狀

Terminal log 範例：

```text
GET /auth/google/login        → 302 OK
GET /auth/google/callback     → 302 OK（有 code）
GET /portal?login_error=...   → Google 登入失敗
GET /auth/me                  → 401
```

代表：瀏覽器 ↔ Google 正常，但**伺服器無法完成 token 交換**。

### 根因（已驗證）

在 `MKSH-AI-Server` 上執行：

```bash
curl -4 -s --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" https://oauth2.googleapis.com/
```

結果：**`HTTP 000`**（連線逾時／無法建立連線）

伺服器**無法對外連線** `oauth2.googleapis.com:443`（可能為防火牆、無外網、或路由問題）。`id_token` 驗證亦需連 `www.googleapis.com`。

### 必要修復（網管）

開放此伺服器**對外** HTTPS 443 至：

- `oauth2.googleapis.com`
- `www.googleapis.com`

修復後再測，成功時 curl 應回 `HTTP 404` 或 `HTTP 405`（有 HTTP 回應即可，不代表錯誤）。

### 暫時替代方案

在網路修好前，可清空 `router.yaml` 的 `google_client_id` 與 `google_client_secret`，重啟 uvicorn，Portal 會回到**開發模式**（手動填 Gmail + 姓名）。**不建議正式環境使用。**

---

## 7. 操作指令速查

### 啟動服務

```bash
cd ~/Programs/ollama_router
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

（使用者常在 tmux session `pegacli` 中執行）

### 確認 OAuth 是否啟用

```bash
curl http://127.0.0.1:8000/auth/config
# 預期：{"oauth_enabled":true,"redirect_uri":"http://203-71-78-31.nip.io:8000/auth/google/callback"}
```

### 測試外網連線

```bash
curl -4 -s --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" https://oauth2.googleapis.com/
curl -4 -s --max-time 10 -o /dev/null -w "HTTP %{http_code}\n" https://www.googleapis.com/
```

### 跑相關測試

```bash
cd ~/Programs/ollama_router
uv run pytest tests/presentation/fastapi/test_portal_router.py tests/application/use_cases/test_portal_google_login.py -q
```

最後已知狀態：**102 tests passed**（含 OAuth 相關測試，mock 不依賴外網）。

---

## 8. Google Cloud Console 檢查清單

- [ ] OAuth 2.0 Client 類型為 **Web application**
- [ ] Authorized redirect URI = `{public_url}/auth/google/callback`
- [ ] OAuth consent screen 已設定
- [ ] Testing 模式下，登入者 Gmail 已加入 **Test users**
- [ ] `google_client_id` / `google_client_secret` 已寫入 `~/.ollama_router/router.yaml`（非 `.env`）
- [ ] 改設定後已重啟 uvicorn

---

## 9. 給下一位 agent 的建議待辦

### 優先（阻塞）

1. 確認網管是否已開放對外 443；用上方 curl 指令驗證
2. 外網通後，用 `http://203-71-78-31.nip.io:8000/portal`（或區網改 `192-168-7-16.nip.io`）完整走一次 OAuth
3. 若仍失敗，看 Portal 上 `login_error` 具體訊息（已改善錯誤回報）

### 可選改善

1. 若使用者主要在區網（`192.168.7.16`），將 `public_url` 改為 `http://192-168-7-16.nip.io:8000` 並更新 Google Console
2. 考慮在 README 或獨立 guide 補充「防火牆 / 外網需求」章節
3. `.env` 與 `router.yaml` 重複存放憑證易混淆，可考慮支援從環境變數讀取 OAuth 憑證（**尚未實作**，使用者未要求）
4. callback 可加上 server-side logging（`logging.exception`）方便除錯，目前錯誤主要回傳給前端 query string

### 不建議在未確認需求前做的事

- 改為 Firebase Auth（使用者曾詢問，已說明差異，最終採 Google OAuth Code Flow）
- 在未修外網前嘗試更換 OAuth 實作方式（問題在網路層，非程式邏輯）

---

## 10. 相關對話脈絡（簡要）

1. 使用者發現 `/auth/google` 回 422 → 修復 `portal.html` 的 `window.name` 衝突
2. 使用者問是否真有 Google 驗證 → 說明舊為 dev stub，後實作真正 OAuth
3. 使用者申請 Google Console OAuth Client → IP 被拒，改用 nip.io
4. 協助檢查 `router.yaml`、更新 `session_secret`
5. OAuth callback 收到 code 但登入失敗 → 診斷為伺服器無法連 `oauth2.googleapis.com`（`HTTP 000`）

---

## 11. 伺服器與環境備註

| 項目 | 值 |
|------|-----|
| 主機 | `MKSH-AI-Server` |
| 專案路徑 | `/home/mkshaiadmin/Programs/ollama_router` |
| 區網 IP（log 常見） | `192.168.7.16` |
| 公網 IP（nip.io 目前使用） | `203.71.78.31` |
| 服務 port | `8000` |
| tmux session | `pegacli`（常見） |
| 管理員 email | `mz038197@gmail.com` |

---

## 12. 憑證與安全提醒

- `~/.ollama_router/router.yaml` 含 **client_secret** 與 **session_secret**，勿提交 git
- 專案 `.env` 亦有 OAuth 憑證副本，已在 `.gitignore` 中
- 若憑證曾出現在對話或截圖中，可考慮在 Google Console **輪替 client secret**
